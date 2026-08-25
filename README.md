# NetST

> English | [中文](README.zh-CN.md)

**NetST is an open-source desktop application for project-based haplotype network analysis with metadata integration**. It keeps sequences, sample-to-haplotype assignments, categorical and continuous metadata, network settings, analytical results, and visualization state in one reusable project. NetST is intended for population genetics, phylogeography, molecular
epidemiology, and other studies of closely related sequence variants.

## Highlights

- Import **FASTA, NEXUS, PHYLIP, VCF/VCF.GZ**, plus CSV/TSV metadata.
- Align sequences with **MAFFT** or **MUSCLE** and collapse identical aligned sequences into haplotypes.
- Construct networks with six methods: **Original TCS, Modified TCS, MSN, MJN, RMST, and McAN**.
- Compare construction methods while retaining the same sample-to-haplotype and metadata mappings.
- Display multiple categorical and continuous variables on one network as concentric node layers in the enhanced **tcsBU** view.
- Calculate sequence quality/diversity, population differentiation, pairwise p-distance/PCoA, and network-topology descriptors.
- Export networks, sequences, tables, SVG/PNG/JPG/PDF figures, JSON reports, and a portable `<project>.netst.json` project record.
- Use the interface in English or Chinese; long-running tasks can be cancelled.

## Download and run

Published packages, when available, are listed on the [GitHub Releases page](https://github.com/plant720/NetST/releases).

| Platform | Release target | Bundled analysis tools |
|---|---|---|
| Windows x86-64 | `NetST\NetST.exe` | MAFFT, MUSCLE, fastHaN, RMST, McAN |
| macOS Apple Silicon | `NetST.app` | MAFFT, MUSCLE, fastHaN, RMST, McAN |

Keep every file in the extracted package together. 

To run from source, use Python 3.10, 3.11, or 3.12:

```bash
pip install -r requirements.txt
python main_form.py
```

## Quick start

1. Choose **File → Import FASTA/NEXUS/PHYLIP/VCF** and standardize the sample identifiers.
2. Optionally choose **File → Load Metadata** and map one sample-name column, categorical traits, continuous traits, and one categorical Group.
3. Set the project name and output directory in the right-side panel.
4. Choose **Analysis → Build / Rebuild Haplotype Network**, then select a construction method and its parameters.
5. Inspect the **Network**, **Haplotype**, **Alignment**, and optional **Interpretation** tabs. Use the Metadata tab to change visible traits and colours without rebuilding topology.

NetST automatically maintains `<project>.netst.json`. Use **File → Export Project Configuration** to save a portable copy, or **File → Import and Replay Project** to verify source hashes and restore the recorded workflow and view.

## Inputs and outputs

| Type | Supported files or main results |
|---|---|
| Sequence input | `.fas`, `.fasta`, `.fa`, `.fna`, `.ffn`, `.nex`, `.nexus`, `.nxs`, `.phy`, `.phylip`, `.vcf`, `.vcf.gz` |
| Metadata input | `.csv`, `.tsv`, `.txt`; sample names must match the loaded sequence names exactly |
| Sequence and haplotypes | raw/aligned FASTA, haplotype FASTA, PHYLIP, and sample-to-haplotype CSV |
| Network and visualization | GML, HTML/JavaScript, tcsBU configuration CSV, SVG, PNG, JPG, and PDF |
| Interpretation | `<project>_diversity_analysis.json`, `<project>_distance_analysis.json`, `<project>_topology_analysis.json` |
| Reusable project | `<project>.netst.json` plus managed inputs under `inputs/<role>/` |

Files that reuse the same output directory and project name may be replaced by a later run. The default output directory is `~/HaplotypeOutput`.

## Documentation

- User manual: [English](docs/NetST-User-Manual.md) · [中文](docs/NetST-使用手册.md)
- Embedded tcsBU help: [HTML](static/tcsbu/help.html) · [PDF](static/docs/tcsbu.pdf)
- In-app NetST manual: [PDF](static/docs/netst.pdf)

The manuals describe input validation, algorithm parameters, metadata mapping, output files, interpretation conventions, project replay, and known limits.

## Example datasets

The [`examples/`](examples) directory contains ready-to-run projects covering plants, animals, and viruses:

| Dataset | Demonstrates |
|---|---|
| `Bupleurum_chinense` | Unaligned multi-locus sequences with categorical and continuous traits |
| `Rhodiola_bupleuroides` | A larger aligned plastome dataset with genetic clusters and elevation |
| `Lepus_europaeus` | Prepared mitochondrial haplotype representatives and reported haplogroups |
| `DP-SARS-CoV-2` | FASTA/PHYLIP/VCF import, geographic/time metadata, and McAN input |
| `SL-SARS-CoV-2` | Full-genome lineage data and reference-based McAN analysis |

Each example directory includes its own README with data provenance and a suggested workflow.

## Citation

The accompanying manuscript is currently cited provisionally as:

> Zhang Z, Song Y, Yu X, Hou J, Yu Y. *NetST: a desktop application for project-based haplotype network analysis with metadata integration.* Manuscript.

Please also cite the external methods used in your analysis, including [fastHaN](https://doi.org/10.1111/1755-0998.13829), [tcsBU](https://doi.org/10.1093/bioinformatics/btv636), [MAFFT](https://doi.org/10.1093/bioinformatics/bty121), [RMST](https://doi.org/10.1111/2041-210X.12969), and [McAN](https://doi.org/10.1093/bib/bbad174), as applicable.

## License and contact

NetST source code is released under the [MIT License](LICENSE). Bundled third-party programs retain their own licenses. Report reproducible software problems through the [issue tracker](https://github.com/plant720/NetST/issues), without attaching private or sensitive sequence data. For other questions, contact [yyu@scu.edu.cn](mailto:yyu@scu.edu.cn) or [zzhen0302@163.com](mailto:zzhen0302@163.com).
