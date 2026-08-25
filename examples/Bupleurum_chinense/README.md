# Bupleurum chinense phylogeography example for NetST

This example contains multi-locus nuclear gene sequence data (MOR1 and XTH7) from a phylogeographic study of *Bupleurum chinense* (Apiaceae) by Song et al. (2026). The dataset demonstrates NetST's ability to handle multiple loci and multi-trait metadata with both discrete and continuous traits.

## Files

| File | Description |
|---|---|
| `b.chinense.MOR1.fasta` | 76 sequences of the nuclear gene MOR1 (3,377 bp each). FASTA headers use plain sample names (e.g. `>Bupleurum_chinense_EMS1`). |
| `b.chinense.XTH7.fasta` | 78 sequences of the nuclear gene XTH7 (748 bp each). FASTA headers use pipe-delimited format `name|group|height` (e.g. `>Bupleurum_chinense_EMS1|B|35`), which NetST can parse automatically during import. |
| `b.chinense.MOR1.meta.csv` | Metadata CSV with columns `sample`, `group`, and `height`. Applies to both loci. |
| `Figure1.jpg` | Reference figure from the published article. |
| `Yu -3P, 2026.pdf` | The published reference article. |

## Dataset overview

- Species: *Bupleurum chinense*
- Marker type: nuclear genes (MOR1, XTH7)
- MOR1: 76 sequences, 3,377 bp each
- XTH7: 78 sequences, 748 bp each

### Metadata columns

| Column | Type | Description |
|---|---|---|
| `sample` | ID | Sample identifier, matches FASTA headers |
| `group` | Categorical | Phylogeographic group: A (45 samples) or B (31 samples) |
| `height` | Continuous | Plant height in cm (range: 25–130) |

## Usage in NetST

### MOR1 analysis

1. Load `b.chinense.MOR1.fasta` via File > Load FASTA.
2. Load `b.chinense.MOR1.meta.csv` via File > Load Metadata to assign groups (A/B) and plant height values.
3. Select all sequences, then run Analysis > Build Haplotype Network.
   Recommended algorithm: Modified TCS.

### XTH7 analysis

1. Load `b.chinense.XTH7.fasta` via File > Load FASTA.
   In the standardization dialog, configure the `|` delimiter to parse sample name, group, and height from the header.
2. Optionally load `b.chinense.MOR1.meta.csv` via File > Load Metadata if you prefer to assign traits from the CSV rather than the FASTA headers.
3. Select all sequences, then run Analysis > Build Haplotype Network.
   Recommended algorithm: Modified TCS.

## Notes

- Both loci have uniform sequence lengths within each file, so no multiple sequence alignment step is strictly required. However, NetST will still run MSA if requested.
- The metadata CSV provides both a discrete trait (`group`: A or B) and a continuous trait (`height`). When loaded, the network visualization displays group coloring in pie charts and height as a gradient on the outer ring.
- The XTH7 FASTA embeds group and height in the headers using pipe delimiters. This provides an alternative to loading a separate metadata CSV.

## Reference

Song Y-X, Shi Y, Hou J-Q, Zhang Z, Yu X-Y, Zeng Y-Q, Jiang X-Y, Yu Y. 2026. Pleistocene climate oscillations and topographic barriers jointly shape stepwise phylogeographic divergence and polygenic adaptation to isothermality in *Bupleurum chinense*. Palaeogeography, Palaeoclimatology, Palaeoecology 696:113875.

If you use this dataset, please cite the reference above.
