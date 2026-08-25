# Diamond Princess SARS-CoV-2 example for NetST

This example contains 482 SARS-CoV-2 sequences from the Diamond Princess cruise ship outbreak and contemporaneous global samples, as analyzed by Sekizuka et al. (2020). The dataset demonstrates multiple input formats supported by NetST, including FASTA, PHYLIP, and VCF.

## Files

| File | Format | Description |
|---|---|---|
| `DP-SARS-CoV-2.fasta` | FASTA | 482 aligned sequences (444 variable sites) |
| `DP-SARS-CoV-2.phy` | PHYLIP | Same 482 sequences in PHYLIP format |
| `DP-SARS-CoV-2.vcf` | VCF 4.1 | Variant calls for all 482 samples (444 variant records). Recommended input format for the McAN algorithm. |
| `DP-SARS-CoV-2.meta.csv` | CSV | Metadata with columns `ID`, `Location`, and `Time` |
| `DP-SARS-CoV-2.tsv` | TSV | McAN six-column metadata for VCF import (no header row) |

## Dataset overview

- Pathogen: SARS-CoV-2
- Number of samples: 482
- Variable sites: 444
- Collection date range: 2019/12/24 – 2020/03/03
- Alignment: pre-aligned (no MSA needed)

### Metadata columns (CSV)

| Column | Type | Description |
|---|---|---|
| `ID` | ID | Sample identifier, matches FASTA/PHYLIP/VCF sample names |
| `Location` | Categorical | Sampling region |
| `Time` | Continuous | Collection date (YYYY/M/D format) |

### Location distribution

| Location | Samples |
|---|---:|
| China | 244 |
| other Asia | 100 |
| DP (Diamond Princess) | 72 |
| North America | 18 |
| Europe | 16 |
| CruiseA | 12 |
| Oceania | 11 |
| Japan | 9 |

### TSV metadata format (for McAN VCF import)

The `DP-SARS-CoV-2.tsv` file uses the McAN six-column format with no header row. Each row contains tab-separated fields:

1. Reserved (`*`)
2. Sample ID
3. Collection date
4. Location
5. Reserved (`*`)
6. Reserved (`*`)

## Usage in NetST

### Standard workflow (TCS / MSN / MJN / RMST)

1. Load `DP-SARS-CoV-2.fasta` via File > Load FASTA (or `DP-SARS-CoV-2.phy` via File > Load PHYLIP).
2. Load `DP-SARS-CoV-2.meta.csv` via File > Load Metadata to assign location groups.
3. Select all sequences, then run Analysis > Build Haplotype Network.

### McAN workflow (via VCF)

1. Load `DP-SARS-CoV-2.vcf` via File > Load VCF.
2. In the VCF import dialog, select `DP-SARS-CoV-2.tsv` as the metadata file. This enables native McAN VCF mode.
3. Select all sequences, then run Analysis > Build Haplotype Network and choose the McAN algorithm.

## Notes

- The sequences are pre-aligned and contain only variable sites (444 bp). No MSA step is required.
- The VCF + TSV combination is the recommended input for McAN, as it preserves the original variant representation without conversion.
- The `Time` column in the metadata can be used as a continuous trait for temporal visualization.

## Reference

Sekizuka T, Itokawa K, Kageyama T, Saito S, Takayama I, Asanuma H, Nao N, Tanaka R, Hashino M, Takahashi T, Kamiya H, Yamagishi T, Kakimoto K, Suzuki M, Hasegawa H, Wakita T, Kuroda M. Haplotype networks of SARS-CoV-2 infections in the Diamond Princess cruise ship outbreak. *Proc. Natl. Acad. Sci. U.S.A.* 117(33):20198–20201 (2020). https://doi.org/10.1073/pnas.2006824117

If you use this dataset, please cite the reference above.
