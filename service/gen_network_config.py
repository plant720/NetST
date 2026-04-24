"""
Utility module replacing the GenNetworkConfig2 external executable.
Generates haplotype network configuration and JavaScript visualization files.

Original author: xlzh (xiaolongzhang2015@163.com)
Integrated as Python module 2026
"""

import csv
import os
import random

# Predefined color palettes for 3–10 groups
_COLOR_PALETTES = {
    3: ("#D85356", "#D7AA36", "#94BBAD"),
    4: ("#F0776D", "#FBD2CB", "#29B4B6", "#C5E7E8"),
    5: ("#8386A8", "#D15C6B", "#F5CF36", "#8FB943", "#78B9D2"),
    6: ("#DA352A", "#FF8748", "#5BAA56", "#B8BB5B", "#4186B7", "#8679BE"),
    7: ("#794292", "#44599B", "#2C8FA0", "#40A93B", "#EFE644", "#E97124", "#DF4442"),
    8: ("#FF7F00", "#FDBF6F", "#E31A1C", "#FB9A99", "#33A02C", "#B2DF8A", "#1F78B4", "#A6CEE3"),
    9: ("#E71F19", "#2CB8BB", "#55B333", "#6A1B86", "#E2C9E1", "#A4C5E8", "#EF7A1C", "#F9CA9C", "#F7C3C4"),
    10: ("#009F72", "#D25F27", "#E49E21", "#EFE341", "#1F78B4", "#FB9A99", "#E21A1C", "#EAD59F", "#C9B1D4", "#52310F"),
}


def _text_to_integer(text: str) -> int:
    if not text:
        return 0
    return int(''.join(str(ord(ch)) for ch in text))


def _random_color(seed: int) -> str:
    random.seed(seed)
    chars = '123456789ABCDEF'
    return '#' + ''.join(chars[random.randint(0, 14)] for _ in range(6))


def _gen_hap_config(hap_file: str):
    """Read _seq.meta.csv and return list of (sample, group, hap) tuples.

    The CSV columns are: sequence_name, haplotype, continuous_traits, discrete_traits.
    discrete_traits (last column) is used as the group label; empty values are
    mapped to 'Default' so that tcsBU always has a valid group name.
    """
    hap_conf_list = []
    with open(hap_file, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        # Skip header; empty file → no rows to process.
        if next(reader, None) is None:
            return hap_conf_list
        for row in reader:
            if len(row) < 2:
                continue
            sample = row[0]
            hap = row[1]
            group = row[-1].strip() if len(row) >= 4 else ""
            if not group:
                group = "Default"
            hap_conf_list.append((sample, group, hap))
    return hap_conf_list


def _color_group_config(hap_conf_list):
    """Assign colors to each unique group.

    Groups are written to groupconf.csv exactly as-is; tcsBU's loadGroups
    already seeds the list with a 'Default' (white) entry, so we only
    write non-Default groups.  When all samples fall into 'Default'
    (i.e. no discrete traits) we return an empty list — the groupconf
    file will be empty and tcsBU will keep its built-in Default group.
    """
    group_names = list(dict.fromkeys(group for _, group, _ in hap_conf_list))
    non_default = [g for g in group_names if g != "Default"]

    n = len(non_default)
    if n == 0:
        # No named groups — all samples belong to Default; groupconf stays empty.
        return []

    if n in _COLOR_PALETTES:
        return [(name, _COLOR_PALETTES[n][i], 'none') for i, name in enumerate(non_default)]

    # Fallback: random colors seeded by group name
    result = []
    seen = {}
    for _, group, _ in hap_conf_list:
        if group != 'Default' and group not in seen:
            color = _random_color(_text_to_integer(group))
            seen[group] = color
            result.append((group, color, 'none'))
    return result


def _write_conf(hap_conf_list, group_conf_list, out_prefix: str) -> None:
    with open(out_prefix + '_hapconf.csv', 'w', encoding='utf-8') as f:
        for sample, group, hap in hap_conf_list:
            f.write(f"{sample};{group};{hap}\n")
    with open(out_prefix + '_groupconf.csv', 'w', encoding='utf-8') as f:
        for group, color, style in group_conf_list:
            f.write(f"{group};{color};{style}\n")


def _file_to_escaped(file_name: str) -> str:
    with open(file_name, 'r', encoding='utf-8') as f:
        content = f.read()
    return content.replace('"', '\\"').replace('\n', '\\n')


def generate_network_config(gml_file: str, hap_file: str, out_prefix: str,
                            has_continuous_traits: bool = False) -> None:
    """
    Main entry point replacing the GenNetworkConfig2 executable.

    Args:
        gml_file:               Path to the .gml network file produced by fastHaN.
        hap_file:               Path to the _seq.meta.csv file.
        out_prefix:             Output path prefix (without extension). Writes
                                <out_prefix>_hapconf.csv, <out_prefix>_groupconf.csv,
                                and <out_prefix>.js.
        has_continuous_traits:  When True, also embeds traitconffile in the .js so that
                                tcsBU.js can auto-load continuous-trait coloring.
    """
    hap_conf_list = _gen_hap_config(hap_file)
    group_conf_list = _color_group_config(hap_conf_list)
    _write_conf(hap_conf_list, group_conf_list, out_prefix)

    with open(out_prefix + '.js', 'w', encoding='utf-8') as fp:
        fp.write('var gmlfile = {target: {files: [new File(["')
        fp.write(_file_to_escaped(gml_file))
        fp.write('"], ".gml")]}};\n')

        fp.write('var hapconffile = {target: {files: [new File(["')
        fp.write(_file_to_escaped(out_prefix + '_hapconf.csv'))
        fp.write('"], ".csv")]}};\n')

        fp.write('var groupconffile = {target: {files: [new File(["')
        fp.write(_file_to_escaped(out_prefix + '_groupconf.csv'))
        fp.write('"], ".csv")]}};\n')

        traitconf_path = out_prefix + '_traitconf.csv'
        if has_continuous_traits and os.path.isfile(traitconf_path):
            fp.write('var traitconffile = {target: {files: [new File(["')
            fp.write(_file_to_escaped(traitconf_path))
            fp.write('"], ".csv")]}};\n')
