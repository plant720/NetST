# Rhodiola bupleuroides plastome haplotype network example for NetST

This example contains population-scale chloroplast genome haplotype data
from *Rhodiola bupleuroides* used for demonstrating haplotype network
construction and metadata visualization in NetST.

The dataset represents maternal lineage structure of an alpine herb
distributed across the Qinghai–Xizang Plateau. Complete chloroplast
genomes from 468 individuals belonging to 19 natural populations were
analyzed, and haplotype relationships were visualized using a minimum
spanning network (MSN) implemented in NetST.

## Files

| File | Description |
|---|---|
| `Rhodiola_bupleuroides_chloroplast.fasta` | 468 pre-aligned chloroplast genome sequences (~65 MB) |
| `metadata.csv` | Sample metadata with columns `sample`, `group`, and `value` |
| `1-s2.0-S2468265926001411-main.pdf` | The published reference article |

## Dataset overview

- Species: *Rhodiola bupleuroides*
- Marker type: complete chloroplast genome
- Number of samples: 468
- Number of populations: 19
- Recommended network algorithm: Minimum Spanning Network (MSN)

### Metadata columns

| Column | Type | Description |
|---|---|---|
| `sample` | ID | Sample identifier, matches FASTA headers |
| `group` | Categorical | Maternal genetic cluster assignment |
| `value` | Continuous | Sampling elevation in meters (range: 3,200–5,200 m) |

Four maternal genetic clusters are represented:

| Cluster | Samples |
|---|---:|
| Cluster_1 | 41 |
| Cluster_2 | 145 |
| Cluster_3 | 165 |
| Cluster_4 | 117 |

## Suggested NetST workflow

### 1. Load sequence data

Load `Rhodiola_bupleuroides_chloroplast.fasta` via File > Load FASTA.
The sequences are pre-aligned, so no MSA step is needed. NetST will
proceed directly to haplotype identification.

### 2. Load metadata

Load `metadata.csv` via File > Load Metadata.

Map the columns as follows:

| Column | NetST annotation | Description |
|---|---|---|
| `sample` | Sample ID | Sequence identifier |
| `group` | Categorical trait | Maternal genetic cluster |
| `value` | Continuous trait | Sampling elevation |

### 3. Construct haplotype network

Run Analysis > Build Haplotype Network and select MSN.

## Metadata visualization

- **Node size** represents haplotype frequency — larger nodes indicate
  haplotypes shared by more individuals.
- **Node color** represents maternal genetic cluster — the four clusters
  correspond to lineage groups identified from population genetic analyses.
- **Continuous trait mapping** — the `value` column (elevation) can be
  displayed as a gradient, allowing visualization of haplotype
  distribution along elevation gradients.

## Biological interpretation

The original study identified 177 chloroplast haplotypes and showed that
haplotype relationships were structured among four maternal lineages.
Different lineages displayed contrasting network architectures, including
star-like and more complex internal structures.

Network topology alone does not represent direct evidence of ancestry,
migration direction, or evolutionary causality. Interpretation should be
integrated with complementary analyses, including phylogenetic
reconstruction, population differentiation statistics, and landscape
genetic analyses.

## Notes

- This is the largest example dataset (~65 MB). Network construction may
  take longer than the other examples.
- The sequences are pre-aligned (uniform length), so no MSA step is required.

## Reference

Hou J-Q, Shi Y, Song Y-X, et al. Topographic fragmentation shapes
maternal lineage divergence and plastome variation in the seed dispersal
limited alpine herb *Rhodiola bupleuroides*. *Plant Diversity* (2026).
DOI: 10.1016/j.pld.2026.06.006

If you use this dataset, please cite the reference above.
