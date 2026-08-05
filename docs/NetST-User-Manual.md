# NetST — User Manual & Software Guide

> 🌐 **English** | [中文](NetST-使用手册.md)

> **NetST — Haplotype Network Analysis Tool / 单倍型网络分析工具**
> Interface version: **2.0.0**　·　Audience: researchers in population genetics, phylogeography, and molecular epidemiology
>
> This manual describes **NetST-py**, the PyQt6 rewrite. It keeps the core workflow of the legacy VB.NET NetST while rewriting and extending data import, network construction, visualization, and interpretation. Its content follows the current source code and `README.md`. Some features mentioned in older promotional material — community detection, modularity analysis, automatic Tajima's D, dual-trait ANOVA association — are **not** provided in this version and are deliberately omitted here to avoid misleading readers.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Workflow at a Glance](#2-workflow-at-a-glance)
3. [Installation & Running](#3-installation--running)
4. [Interface Overview](#4-interface-overview)
5. [Quick Start (Example Data)](#5-quick-start-example-data)
6. [Data Import & Preprocessing](#6-data-import--preprocessing)
7. [Metadata Management & Visualization Config](#7-metadata-management--visualization-config)
8. [Alignment & Haplotype Identification](#8-alignment--haplotype-identification)
9. [Haplotype Network Construction](#9-haplotype-network-construction)
10. [Network Visualization (tcsBU)](#10-network-visualization-tcsbu)
11. [Interpretation Analysis](#11-interpretation-analysis)
12. [Data Export & Format Conversion](#12-data-export--format-conversion)
13. [Output Files](#13-output-files)
14. [Methods & Algorithms](#14-methods--algorithms)
15. [FAQ & Known Limitations](#15-faq--known-limitations)
16. [Citation & Acknowledgements](#16-citation--acknowledgements)
17. [Contact](#17-contact)

---

## 1. Overview

**NetST** is an integrated analysis platform for large-scale, multi-trait haplotype datasets. It covers the full path from raw sequences to interactive network visualization, unifying several established bioinformatics engines (MAFFT, MUSCLE, fastHaN, McAN) with built-in algorithms (RMST, interpretation analytics) in a single graphical interface. Every long-running task runs on a background thread and can be cancelled at any time.

**Core capabilities**

- **Multi-format import**: FASTA, NEXUS, PHYLIP, VCF/VCF.GZ; metadata can be parsed from sample IDs or imported separately from CSV/TSV.
- **Multiple network algorithms**: Original TCS, Modified TCS, MSN, MJN (fastHaN), built-in RMST, and McAN minimum-cost arborescence network.
- **Multi-trait concentric-ring visualization**: an enhanced tcsBU / D3.js view overlays several categorical and continuous traits as concentric rings with a matching legend; export to SVG/PNG/JPG.
- **Interpretation module**: visual quality, diversity, genetic-distance/PCoA, and network-topology metrics that help you understand the data and network at a glance.
- **Bilingual UI**: menus, tabs, table headers, logs, and result summaries refresh together on a language switch.

**Design principle**: topological description and biological inference are strictly separated. Centrality, bridges, PCoA proximity, etc. are **exploratory descriptors**; the software never automatically equates them with ancestry, origin, transmission source, or true populations.

---

## 2. Workflow at a Glance

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

| Stage | Module | Notes |
|---|---|---|
| Import & preprocess | File menu + standardization dialog | Four sequence formats + separate metadata table; clean/split sample IDs at import |
| Alignment | MAFFT / MUSCLE | Runs automatically during network construction; can also be run alone under Tools |
| Haplotype identification | built-in | Collapses identical aligned sequences into unique haplotypes (H1, H2, …) |
| Network construction | fastHaN / RMST / McAN | Six algorithms, unified GML output |
| Visualization | tcsBU / D3.js | Multi-trait concentric rings + legend, interactive layout |
| Interpretation | built-in pure computation | Quality/diversity, genetic distance/PCoA, network topology |

---

## 3. Installation & Running

### 3.1 Release build (recommended for end users)

- Download the platform package from [NetST GitHub Releases](https://github.com/sculab/NetST/releases).
- Extract and launch from **inside** the extracted directory (`NetST.app` on macOS, `NetST.exe` on Windows). No installation required.
- **Important**: run the program from within the extracted NetST folder. External dependencies (MAFFT, MUSCLE, fastHaN, McAN) are bundled and linked per platform.

| Platform | Run from source | Bundled analysis programs | PyInstaller spec |
|---|:---:|---|---|
| macOS Apple Silicon | Yes | MAFFT, MUSCLE 3, fastHaN, McAN 1.4.3 arm64 | `netst-mac-arm64.spec` |
| Windows x86-64 | Yes | MAFFT, MUSCLE 3, fastHaN, McAN 1.4.3 | `netst-win.spec` |
| Linux | Code path exists | Provide your own | Not provided |

> McAN is bundled for both supported platforms. NetST probes the executable and automatically selects the version-specific output option.

### 3.2 Run from source (developers / Linux users)

Use Python 3.10 and an isolated virtual environment.

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_form.py
```

**Windows PowerShell**

```powershell
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main_form.py
```

Main Python dependencies: `PyQt6`, `PyQt6-WebEngine`, and `chardet` (`PyInstaller` is only needed to build releases). RMST does not require NumPy. If the bundled MAFFT is unavailable, the program falls back to a system `mafft` on `PATH`.

### 3.3 Packaging

```bash
python -m pip install -r requirements-build.txt
python scripts/build.py

# Optional Windows one-file mode
python scripts/build.py --onefile
```

macOS produces `dist/NetST.app`; Windows produces the complete `dist/NetST/` directory by default. The build driver checks dependencies, architecture, bundled tools, the packaged structure, and Qt WebEngine resources. Build natively on each target OS. See `docs/PACKAGING.zh-CN.md` for signing, notarization, and release packaging.

---

## 4. Interface Overview

The main window has a **menu bar**, a **tabbed workspace**, and a bottom **status bar**.

### 4.1 Menu bar

| Menu | Items |
|---|---|
| **File** | Import FASTA / NEXUS / PHYLIP / VCF; Load Metadata (CSV/TSV); Export Sequence Data; Export Metadata; Exit |
| **Analysis** | **Build / Rebuild Haplotype Network**; **Interpretation Analysis** ▸ Sequence Quality and Diversity / Genetic Distance and PCoA / Network Topology Metrics |
| **Tools** | Multiple Sequence Alignment (alignment only); Calculate Haplotype (align + haplotypes, no network); Sequence Format Conversion; Language (中文 / English) |
| **Help** | About; TCS-BU Help; NetST Help |

### 4.2 Tabbed workspace

| Tab | Content |
|---|---|
| **Home** | Software positioning, core capabilities, quick workflow, supported algorithms, and I/O overview |
| **Network** | Interactive tcsBU haplotype network (embedded Qt WebEngine) |
| **Data** | Sequence table: ID, name, sequence (read-only), analysis checkbox; names/selection/traits are editable |
| **Metadata** | Appears after metadata import: configure each trait's type, Group, visibility, and colour |
| **Haplotype** | Haplotype summary and sample-to-haplotype mapping |
| **Alignment** | Alignment matrix (renders the first 500 sites for responsiveness) |
| **Interpretation** | Structured interpretation results: overview KPI cards, chart visualizations, detail tables |

> In the tcsBU Network view, the Data (left) and Info (right) side panels can be collapsed and drag-resized to give the network more room.

### 4.3 Status bar

While an analysis runs, the bottom of the window shows a progress bar and a **Cancel** button. Cancelling requests the background task to stop and terminates the entire process group of the current external program; the same cleanup runs when the program closes or a new task replaces an old one.

---

## 5. Quick Start (Example Data)

Two SARS-CoV-2 example datasets are provided:

- **SL-SARS-CoV-2**: 130 representative haplotypes distinguishing the L / S lineages (categorical trait).
- **DP-SARS-CoV-2**: 482 genome sequences (72 from the Diamond Princess + 410 worldwide) with geographic location (categorical) and collection date (continuous).

Shortest path using DP-SARS-CoV-2:

1. **File → Import FASTA**, choose `DP-SARS-CoV-2.fasta`.
2. In the **standardization dialog**, set the delimiter to `|` and map field positions: `0 = sample name`, `1 = categorical trait (region)`, `2 = continuous trait (collection day)`.
3. On the **Data** tab, review the data and tick the samples to include (all selected by default).
4. On the right, enter a **project name** and choose the **output directory** (default `~/HaplotypeOutput`).
5. **Analysis → Build / Rebuild Haplotype Network**, pick an algorithm (e.g. Original TCS), and run. NetST automatically performs alignment → haplotype identification → construction → visualization.
6. View the interactive network on the **Network** tab; inspect intermediate results on **Alignment / Haplotype**.
7. For statistical interpretation, run any analysis under **Analysis → Interpretation Analysis**; results appear on the **Interpretation** tab.
8. Export via **File → Export Sequence Data** or the toolbar **Save Image**.

> A FASTA header like `>DP0005|DP|54|1|Human` encodes (name | region | collection day | quantity | organism). Field positions are 0-based; use only the fields you need.

---

## 6. Data Import & Preprocessing

### 6.1 Supported sequence formats

| Format | Menu | Notes |
|---|---|---|
| **FASTA** | File → Import FASTA | Whitespace in headers is normalized to underscores so PHYLIP/fastHaN don't split a name into fields |
| **NEXUS** | File → Import NEXUS | DNA/RNA MATRIX in DATA/CHARACTERS blocks: sequential, interleaved, quoted names, nested comments, `MATCHCHAR` |
| **PHYLIP** | File → Import PHYLIP | Sequential and common interleaved; the declared count and length must match the data |
| **VCF / VCF.GZ** | File → Import VCF | See [§6.3](#63-vcf-import) |

The three non-VCF formats all enter the same **name-standardization dialog** and load into the Data tab as the current raw data. A failed import does not overwrite existing table data.

### 6.2 Standardization dialog (sample-ID handling)

The import dialog can:

- **clean / replace** characters in sample names;
- extract **sample name, categorical trait, continuous trait** from a composite header by **delimiter + 0-based field index** (compatible with legacy headers like `sample_01|population_A|12.5`);
- or process only the sample name and later import multiple traits via **File → Load Metadata**;
- optionally **filter sequences containing `RYSWKMBDHVN` ambiguity codes**.

Continuous traits must be valid numbers.

### 6.3 VCF import

**File → Import VCF** accepts VCF / VCF.GZ with per-sample genotype columns. The sequence workflow targets a **single sequence region**, so the VCF must contain a single contig and each record must carry a `GT` field.

**Metadata file (optional)**

| Provided as | Effect |
|---|---|
| None | metadata parsed from sample IDs only |
| Plain CSV/TSV | matched by sample name; fills categorical (group) and continuous traits |
| McAN six-column TSV | fills a categorical trait merged from Country/State/City; **if sample names are unchanged**, enables native McAN VCF analysis and keeps real sampling dates for network orientation |

> McAN six-column format: `SampleName AccessionID SamplingDate Country State City`, missing values as `*`, header optional. If you rename/remove samples in standardization or later edit the table, the program automatically falls back to the aligned-FASTA → mutation adapter path.

**Alignment reconstruction rules**

- **No reference FASTA**: each VCF record becomes an equal-width variant-site block, producing a "variant-sites-only alignment".
- **With reference FASTA**: each VCF `REF` is validated against the reference; invariant regions are filled back to produce a full-length alignment.
- Multi-allelic sites resolve by GT allele number; heterozygous single-base sites use IUPAC codes, heterozygous complex indels use `N`.
- Symbolic ALTs, breakends, multiple contigs, and mutually overlapping records are explicitly rejected.

---

## 7. Metadata Management & Visualization Config

### 7.1 Importing metadata from CSV/TSV

**File → Load Metadata** imports a standalone metadata table. The first row is a header, and at least one column must map 1-to-1 to already-imported sequence names:

```csv
sample,population,value
sample_01,population_A,12.5
sample_02,population_B,13.1
```

The delimiter is auto-detected from the first data row (tab preferred). Each column can be set to **Sample name / Ignore / Categorical trait / Continuous trait**; you may select any number of traits at once, but **at least one categorical trait must be designated as the Group**. The program checks that sample names match completely on both sides and rejects duplicate names on either side, preventing silent overwrite or mismatch.

For every Continuous column, click **Continuous conversion** and choose one rule:

| Input type | Accepted input and output |
|---|---|
| Plain number | Strict finite numeric values; blanks remain blank |
| Date / time | `YYYY-MM-DD`, `YYYY/MM/DD`, `YYYY-MM`, `YYYY`, or ISO date-time → elapsed days, calendar months, or calendar years from a selected start date; blank start means the earliest valid date |
| Measurement with unit | Length (`mm/cm/m/km/in/ft`), mass (`mg/g/kg`), or temperature (`°C/°F/K`) → one selected output unit; choose the assumed source unit for bare values |

The preview checks the complete column, not only the visible first rows. Invalid
input prevents confirmation and identifies its original metadata row. Conversion
does not edit the source file; the normalized numeric result is stored in the
current Data table and feeds the ordinary continuous visualization path. Calendar
intervals are intuitive: the same day in the next month is exactly 1 month, and
the same date in the next year is exactly 1 year; partial intervals remain
fractional so the colour gradient stays continuous.

### 7.2 The Metadata tab

After import, a **Metadata** tab appears. Each row is one trait; you can switch categorical/continuous, choose the single Group, toggle visibility, and edit colours (categorical palette or continuous low/high endpoints, via a colour picker or a hex value). Categorical traits with 2–10 classes use curated class-count-specific palettes; larger sets receive stable, non-repeating generated colours. The default continuous gradient is gray (`#BDBDBD`) to black (`#000000`). The program prevents deleting the last categorical Group.

Network nodes draw **concentric rings** in the order of the Metadata table: the **Group innermost**, then other enabled traits outward. A categorical ring is segmented by the class proportions of a haplotype's members; a continuous ring first sorts member values numerically from low to high, then draws the sectors in that order using the trait's range and gradient. The tcsBU **Legend** lists every class swatch and continuous gradient range in the same inner-to-outer order.

### 7.3 When to rebuild vs. only refresh the visualization config

> Network **topology** is determined by the input samples and sequences; the metadata's types, grouping, rings, and colours only decide **how** existing topology is displayed.

| Change | Action |
|---|---|
| Import a new FASTA/NEXUS/PHYLIP/VCF | **Rebuild** the haplotype network |
| Change sample names, sequences, or the analysis selection | **Rebuild** the haplotype network |
| Change the network algorithm/parameters | **Rebuild** the haplotype network |
| Import or edit metadata values | Only click **Apply Visualization Config** on the Metadata tab |
| Change trait type, Group, Visualize, or colour | Only click **Apply Visualization Config** |
| Adjust group names, colours, or sample-group membership in tcsBU | Only update the current visualization config |

A lightweight refresh rewrites only tcsBU's `_hapconf.csv`, `_groupconf.csv`, `_traitconf.csv`, the embedded-data `.js`, and `.html`; the existing `.gml`, alignment, and sample-to-haplotype mapping are unchanged (identical sequences keep the same H1/H2… labels).

---

## 8. Alignment & Haplotype Identification

### 8.1 Multiple-sequence alignment (MSA)

NetST aligns with **MAFFT** (several modes) or **MUSCLE**:

| MAFFT mode | Character |
|---|---|
| Auto | automatic selection |
| FFT-NS-1 | very fast, rough |
| FFT-NS-2 | fast |
| G-INS-i | global, slower |
| L-INS-i | local, most accurate |
| E-INS-i | long unaligned regions |

- **Full network analysis**: if input lengths differ, MAFFT runs first, falling back to MUSCLE on failure; equal lengths are treated as already aligned and go straight to haplotype processing.
- **Tools → Multiple Sequence Alignment**: alignment only, for visual inspection or fine-tuning; most users do not need it separately.

### 8.2 Haplotype identification

- **Tools → Calculate Haplotype**: align and compute haplotypes without building a network.
- Identical aligned sequences collapse into unique haplotypes (H1, H2, …) to streamline the network. Results appear on the **Haplotype** tab and generate `project_hap.fasta`, `project_seq.meta.csv`, etc.

---

## 9. Haplotype Network Construction

**Analysis → Build / Rebuild Haplotype Network** opens the construction dialog. Pick an algorithm and parameters to run alignment → haplotype identification → construction → visualization in one step.

### 9.1 Algorithms & parameters

| Algorithm | Engine ID | Parameters | Ideal for |
|---|---|---|---|
| **Original TCS** (statistical parsimony) | `original_tcs` | threads, ambiguous sites, merge intermediate nodes | intraspecific phylogeography, shallow divergence |
| **Modified TCS** | `modified_tcs` | threads | improved TCS variant |
| **MSN** (minimum spanning) | `msn` | epsilon | closely related, low-divergence populations |
| **MJN** (median-joining) | `mjn` | threads, epsilon | recombination/missing data, ancestral inference |
| **RMST** (randomized minimum spanning tree) | `rmst` | exact/random mode, replicates, random seed, exclude ambiguous sites | bundled native engine, see [§14.1](#141-rmst-built-in-implementation) |
| **McAN** (minimum-cost arborescence) | `mcan` | threads, reference sequence, exclude ambiguous sites | directed inclusion network, see [§14.2](#142-mcan-adapter) |

### 9.2 Choosing an algorithm

- **MSN**: simplest connectivity — intraspecific / population-level, low-divergence data.
- **MJN**: accommodates reticulate evolution and infers ancestral haplotypes — complex reconstructions, ancient DNA, viral dynamics.
- **TCS**: 95% connection threshold for statistically reliable links — intraspecific phylogeography.
- **RMST**: bundled native C++ engine; exact mode is deterministic and reproducible — a fast, robust default.
- **McAN**: a mutation-inclusion network rooted at the reference; time-orientable when real sampling dates are provided.

---

## 10. Network Visualization (tcsBU)

The network renders on the **Network** tab with an enhanced **tcsBU / D3.js** view embedded in Qt WebEngine.

### 10.1 Multi-trait concentric rings

Each haplotype node is drawn as concentric rings: **Group innermost**, other enabled traits outward. Node size scales with frequency. The **Legend** lists every class swatch and continuous gradient range in inner-to-outer order.

### 10.2 Toolbar

- **Save Image**: export **SVG (vector) / PNG / JPG**, then choose a location in the system save dialog. SVG is standard `image/svg+xml`; PNG/JPG default to 2× resolution.
- **Zoom In / Zoom Out**, **Delete Node / Delete Link** (interactive editing).
- **Legend**: show/hide the legend.
- **Haplotype / Distance**: show haplotype labels / per-edge mutation-distance labels.
- **Advanced**: open the advanced-settings dialog (below).

### 10.3 Advanced settings dialog

The dialog can be **moved by dragging its title bar** and is organized into three sections:

**Force-Directed Layout Settings** — Link Distance, Link Strength, Friction, Charge, Gravity, plus Start / Stop.

**Node and Edge Settings**

| Parameter | Meaning | Default |
|---|---|---|
| Node Radius | radius (px) of a frequency-1 haplotype node; preserves relative sizes when adjusted | 5 |
| **Node Line Width** | node outline stroke width | 1.5 |
| **Edge Line Width** | base edge (link) line width | 1.5 |
| **Edge Weight Scale** | maximum Edge Line Width multiplier when Edge Weight is enabled | 4 |
| Text Offset | label offset beside a node | 5 |

**Metadata Ring Settings**

| Parameter | Meaning | Default |
|---|---|---|
| **Ring Line Width** | ring-segment stroke width | 0.5 |
| Base Ring Width | base thickness (px) of each non-Group outer ring at ratio 1; actual = base × ring ratio | 7 |
| Outer Ring Ratios | comma-separated ratios inner→outer (missing values use 1) | — |

> Node/Edge Line Width are independent, separately adjustable parameters. Edge Weight reads the numeric Changes distance and scales every edge from the configured base line width; fewer changes produce thicker edges.

### 10.4 Read-only Data column

The **Sequence column on the Data tab is read-only** to prevent accidental edits from invalidating an existing alignment, haplotypes, and network. Sample names, selection state, and metadata traits remain editable.

---

## 11. Interpretation Analysis

**Analysis → Interpretation Analysis** offers three pure-computation analyses. The computation layer uses an **immutable aligned-sequence snapshot**, decoupled from the UI and file output, and runs on a background thread (cancellable). Results appear on the **Interpretation** tab and are saved as JSON.

| Menu item | Input & computation | Main results |
|---|---|---|
| **Sequence Quality and Diversity** | current selected equal-length aligned sequences; complete or pairwise deletion | per-sample/per-site missing rates, effective sites, variable sites, parsimony-informative sites, S, Hd, π, θW, group richness, private haplotypes |
| **Genetic Distance and PCoA** | only A/C/G/T as called states; gap, N, ?, and IUPAC ambiguity pairwise-deleted | p-distance matrix, comparable sites per pair, PCoA coordinates, positive/negative eigenvalue diagnostics |
| **Network Topology Metrics** | the current project GML, or a user-selected tcsBU-compatible GML | node/edge counts, connected components, density, cycle rank, degree, closeness, betweenness, articulation points, bridges |

Before running, **Sequence Quality and Diversity** and **Genetic Distance and PCoA** show a parameter dialog: the former offers the missing-data policy (complete / pairwise deletion) and the categorical trait used for grouping; the latter sets the minimum comparable sites and minimum comparable coverage.

### 11.1 Result-tab visualizations

The Interpretation tab organizes results as **Overview + Charts + Detail tables** so you can grasp the data and network intuitively:

- **Overview**: a row of colour-coded **KPI cards** (e.g. missing rate graded green/amber/red), alongside a full metrics table and warnings/notes.
- **Charts (Visualizations)**:
  - *Diversity*: group-diversity small multiples (N / haplotypes / Hd / π / θW), a per-sample missing-rate bar chart (coloured by threshold), and a **per-site variation-and-missing "track"** along the alignment (dark = parsimony-informative; bottom lane = missing-rate heat strip).
  - *Distance/PCoA*: a **PCoA ordination scatter** (coloured by group, with legend and explained-variance axis labels) and a **genetic-distance heatmap** (grey cells = too few comparable sites, distance unavailable).
  - *Topology*: a node-degree histogram and a hub-node betweenness ranking (**articulation points highlighted red**).
- **Detail tables**: retain all exact values for reference and cross-checking.

> With `PyQt6-WebEngine`, charts render in a web view with hover tooltips; otherwise they fall back to static SVG (equally complete). Large tables limit displayed rows/columns for responsiveness; the complete result is always saved as JSON.

### 11.2 Missing-data & interpretation conventions

- RNA `U` is unified to `T` internally; `-`/`N`/`?`/IUPAC ambiguity are not treated as called alleles.
- Sequence pairs below the minimum comparable sites or coverage record distance as **missing** — never filled with 0 or an artificial saturation constant.
- PCoA uses classical multidimensional scaling; it does not run PCA on the distance matrix as if it were ordinary features.
- The direction of a McAN directed GML is kept as provenance; current centrality, articulation, and bridge metrics use an **undirected projection**.
- **Topological centrality, bridging nodes, and PCoA proximity are exploratory descriptors — never automatically equated with ancestry, origin, transmission source, or true populations.**
- **Tajima's D is not computed automatically**, because defensible interpretation requires demographic, recombination, sampling, and null-model assumptions.

---

## 12. Data Export & Format Conversion

### 12.1 Export

**File → Export Sequence Data** exports all records on the Data tab:

| Target format | Notes |
|---|---|
| FASTA | header `name\|discrete\|continuous`, preserving both sequence and metadata |
| NEXUS / PHYLIP | writes name and sequence only (no metadata in the identifier); requires equal-length sequences |
| VCF | writes sequence variants and a `NetSTSampleMetadata` header, plus a matching `_metadata.csv`; requires equal length and at least one variant site |

**File → Export Metadata** produces a standalone CSV/TSV metadata table with only `sample` and the traits on the current Metadata tab.

### 12.2 Sequence format conversion

**Tools → Sequence Format Conversion**:

| Input | Output | Notes |
|---|---|---|
| FASTA | NEXUS, PHYLIP, VCF | NEXUS/PHYLIP require equal length; VCF can specify a reference sample |
| NEXUS | FASTA, PHYLIP, VCF | reads DATA/CHARACTERS matrix; sequential, interleaved, MATCHCHAR |
| PHYLIP | FASTA, NEXUS, VCF | sequential or common interleaved; declared count/length must be correct |
| VCF / VCF.GZ | FASTA, NEXUS, PHYLIP | reference FASTA optional; without it, a variant-sites alignment is produced |

> Converting to VCF requires equal-length aligned sequences; consecutive variant columns are merged into valid allele blocks and reference anchors are added for indels. A fully invariant alignment cannot produce a variants-only VCF. Input and output paths must differ.

---

## 13. Output Files

All generated files share the "output directory + project name" prefix (examples use `project`):

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
| `project_mcan/` | McAN input, sample-alias mapping, and original GraphML/JSON (McAN only) |
| `project_hapconf.csv` / `project_groupconf.csv` | tcsBU haplotype / group-and-colour config |
| `project.js` / `project.html` | local interactive visualization assets |
| `project_diversity_analysis.json` | sequence QC, overall/group diversity, and computation warnings |
| `project_distance_analysis.json` | p-distance, comparable sites, PCoA eigenvalues and coordinates |
| `project_topology_analysis.json` | network overview, node/edge topology metrics, direction provenance |

> The Alignment and Haplotype tabs render only the first 500 sites for responsiveness; output files always keep the complete sequences.

---

## 14. Methods & Algorithms

### 14.1 RMST built-in implementation

RMST (Randomized Minimum Spanning Tree) is implemented by the bundled dependency-free C++17 `netst-rmst` executable. It reads `project_hap.fasta` and `project_seq.meta.csv` and computes uncorrected mutation counts (Hamming distance) over unique haplotypes. Two modes:

- **Exact mode (default, recommended)**: by distance layer, determines all edges that can appear in at least one minimum spanning tree; deterministic and seed-independent.
- **Random mode**: repeatedly randomizes haplotype order and runs stable Kruskal, reporting each edge's occurrence count and frequency; a fixed seed is reproducible, but finite replicates do not guarantee finding every compatible edge.

The native random mode uses a platform-independent SplitMix64 permutation stream. A seed is stable between the new macOS and Windows binaries, but it does not reproduce the historical NumPy RNG stream byte-for-byte.

By default any alignment column containing a character outside `A/C/G/T/U/-` is excluded, RNA `U` is unified to `T`, and gap is a comparable state. Haplotypes that become identical after filtering are merged with their sample members into one node, recorded in the JSON `warnings` and node `haplotypes` fields. Scale limits: exact mode ≤ 1000 filtered nodes; random mode ≤ 500 nodes and ≤ 1000 replicates.

> Reference: Paradis, E. (2018) *Analysis of haplotype networks: The randomized minimum spanning tree method.* Methods in Ecology and Evolution 9:1308–1317.

### 14.2 McAN adapter

McAN natively accepts a VCF or mutation + metadata + site mask and outputs GraphML/JSON. `service/mcan_adapter.py` supports two paths:

- **Native VCF path**: importing a VCF with McAN six-column metadata and unchanged sample names calls `McAN --vcf` directly, keeping real sampling dates for network orientation.
- **Mutation adapter path**: FASTA/PHYLIP sources, VCFs without metadata, or samples renamed/edited:
  1. read the aligned FASTA and compute per-site differences against the chosen reference;
  2. generate mutation/metadata with internal aliases like `S0000001` to avoid GraphML corruption from unescaped names;
  3. produce an explicit site mask (optionally excluding columns with non-A/C/G/T/U/gap characters);
  4. call McAN in a dedicated `project_mcan/` directory, preserving the original GraphML/JSON;
  5. convert to a tcsBU-readable GML, restoring original names and network distances.

> NetST limits the maximum McAN sequence coordinate to 30000 and rejects longer alignments before calling it. The adapter automatically selects McAN 1.2 `--outDir` or McAN 1.4.x `--out`, and supports both GraphML formats. When a FASTA has no sampling dates, it does not fabricate a time order — it yields a mutation-inclusion network rooted at the reference.
> Reference: Li, L. et al. (2022) *McAN: an ultrafast haplotype network construction algorithm.* bioRxiv 2022.07.23.501111.

### 14.3 Interpretation metric definitions

- **Sequence quality**: per-sample/per-site missing, gap, unknown, and ambiguity counts and rates; effective sites, variable sites, parsimony-informative sites.
- **Diversity**: haplotype richness, haplotype diversity Hd, nucleotide diversity π, Watterson's θW, segregating sites S, group private haplotypes.
- **Genetic distance**: pairwise-deletion p-distance, reporting the effective comparable sites for each pair.
- **PCoA**: classical multidimensional scaling (the dependency-free solver defaults to ≤ 200 sequences; larger sets still output the distance matrix but skip PCoA with a warning).
- **Network topology**: connected components, density, cycle rank (independent loops), degree, closeness, betweenness, articulation points, bridges. Mutation count is always treated as distance, never as stronger connectivity.

---

## 15. FAQ & Known Limitations

**Q: Why is there no Tajima's D / community detection / dual-trait significance test in Interpretation?**
A: These are deliberately not provided. Defensible interpretation of Tajima's D, FST/AMOVA, community stability, and demographic null models requires extra sampling, recombination, and null-model assumptions beyond the scope of the current descriptive/exploratory analytics.

**Q: I edited metadata or colours — do I need to rebuild the network?**
A: No. As long as sequences and the sample set are unchanged, click **Apply Visualization Config** on the Metadata tab (see [§7.3](#73-when-to-rebuild-vs-only-refresh-the-visualization-config)).

**Q: The network view is blank / text only?**
A: tcsBU depends on Qt WebEngine. Without `PyQt6-WebEngine`, the network tab falls back to a degraded text widget; install that dependency.

**Known limitations**

- No complete Linux release yet; Linux needs compatible external programs supplied by the user.
- Bundled external binaries are platform-specific and cannot be used across architectures. Windows ships static-runtime x86-64 McAN and RMST executables; Linux engines must still be supplied separately.
- The McAN adapter accepts at most 30000 alignment sites.
- Native RMST: exact mode ≤ 1000 nodes and random mode ≤ 500 nodes; randomized work is additionally bounded at 50 million edge evaluations.
- VCF sequence conversion is limited to single-contig, non-overlapping small variant records; no structural variants, breakends, or symbolic ALTs.
- The dependency-free PCoA solver defaults to ≤ 200 sequences.
- Full GUI interaction, platform packaging, and real-data end-to-end workflows need manual verification on target systems.

---

## 16. Citation & Acknowledgements

If you use NetST in your research, please cite:

> Zhang Z, Yu Y. *NetST: An integrated software for large-scale haplotype network construction, visualization, and automated analytics.*

Please also cite the relevant dependencies:

- Chi L, Zhang X, Xue Y, Chen H. 2023. *fastHaN: a fast and scalable program for constructing haplotype network for large-sample sequences.* Mol Ecol Resour. https://doi.org/10.1111/1755-0998.13829
- Múrias Dos Santos A, et al. 2016. *tcsBU: a tool to extend TCS network layout and visualization.* Bioinformatics 32:627–628.
- Nakamura T, et al. 2018. *Parallelization of MAFFT for large-scale multiple sequence alignments.* Bioinformatics 34:2490–2492.
- Paradis E. 2018. *Analysis of haplotype networks: The randomized minimum spanning tree method.* Methods Ecol Evol 9:1308–1317.
- Li L, et al. 2022. *McAN: an ultrafast haplotype network construction algorithm.* bioRxiv 2022.07.23.501111.

Example-data citation:

- DP-SARS-CoV-2: Sekizuka T, et al. 2020. *Haplotype networks of SARS-CoV-2 infections in the Diamond Princess cruise ship outbreak.* PNAS 117:20198–20201.

---

## 17. Contact

For any questions, suggestions, or comments about NetST, please contact:
[yyu@scu.edu.cn](mailto:yyu@scu.edu.cn)　·　[zzhen0302@163.com](mailto:zzhen0302@163.com)

---

*This manual is based on the current NetST-py source and README and may change as the software evolves. License: MIT.*
