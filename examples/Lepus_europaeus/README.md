# European brown hare example for NetST

This example contains the mitochondrial control-region I (CR-I/D-loop) data used by Stamatis et al. (2009) for *Lepus europaeus*.

## Files

| File | Description |
|---|---|
| `CR-I.fasta` | 69 unaligned mitochondrial CR-I sequences (291–464 bp). FASTA identifiers are haplotype names (e.g. `EUA01`, `SEE05`, `AM30`), not GenBank accessions. |
| `metadata.csv` | One row per haplotype (69 rows) with GenBank accession, haplotype name, sampling locality, and haplogroup. |

## Dataset overview

- Species: *Lepus europaeus* (European brown hare)
- Marker type: mitochondrial control-region I (D-loop)
- Number of haplotypes: 69
- Number of unique sampling localities: 21
- Sequence length range: 291–464 bp (variable, requires alignment)

### Metadata columns

| Column | Type | Description |
|---|---|---|
| `accession` | ID | GenBank accession number (e.g. `DQ469656`) |
| `haplotype` | ID | Haplotype name from Appendix S1 (e.g. `EUA01`); matches FASTA headers |
| `sampling_locality` | Categorical | Sampling locality as reported in Appendix S1 |
| `haplogroup` | Categorical | Haplogroup assignment from Appendix S1 |

### Haplogroup distribution

| Haplogroup | Haplotypes |
|---|---:|
| AMh | 29 |
| EUh-A | 16 |
| SEEh | 16 |
| EUh-B | 7 |
| INTERh | 1 |

## Suggested NetST workflow

1. Load `CR-I.fasta` via File > Load FASTA.
2. Load `metadata.csv` via File > Load Metadata.
   - Map `haplotype` as the sample ID column (matches FASTA headers).
   - Map `sampling_locality` or `haplogroup` as the categorical trait (Group).
3. Select all sequences, then run Analysis > Build Haplotype Network.

## Notes

- Each record is a haplotype representative, not an individual-level sequence. Sample sizes per haplotype are not included.
- Sequence lengths vary (291–464 bp) because the contributing GenBank submissions cover slightly different portions of the control region. NetST will align these sequences automatically before haplotype identification.
- Some sampling localities contain multiple places separated by semicolons because the same haplotype occurred in more than one location; these strings are preserved verbatim from Appendix S1.
- `AM30` is recorded as haplogroup `INTERh` following the original article text.

## Provenance

Sequences were downloaded from NCBI. Metadata were transcribed programmatically from Appendix S1 and checked against all five rendered appendix pages.

## Reference

Stamatis, C. et al. (2009). Phylogeography of the brown hare (*Lepus europaeus*) in Europe: a legacy of south-eastern Mediterranean refugia? *Journal of Biogeography*, 36, 515–528. https://doi.org/10.1111/j.1365-2699.2008.02013.x

If you use this dataset, please cite the reference above.
