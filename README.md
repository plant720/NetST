# NetST

> 🌐 **English** | [中文](README.zh-CN.md)

**Haplotype Network Analysis Tool / 单倍型网络分析工具**

NetST is a PyQt6 desktop application for multiple-sequence alignment, haplotype identification, haplotype-network construction, and interactive visualization, rebuilt from a legacy VB.NET program. It targets population genetics, phylogeography, and molecular epidemiology, and unifies established engines (MAFFT, MUSCLE, fastHaN, McAN) with built-in algorithms (RMST, interpretation analytics) behind one bilingual interface.

**Interface version: 2.0.0**

---

## Table of Contents

- [Features](#features)
- [Documentation](#documentation)
- [Workflow](#workflow)
- [Supported Platforms](#supported-platforms)
- [Installation & Running](#installation--running)
- [Quick Start](#quick-start)
- [Input Data](#input-data)
- [Metadata & Visualization Refresh](#metadata--visualization-refresh)
- [Network Algorithms & Parameters](#network-algorithms--parameters)
- [Visualization (tcsBU)](#visualization-tcsbu)
- [Interpretation Analysis](#interpretation-analysis)
- [Data Export & Format Conversion](#data-export--format-conversion)
- [Output Files](#output-files)
- [Project Structure](#project-structure)
- [Subprocess Control](#subprocess-control)
- [Testing](#testing)
- [Packaging](#packaging)
- [Development Notes](#development-notes)
- [Known Limitations](#known-limitations)
- [Citation](#citation)
- [License](#license)

---

## Features

- Import **FASTA, NEXUS, PHYLIP, or VCF** sequence data; metadata can be parsed from legacy sample IDs or imported separately from CSV/TSV.
- Export the current data as FASTA, NEXUS, PHYLIP, VCF + metadata, or a standalone metadata table (CSV/TSV).
- Import multi-sample VCF (optionally reconstructing full-length sequences with a reference FASTA); parse metadata from sample IDs, or pass a metadata file to enable native McAN VCF mode.
- Clean, replace, or split sample IDs at import, extracting sample name, categorical trait, and continuous trait.
- Import multiple categorical/continuous traits at once from CSV/TSV, designate one categorical trait as the group, with a visual column mapping and delimiter auto-detection.
- Inspect, edit, select, or deselect the sequences included in an analysis from the data table.
- Align with **MAFFT** or **MUSCLE**; collapse identical aligned sequences into unique haplotypes.
- Build **Original TCS, Modified TCS, MSN, or MJN** networks with fastHaN, a built-in **RMST**, or a **McAN** minimum-cost arborescence network.
- Visualize multiple categorical/continuous traits as concentric rings using an embedded **tcsBU / D3.js** view, with a matching multi-ring legend; side panels collapse and drag-resize.
- Re-map grouping and continuous traits onto an existing network without rebuilding it, when metadata is added or edited after construction.
- Explore data and network in **Analysis → Interpretation Analysis** with visual quality/diversity, missing-aware pairwise **p-distance + PCoA**, and network **topology metrics**, keeping topological description distinct from ancestry/transmission inference.
- Bilingual **Chinese / English** UI that refreshes together on a language switch.
- Long-running analyses run on background threads and are cancellable from the status bar; timeouts and cancellation clean up external processes and their children.

## Documentation

A full step-by-step user manual is available in both languages:

- 📘 **[NetST User Manual (English)](docs/NetST-User-Manual.md)**
- 📗 **[NetST 使用手册（中文）](docs/NetST-使用手册.md)**

Two SARS-CoV-2 example datasets are referenced throughout the manual:

- **SL-SARS-CoV-2** — 130 representative haplotypes distinguishing the L / S lineages (categorical trait).
- **DP-SARS-CoV-2** — 482 genome sequences with geographic location (categorical) and collection date (continuous).

## Workflow

```text
FASTA / NEXUS / PHYLIP / VCF sequences
  │
  ├─ Sample-ID standardization (optional legacy-metadata parsing) / ambiguous-base filtering
  ├─ Optional: import metadata from CSV/TSV
  ▼
MAFFT or MUSCLE multiple-sequence alignment
  ▼
Identify unique haplotypes → PHYLIP / CSV / FASTA files
  ▼
fastHaN (TCS / MSN / MJN), built-in RMST, or McAN directed network
  ▼
Convert to a common GML and generate tcsBU config
  ▼
Interactive visualization in Qt WebEngine ── optional: Interpretation Analysis
```

## Supported Platforms

| Platform | Run from source | Bundled analysis programs | PyInstaller spec |
|---|:---:|---|---|
| macOS Apple Silicon | Yes | MAFFT, MUSCLE 3, fastHaN, McAN 1.4.3 arm64 | `netst-mac-arm64.spec` |
| Windows x86-64 | Yes | MAFFT, MUSCLE 3, fastHaN, McAN 1.4.3 | `netst-win.spec` |
| Linux | Code path exists | Not fully provided | Not provided |

Linux users must supply compatible external programs and place the binaries per the platform conventions in `AnalysisService`. The current official packaging targets are macOS Apple Silicon and Windows x86-64.

## Installation & Running

Use Python 3.10 and an isolated virtual environment.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_form.py
```

### Windows PowerShell

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_form.py
```

Main Python dependencies: `PyQt6`, `PyQt6-WebEngine`, and `chardet` (`PyInstaller` is only needed to build releases). RMST does not require NumPy.

Target-platform binaries for MAFFT, MUSCLE, fastHaN, McAN, and RMST are already under `lib/` for macOS and Windows. Apple Silicon uses native arm64 engines; the Windows McAN and RMST executables are static-runtime x86-64 builds. If the bundled MAFFT is unavailable, the program falls back to a system `mafft` on `PATH`.

## Quick Start

1. In the **File** menu, choose **Import FASTA / NEXUS / PHYLIP / VCF** to load sequences.
2. In the standardization dialog, preview and configure sample-name cleaning, replacement, splitting, or numbering; legacy files can still extract categorical/continuous traits from sample IDs.
3. For a standalone metadata table, choose **File → Load Metadata** to import CSV/TSV and map the sample-name, categorical, and continuous columns.
4. On the **Data** tab, review the data and tick the samples to include.
5. On the right, enter a project name and choose an output directory (default `~/HaplotypeOutput`).
6. Pick what to run:
   - **Tools → Multiple Sequence Alignment** — run MAFFT/MUSCLE only;
   - **Tools → Calculate Haplotype** — align and compute haplotypes without a network;
   - **Analysis → Build / Rebuild Haplotype Network** — the full network analysis;
   - **Metadata → Apply Visualization Config** — re-skin an existing network without rebuilding (see below).
7. View results on the **Network, Alignment, and Haplotype** tabs.
8. Run quality/diversity, genetic distance/PCoA, or topology analysis from **Analysis → Interpretation Analysis**; results appear on the **Interpretation** tab.
9. Use **File → Export Sequence Data** to pick a sequence format, or **Export Metadata** for a standalone metadata table.

While an analysis runs, the bottom of the window shows progress and a **Cancel** button. Cancelling requests the background task to stop and terminates the whole process group of the current external program. The same cleanup runs on close or when a new task replaces an old one.

## Input Data

### FASTA

Plain FASTA works:

```fasta
>sample_01|population_A|12.5
ATGCTAGCTAGCTACG
>sample_02|population_B|13.1
ATGCTAGCTAGTTACG
```

The import dialog can clean, replace, or extract the sample name, categorical trait, and continuous trait by delimiter and 0-based field index, compatible with legacy composite headers; or process only the sample name and import multiple traits via **File → Load Metadata**. Continuous traits must be valid numbers; sequences containing `RYSWKMBDHVN` ambiguity codes can be filtered at import. Whitespace in FASTA headers is normalized to underscores so PHYLIP and fastHaN do not split one name into several fields.

### NEXUS & PHYLIP

- **Import NEXUS** supports DNA/RNA `MATRIX` in `DATA`/`CHARACTERS` blocks: sequential, named interleaved, unnamed interleaved continuation lines, quoted names, nested comments, and `MATCHCHAR`.
- **Import PHYLIP** supports sequential and common interleaved PHYLIP; the declared count and alignment length in the first line must match the data.
- Both enter the same name-standardization dialog as FASTA and load as the current raw data. A failed import does not overwrite existing table data.

### Metadata table (CSV / TSV)

Besides parsing from sample IDs, metadata can be imported from a separate CSV/TSV (**File → Load Metadata**). The first line is a header, and at least one column must map 1-to-1 to imported sequence names:

```csv
sample,population,value
sample_01,population_A,12.5
sample_02,population_B,13.1
```

The delimiter is auto-detected (tab preferred). Each column can be Sample name, Ignore, Categorical, or Continuous; select any number of traits, but at least one categorical trait must be the Group. The program verifies that sample names match completely and rejects duplicates on either side.

Each Continuous column has its own **Continuous conversion** button. The source
text may be handled as:

- **Plain number** — strict numeric validation;
- **Date / time** — accepts common forms such as `2022-10-1`, `2022/10/1`,
  `2022-10`, and ISO date-times, then converts them to elapsed days, calendar
  months, or calendar years from a user-supplied start date (or the earliest
  valid date when left blank);
- **Measurement with unit** — normalizes mixed length (`mm/cm/m/km/in/ft`),
  mass (`mg/g/kg`), or temperature (`°C/°F/K`) values to one selected unit.
  A separate source unit can be assigned to values without a suffix.

The dialog previews source and converted values, validates the full column, and
reports the original file row when a value cannot be converted. Blank cells stay
blank and the source file is never modified; normalized numbers enter the Data
table and therefore use the existing continuous gradient/ring visualization.

A **Metadata** tab then appears. Each row is a trait: switch categorical/continuous, choose the single Group, toggle visibility, and edit colours (categorical palette or continuous low/high endpoints, via a colour picker or hex value). Categorical traits with 2–10 classes use curated class-count-specific palettes; larger sets receive stable, non-repeating generated colours. The default continuous gradient runs from gray (`#BDBDBD`) to black (`#000000`); values within each node are sorted numerically from low to high before its ring sectors are drawn. The program prevents deleting the last categorical Group. Nodes draw concentric rings in Metadata-table order — Group innermost, others outward — and the tcsBU **Legend** lists them in the same order.

### VCF import

**File → Import VCF** accepts VCF / VCF.GZ with per-sample genotype columns. The sequence workflow targets a single region, so the VCF must contain one contig and each record must carry `GT`. VCF sample names enter the standardization dialog like other formats.

The metadata file is optional:

- **None** — metadata parsed from sample IDs only.
- **Plain CSV/TSV** — matched by sample name; fills categorical (group) and continuous traits.
- **McAN six-column TSV** (`SampleName AccessionID SamplingDate Country State City`, `*` for missing, header optional) — fills a categorical trait merged from Country/State/City and, when sample names are unchanged, enables native McAN VCF analysis (`McAN --vcf`) that keeps real sampling dates for orientation. Renaming/removing samples or later editing the table falls back to the aligned-FASTA → mutation adapter.

Alignment reconstruction: without a reference FASTA, each record becomes an equal-width variant-site block; with a reference FASTA, each VCF `REF` is validated and invariant regions are filled back for a full-length alignment. Multi-allelic sites resolve by GT allele number; heterozygous single-base sites use IUPAC codes, heterozygous complex indels use `N`. Symbolic ALTs, breakends, multiple contigs, and overlapping records are rejected.

## Metadata & Visualization Refresh

Network **topology** is determined by input samples and sequences; metadata types, grouping, rings, and colours only decide **how** existing topology is displayed.

| Change | Action |
|---|---|
| Import a new FASTA/NEXUS/PHYLIP/VCF | Rebuild the haplotype network |
| Change sample names, sequences, or the analysis selection | Rebuild the haplotype network |
| Change the network algorithm/parameters | Rebuild the haplotype network |
| Import or edit metadata values | Only click **Apply Visualization Config** |
| Change trait type, Group, Visualize, or colour | Only click **Apply Visualization Config** |
| Adjust group names, colours, or membership in tcsBU | Only update the current visualization config |

A lightweight refresh rewrites only tcsBU's `_hapconf.csv`, `_groupconf.csv`, `_traitconf.csv`, embedded `.js`, and `.html`; the existing `.gml`, alignment, and sample-to-haplotype mapping are unchanged. Identical sequences keep the same H1/H2… labels. Metadata is matched by sample name; samples renamed after construction fall back to empty metadata. When sequences/alignment actually change, use **Build / Rebuild Haplotype Network** instead.

## Network Algorithms & Parameters

| Algorithm | Engine ID | Parameters |
|---|---|---|
| Original TCS | `original_tcs` | threads, ambiguous sites, merge intermediate nodes |
| Modified TCS | `modified_tcs` | threads |
| Minimum Spanning Network | `msn` | epsilon |
| Median-Joining Network | `mjn` | threads, epsilon |
| Randomized Minimum Spanning Tree | `rmst` | exact/random mode, replicates, random seed, exclude ambiguous sites |
| McAN Minimum-cost Arborescence Network | `mcan` | threads, reference sequence, exclude ambiguous sites |

If input sequences differ in length, the full analysis runs MAFFT first, falling back to MUSCLE; equal lengths are treated as already aligned.

### RMST built-in implementation

The bundled C++17 `netst-rmst` executable reads `project_hap.fasta` and `project_seq.meta.csv` and computes uncorrected mutation counts (Hamming distance) over unique haplotypes. **Exact mode** (default, recommended) determines all edges that can appear in at least one MST by distance layer — deterministic and seed-independent. **Random mode** repeatedly randomizes haplotype order and runs stable Kruskal, reporting each edge's occurrence count and frequency; a fixed seed reproduces results across macOS and Windows, but finite replicates do not guarantee finding every compatible edge.

The native randomized engine uses a platform-independent SplitMix64 permutation stream. Consequently, the same seed is stable between the new macOS and Windows binaries but is not intended to reproduce historical NumPy RNG samples byte-for-byte.

By default any column with a character outside `A/C/G/T/U/-` is excluded, RNA `U` becomes `T`, and gap is a comparable state. Haplotypes that become identical after filtering merge into one node (recorded in `warnings` and node `haplotypes`). The standard-library-only native engine keeps RMST out of the Python package graph; exact mode accepts ≤ 1000 filtered nodes, random mode ≤ 500 nodes and ≤ 1000 replicates. The RMST `project.gml` uses the same tcsBU dialect as fastHaN/McAN. Reference: Paradis, E. (2018), *Methods Ecol Evol* 9:1308–1317.

### McAN adapter

`service/mcan_adapter.py` supports two paths. When importing a VCF with McAN six-column metadata and unchanged sample names, it calls `McAN --vcf` natively and keeps real sampling dates for orientation. For FASTA/PHYLIP sources, metadata-free VCFs, or renamed/edited samples, it builds mutations from the aligned sequences: compute per-site differences against the chosen reference, generate mutation/metadata with `S0000001`-style aliases to avoid GraphML corruption, produce an explicit site mask, run McAN in a dedicated `project_mcan/`, and convert the GraphML to a tcsBU-readable GML restoring original names and distances.

The bundled McAN workflow limits the maximum sequence coordinate to 30000, so longer alignments are rejected up front. A FASTA has no sampling dates, so the adapter does not fabricate a time order — the result is a mutation-inclusion network rooted at the chosen reference. The adapter probes `--help` and selects McAN 1.2's `--outDir` or McAN 1.4.x's `--out` automatically; it accepts both legacy `haplotype_loci.graphml` output and `<prefix>.haplonet.graphml` output. The program prefers `McAN`/`McAN.exe` in the platform `lib` directory; a self-built executable can be set via `NETST_MCAN_EXECUTABLE`. Reference: Li, L. et al. (2022), bioRxiv 2022.07.23.501111.

## Visualization (tcsBU)

The network renders on the **Network** tab with an enhanced **tcsBU / D3.js** view embedded in Qt WebEngine. Each haplotype node draws concentric rings (Group innermost, other enabled traits outward), sized by frequency, with a **Legend** listing every class swatch and continuous gradient range in inner-to-outer order.

The toolbar provides **Save Image** (SVG / PNG / JPG — SVG is standard `image/svg+xml`, PNG/JPG export at 2× by default), zoom, node/link editing, legend toggle, haplotype/distance labels, and **Edge Weight** (thicker edges for smaller mutation distances).

The **Advanced** dialog is draggable by its title bar and grouped into three sections:

- **Force-Directed Layout Settings** — Link Distance, Link Strength, Friction, Charge, Gravity, plus Start/Stop.
- **Node and Edge Settings** — **Node Radius** (radius of a frequency-1 node, preserving relative sizes), **Node Line Width** (node outline), **Edge Line Width** (base edge/link stroke), **Edge Weight Scale** (maximum weighted-width multiplier), and Text Offset.
- **Metadata Ring Settings** — **Ring Line Width** (ring-segment stroke), **Base Ring Width** (base thickness of a non-Group ring at ratio 1; actual = base × ring ratio), and Outer Ring Ratios (comma-separated, inner→outer).

The Data tab's Sequence column is read-only so an accidental edit cannot invalidate an existing alignment, haplotypes, and network; names, selection, and metadata traits stay editable.

## Interpretation Analysis

Reimplemented from a review of the legacy auxiliary scripts (not a wrapper around them). The computation layer uses an immutable aligned-sequence snapshot, decoupled from the Qt UI and file output, and runs on a background thread.

| Menu item | Input & computation | Main results |
|---|---|---|
| Sequence Quality and Diversity | current selected equal-length aligned sequences; complete or pairwise deletion | per-sample/per-site missing rates, effective sites, variable sites, parsimony-informative sites, S, Hd, π, θW, group richness, private haplotypes |
| Genetic Distance and PCoA | only A/C/G/T as called; gap, N, ?, IUPAC pairwise-deleted | p-distance matrix, comparable sites per pair, PCoA coordinates, positive/negative eigenvalue diagnostics |
| Network Topology Metrics | the current project GML, or a chosen tcsBU-compatible GML | node/edge counts, components, density, cycle rank, degree, closeness, betweenness, articulation points, bridges |

**Result visualizations.** The Interpretation tab presents results as **Overview + Charts + tables**: colour-coded **KPI cards**; a **PCoA ordination scatter** (coloured by group) and **distance heatmap**; **group-diversity small multiples**, a **per-sample missing-rate** chart, and a **per-site variation/missing track** along the alignment; a **degree distribution** and **hub-node** ranking with articulation points highlighted. Charts render in a web view (hover tooltips) when `PyQt6-WebEngine` is present, or as static SVG otherwise. Detail tables keep all exact values.

Conventions on missing data and interpretation:

- RNA `U` is unified to `T`; `-`/`N`/`?`/IUPAC ambiguity are not called alleles.
- Pairs below the minimum comparable sites/coverage record distance as missing — never 0 or an artificial saturation constant.
- PCoA uses classical MDS, not PCA on the distance matrix.
- A McAN directed GML keeps its direction as provenance; centrality/articulation/bridge metrics use an undirected projection.
- Topological centrality, bridging nodes, and PCoA proximity are exploratory descriptors — never automatically ancestry, origin, transmission source, or true populations.
- Tajima's D is not computed automatically, since defensible interpretation needs demographic, recombination, sampling, and null-model assumptions.

Large tables limit displayed rows/columns for responsiveness; the complete result is saved as JSON in the output directory.

## Data Export & Format Conversion

**File → Export Sequence Data** exports every record on the Data tab:

- **FASTA** — header `name|discrete|continuous`, keeping both sequence and metadata;
- **NEXUS, PHYLIP** — name and sequence only (no metadata in the identifier);
- **VCF** — sequence variants and a `NetSTSampleMetadata` header, plus a matching `_metadata.csv`;
- NEXUS, PHYLIP, and VCF require equal-length sequences; VCF also requires at least one variant site.

**File → Export Metadata** produces a standalone CSV/TSV with only `sample` and the current Metadata-tab traits.

**Tools → Sequence Format Conversion** converts between FASTA, NEXUS, PHYLIP, and VCF/VCF.GZ. Converting to VCF requires equal-length alignment, merges consecutive variant columns into valid allele blocks, and adds reference anchors for indels; a fully invariant alignment cannot produce a variants-only VCF. Input and output paths must differ.

## Output Files

Assuming a project named `project`, the main outputs are:

| File | Content |
|---|---|
| `project.fasta` | raw input sequences for this run |
| `project_aln.fasta` | aligned sequences |
| `project_seq.fasta` / `project_seq.phy` | analysis sequences with original names / PHYLIP input for fastHaN |
| `project_hap.fasta` | de-duplicated H1, H2, … haplotype sequences |
| `project_seq.meta.csv` | sample, haplotype, and trait mapping |
| `project_hap_trait.csv` / `project_seq_trait.csv` | haplotype summary / per-sample trait table |
| `project_traitconf.csv` | continuous-trait config (only when valid values exist) |
| `project.gml` | tcsBU-dialect network graph (fastHaN / RMST / McAN converted) |
| `project_rmst.json` / `project_rmst.tsv` | RMST parameters, sites, edge table, random-sampling stats (RMST only) |
| `project_mcan/` | McAN input, sample-alias mapping, original GraphML/JSON (McAN only) |
| `project_hapconf.csv` / `project_groupconf.csv` | tcsBU haplotype / group-and-colour config |
| `project.js` / `project.html` | local interactive visualization assets |
| `project_diversity_analysis.json` | sequence QC, overall/group diversity, warnings |
| `project_distance_analysis.json` | p-distance, comparable sites, PCoA eigenvalues and coordinates |
| `project_topology_analysis.json` | network overview, node/edge topology metrics, direction provenance |

The Alignment and Haplotype tabs render the first 500 sites for responsiveness; output files always keep the complete sequences.

## Project Structure

```text
NetST-py/
├── main_form.py                    # App entry, workflow orchestration, Qt background tasks
├── requirements.txt                # Python dependencies
├── netst-mac-arm64.spec            # macOS PyInstaller spec
├── netst-win.spec                  # Windows PyInstaller spec
├── docs/                           # User manuals (EN / 中文)
├── model/
│   ├── alignment_config.py         # MAFFT/MUSCLE parameters and command generation
│   ├── taxon_data.py               # Single-sequence / taxon data model
│   └── taxon_table_model.py        # Qt table model
├── service/
│   ├── file_service.py             # FASTA/CSV / encoding / standardization
│   ├── format_conversion_service.py# FASTA/PHYLIP/VCF/metadata conversion
│   ├── analysis_service.py         # Alignment, haplotype, and network pipeline
│   ├── process_service.py          # Cancellable, timeout-aware external-process control
│   ├── validation_service.py       # Analysis-input and safe filename-prefix checks
│   ├── mcan_adapter.py             # aligned FASTA ↔ McAN ↔ tcsBU format adapter
│   ├── rmst_service.py             # Native RMST process adapter and result model
│   ├── interpretation_models.py    # Immutable aligned-sequence analysis snapshot
│   ├── diversity_analysis_service.py   # QC and overall/group diversity
│   ├── distance_analysis_service.py    # Missing-aware p-distance and PCoA
│   ├── topology_analysis_service.py    # GML parsing and topology metrics
│   ├── interpretation_charts.py    # SVG chart rendering for interpretation results
│   └── gen_network_config.py       # tcsBU config and JS generation
├── ui/
│   ├── main_window_ui.py           # Main window layout
│   ├── data_tab_widget.py          # Data table tab
│   ├── metadata_tab_widget.py      # Metadata configuration tab
│   ├── alignment_tab_widget.py     # Alignment result tab
│   ├── haplotype_tab_widget.py     # Haplotype result tab
│   ├── interpretation_tab_widget.py# Structured interpretation result tab
│   ├── *_dialog.py                 # Import, conversion, and analysis-parameter dialogs
│   ├── output_panel.py             # Output directory and log panel
│   └── language_manager.py         # Chinese / English text
├── static/
│   ├── tcsbu/                      # tcsBU, D3.js, CSS, and HTML
│   ├── docs/                       # NetST and tcsBU help documents
│   └── icon/                       # Application icons
└── lib/                            # Platform MAFFT/MUSCLE/fastHaN/McAN/RMST binaries
```

**Layering** — `MainForm` extends `MainWindowUI` and orchestrates UI events and the analysis pipeline; `model/` holds and presents sample data; `service/` handles file operations, computation, and external-program lifecycle; `ui/` builds windows, tabs, and parameter collection; tcsBU is embedded as a local web app in `QWebEngineView`.

## Subprocess Control

`service/process_service.py` provides a unified runner for MAFFT, MUSCLE, fastHaN, and McAN. The RMST adapter uses the same polling approach for its native child process. Both paths honor Qt-thread cancellation; the shared runner also drains output continuously, manages process groups, and enforces tool timeouts.

## Packaging

```bash
# Install the complete build environment in a dedicated virtual environment.
python -m pip install -r requirements-build.txt

# macOS Apple Silicon → dist/NetST.app
# Windows x86-64 → dist/NetST/ (recommended directory build)
python scripts/build.py

# Optional Windows one-file build → dist/NetST.exe
python scripts/build.py --onefile
```

The build driver checks dependencies, target architecture, bundled tools and executable modes, and validates the packaged structure and QtWebEngine resources. PyInstaller builds must run natively on each target OS; they cannot be cross-compiled. See the [cross-platform packaging guide](docs/PACKAGING.zh-CN.md) for signing, notarization, release archives, and troubleshooting.

## Development Notes

- Add a menu action in `ui/menu_bar.py` and register the callback in `MainForm._get_callbacks()`.
- Add an analysis algorithm by extending the parameter dialog and implementing the service logic in `AnalysisService`; never run long tasks directly on the UI thread.
- Add an external program through `ManagedProcessRunner` to preserve cancellation, timeout, and process-tree cleanup.
- Update UI text by editing both the Chinese and English entries in `ui/language_manager.py`.
- Prefix generated files with "output directory + project name" to avoid writing into the source tree.

## Known Limitations

- No complete Linux release yet.
- Bundled external binaries must be verified per platform. Apple Silicon uses the native arm64 McAN 1.4.3 build. The McAN adapter accepts at most 30000 alignment sites.
- Native RMST uses a dense pairwise distance matrix and complete graph; exact mode caps at 1000 filtered nodes and random mode at 500 nodes with bounded work.
- VCF sequence conversion is limited to single-contig, non-overlapping small variant records; no structural variants, breakends, or symbolic ALTs.
- Full GUI interaction, platform packaging, and real-data end-to-end workflows need manual verification on target systems.
- The dependency-free PCoA solver defaults to 200 sequences; larger sets still output the distance matrix but skip PCoA with a warning.
- The current interpretation analytics are descriptive/exploratory; trait significance, FST/AMOVA, community stability, and demographic null models are out of scope for this stage.
- tcsBU depends on Qt WebEngine; without `PyQt6-WebEngine` the network tab falls back to a degraded text widget.

## Citation

If you use NetST in your research, please cite:

> Zhang Z, Yu Y. *NetST: An integrated software for large-scale haplotype network construction, visualization, and automated analytics.*

Please also cite the dependencies you use: fastHaN (Chi et al. 2023), tcsBU (Múrias Dos Santos et al. 2016), MAFFT (Nakamura et al. 2018), RMST (Paradis 2018), and McAN (Li et al. 2022). See the [user manual](docs/NetST-User-Manual.md#16-citation--acknowledgements) for full references.

## License

MIT License
