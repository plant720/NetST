"""Pure configuration model for MAFFT and MUSCLE command arguments."""

from dataclasses import dataclass
from typing import List


@dataclass
class SequenceAlignmentConfig:
    tool: str = "mafft"
    mafft_algorithm: str = "auto"
    mafft_op: float = 1.53
    mafft_ep: float = 0.0
    mafft_maxiterate: int = 0
    mafft_thread: int = -1
    mafft_clustalout: bool = False
    mafft_reorder: bool = False
    mafft_quiet: bool = False
    mafft_dash: bool = False
    muscle_maxiters: int = 16
    muscle_maxhours: float = 0.0
    muscle_diags: bool = False
    muscle_output_format: str = "fasta"
    muscle_quiet: bool = False

    def to_mafft_method_args(self, force_fasta: bool = False) -> List[str]:
        algorithm_map = {
            "auto": ["--auto"],
            "retree1": ["--retree", "1"],
            "retree2": ["--retree", "2"],
            "linsi": ["--localpair", "--maxiterate", "1000"],
            "ginsi": ["--globalpair", "--maxiterate", "1000"],
            "einsi": ["--genafpair", "--maxiterate", "1000"],
        }
        args = list(algorithm_map.get(self.mafft_algorithm, ["--auto"]))
        if self.mafft_op != 1.53:
            args += ["--op", str(round(self.mafft_op, 6))]
        if self.mafft_ep != 0.0:
            args += ["--ep", str(round(self.mafft_ep, 6))]
        if self.mafft_algorithm not in {"linsi", "ginsi", "einsi"} and self.mafft_maxiterate > 0:
            args += ["--maxiterate", str(self.mafft_maxiterate)]
        args += ["--thread", str(self.mafft_thread)]
        if self.mafft_clustalout and not force_fasta:
            args.append("--clustalout")
        if self.mafft_reorder:
            args.append("--reorder")
        if self.mafft_quiet:
            args.append("--quiet")
        if self.mafft_dash:
            args.append("--dash")
        return args

    def to_muscle_extra_args(self, force_fasta: bool = False) -> List[str]:
        args: List[str] = []
        if self.muscle_diags:
            args.append("-diags")
        if self.muscle_maxiters != 16:
            args += ["-maxiters", str(self.muscle_maxiters)]
        if self.muscle_maxhours > 0.0:
            args += ["-maxhours", str(round(self.muscle_maxhours, 4))]
        format_map = {
            "html": "-html",
            "msf": "-msf",
            "clw": "-clw",
            "clwstrict": "-clwstrict",
        }
        if not force_fasta and self.muscle_output_format in format_map:
            args.append(format_map[self.muscle_output_format])
        if self.muscle_quiet:
            args.append("-quiet")
        return args
