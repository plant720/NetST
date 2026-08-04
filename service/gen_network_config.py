"""
Utility module replacing the GenNetworkConfig2 external executable.
Generates haplotype network configuration and JavaScript visualization files.

Original author: xlzh (xiaolongzhang2015@163.com)
Integrated as Python module 2026
"""

import csv
import json
import os

from model.trait_schema import default_category_colors, normalize_hex_color


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


def _color_group_config(hap_conf_list, group_colors=None):
    """Assign colors to each unique group.

    Groups are written to groupconf.csv exactly as-is; tcsBU's loadGroups
    already seeds the list with a 'Default' (white) entry, so we only
    write non-Default groups.  When all samples fall into 'Default'
    (i.e. no discrete traits) we return an empty list — the groupconf
    file will be empty and tcsBU will keep its built-in Default group.

    ``group_colors`` (group name → ``#RRGGBB``) lets the Metadata tab override
    the automatic colours; groups it does not cover use the curated palette
    for up to ten groups or stable, non-repeating random colours above ten.
    """
    group_colors = group_colors or {}
    group_names = list(dict.fromkeys(group for _, group, _ in hap_conf_list))
    non_default = [g for g in group_names if g != "Default"]

    if not non_default:
        # No named groups — all samples belong to Default; groupconf stays empty.
        return []

    valid_overrides = {
        name: color
        for name in non_default
        if (color := normalize_hex_color(group_colors.get(name)))
    }
    automatic = default_category_colors(
        non_default,
        seed="primary-group",
        excluded=tuple(valid_overrides.values()),
    )
    result = []
    for name in non_default:
        color = valid_overrides.get(name, automatic[name])
        result.append((name, color, 'none'))
    return result


def _write_conf(hap_conf_list, group_conf_list, out_prefix: str) -> None:
    # tcsBU parses these files with line.split(';') rather than a CSV parser,
    # so delimiters/newlines must be normalized instead of CSV-quoted.
    def field(value) -> str:
        return str(value).replace(';', '_').replace('\r', '_').replace('\n', '_')

    with open(out_prefix + '_hapconf.csv', 'w', encoding='utf-8') as f:
        for sample, group, hap in hap_conf_list:
            f.write(f"{field(sample)};{field(group)};{field(hap)}\n")
    with open(out_prefix + '_groupconf.csv', 'w', encoding='utf-8') as f:
        for group, color, style in group_conf_list:
            f.write(f"{field(group)};{field(color)};{field(style)}\n")


def _file_to_json_string(file_name: str) -> str:
    with open(file_name, 'r', encoding='utf-8', newline='') as f:
        content = f.read()
    # json.dumps correctly escapes quotes, backslashes, CR/LF and control
    # characters before the content is embedded into generated JavaScript.
    return json.dumps(content, ensure_ascii=False)


def generate_network_config(gml_file: str, hap_file: str, out_prefix: str,
                            has_continuous_traits: bool = False,
                            group_colors=None) -> None:
    """
    Main entry point replacing the GenNetworkConfig2 executable.

    Args:
        gml_file:               Path to a tcsBU-compatible .gml network file.
        hap_file:               Path to the _seq.meta.csv file.
        out_prefix:             Output path prefix (without extension). Writes
                                <out_prefix>_hapconf.csv, <out_prefix>_groupconf.csv,
                                and <out_prefix>.js.
        has_continuous_traits:  When True, also embeds traitconffile in the .js so that
                                tcsBU.js can auto-load continuous-trait coloring.
        group_colors:           Optional {group name: '#RRGGBB'} overrides from the
                                Metadata tab; unspecified groups fall back to palette.
    """
    hap_conf_list = _gen_hap_config(hap_file)
    generate_network_config_from_assignments(
        gml_file, hap_conf_list, out_prefix,
        has_continuous_traits=has_continuous_traits,
        group_colors=group_colors,
    )


def generate_network_config_from_assignments(
    gml_file: str,
    hap_conf_list,
    out_prefix: str,
    has_continuous_traits: bool = False,
    group_colors=None,
) -> None:
    """Write tcsBU config directly from ``(sample, group, haplotype)`` rows.

    This is used when metadata changes after a network has already been built:
    the existing sample-to-haplotype assignment is preserved and only tcsBU's
    group/haplotype/trait configuration plus its embedding JavaScript changes.
    """
    hap_conf_list = list(hap_conf_list)
    group_conf_list = _color_group_config(hap_conf_list, group_colors)
    _write_conf(hap_conf_list, group_conf_list, out_prefix)

    with open(out_prefix + '.js', 'w', encoding='utf-8') as fp:
        fp.write('var gmlfile = {target: {files: [new File([')
        fp.write(_file_to_json_string(gml_file))
        fp.write('], ".gml")]}};\n')

        fp.write('var hapconffile = {target: {files: [new File([')
        fp.write(_file_to_json_string(out_prefix + '_hapconf.csv'))
        fp.write('], ".csv")]}};\n')

        fp.write('var groupconffile = {target: {files: [new File([')
        fp.write(_file_to_json_string(out_prefix + '_groupconf.csv'))
        fp.write('], ".csv")]}};\n')

        traitconf_path = out_prefix + '_traitconf.csv'
        if has_continuous_traits and os.path.isfile(traitconf_path):
            fp.write('var traitconffile = {target: {files: [new File([')
            fp.write(_file_to_json_string(traitconf_path))
            fp.write('], ".csv")]}};\n')
