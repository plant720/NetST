"""Pure configuration model for MAFFT and MUSCLE command arguments."""

from dataclasses import dataclass
from typing import Any, Dict, List


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

    def to_dict(self) -> Dict[str, Any]:
        """Return the stable project-file representation."""
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SequenceAlignmentConfig":
        if not isinstance(payload, dict):
            raise ValueError("Alignment configuration must be an object")
        unknown = set(payload) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(
                "Unknown alignment configuration field(s): "
                + ", ".join(sorted(unknown)))
        config = cls(**payload)
        if config.tool not in {"mafft", "muscle"}:
            raise ValueError(f"Unsupported alignment tool: {config.tool!r}")
        if config.mafft_algorithm not in {
            "auto", "retree1", "retree2", "linsi", "ginsi", "einsi"
        }:
            raise ValueError(
                f"Unsupported MAFFT algorithm: {config.mafft_algorithm!r}")
        if config.muscle_output_format not in {
            "fasta", "html", "msf", "clw", "clwstrict"
        }:
            raise ValueError(
                f"Unsupported MUSCLE output format: {config.muscle_output_format!r}")
        if not 0 <= config.mafft_op <= 100 or not 0 <= config.mafft_ep <= 100:
            raise ValueError("MAFFT gap parameters are out of range")
        if not -1 <= config.mafft_thread <= 256:
            raise ValueError("MAFFT thread count is out of range")
        if not 0 <= config.mafft_maxiterate <= 9999:
            raise ValueError("MAFFT iteration count is out of range")
        if not 1 <= config.muscle_maxiters <= 9999:
            raise ValueError("MUSCLE iteration count is out of range")
        if not 0 <= config.muscle_maxhours <= 9999:
            raise ValueError("MUSCLE time limit is out of range")
        return config

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
