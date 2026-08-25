# SARS-CoV-2 S/L lineage example for NetST

This example contains 130 early SARS-CoV-2 genome sequences classified into S and L lineages by Tang et al. (2021). The dataset demonstrates full-genome haplotype network construction with lineage-level grouping in NetST.

## Files

| File | Description |
|---|---|
| `SL-SARS-CoV-2.fasta` | 130 aligned full-genome sequences (29,903 bp each). FASTA headers use the pipe-delimited format `name|group` (e.g. `S1a|S1`), which NetST parses automatically during import. |
| `SL-SARS-CoV-2.meta.csv` | Metadata with columns `sample` and `group`, assigning each sequence to one of 27 lineage designations. |
| `NC_045512.fasta` | SARS-CoV-2 reference genome (Wuhan-Hu-1, GenBank NC_045512, 29,903 bp). Required as the reference sequence when using the McAN algorithm. |
| `marker_snvs.tsv` | Diagnostic marker SNVs for each of the 130 sequences. Each row lists a sequence name and its marker mutations in the format `position(SNP:ref->alt)`, semicolon-separated. |

## Dataset overview

- Pathogen: SARS-CoV-2
- Number of samples: 130
- Sequence length: 29,903 bp (full genome, pre-aligned)
- Lineage groups: 27 total (10 S-lineage + 17 L-lineage)
- Alignment: pre-aligned (no MSA needed)

### Lineage groups

**S-lineage (10 groups, 38 samples):** S1 (14), S2 (1), S3 (1), S4 (1), S5 (5), S6 (7), S7 (1), S8 (2), S9 (2), S10 (3)

**L-lineage (17 groups, 92 samples):** L1a (1), L1b (2), L1c (1), L1d (1), L1e (1), L1f (2), L1g (5), L1h (5), L1i (3), L1j (14), L2a (1), L2b (16), L2c (3), L2d (18), L2e (1), L2f (5), L2g (13)

### Metadata columns

| Column | Type | Description |
|---|---|---|
| `sample` | ID | Sequence name (e.g. `S1a`), matches FASTA headers (before the `|` delimiter) |
| `group` | Categorical | Lineage designation (e.g. `S1`, `L2d`) |

### Marker SNVs format

`marker_snvs.tsv` is a two-column tab-separated file (no header row). Column 1 is reserved (`-`), column 2 is the sequence name, followed by a semicolon-separated list of diagnostic mutations. Each mutation is written as `position(SNP:ref->alt)`, e.g. `8782(SNP:C->U)`.

## Usage in NetST

### Standard workflow (TCS / MSN / MJN)

1. Load `SL-SARS-CoV-2.fasta` via File > Load FASTA.
   NetST will parse the `name|group` headers automatically; configure the delimiter in the standardization dialog if needed.
2. Optionally load `SL-SARS-CoV-2.meta.csv` via File > Load Metadata to set group labels.
3. Select all sequences, then run Analysis > Build Haplotype Network.
   Recommended algorithms: Modified TCS or MSN.

### McAN workflow

1. Load `SL-SARS-CoV-2.fasta` via File > Load FASTA.
2. Optionally load `SL-SARS-CoV-2.meta.csv` via File > Load Metadata.
3. Select all sequences, then run Analysis > Build Haplotype Network.
4. Choose the McAN algorithm and select `L1a` as the reference sequence.

## Notes

- The sequences are pre-aligned (equal length), so no MSA step is needed.
- FASTA headers embed the group assignment after a `|` delimiter. If the standardization dialog is configured to parse `|`, the group trait is extracted directly from the headers without needing a separate metadata file.
- The `marker_snvs.tsv` file provides per-sequence diagnostic mutations for reference; it is not used as input by NetST.

## Reference

Tang X, Ying R, Yao X, Li G, Wu C, Tang Y, Li Z, Kuang B, Wu F, Chi C. Evolutionary analysis and lineage designation of SARS-CoV-2 genomes. *Science Bulletin* 66(22):2297–2311 (2021). https://doi.org/10.1016/j.scib.2021.06.006

If you use this dataset, please cite the reference above.
