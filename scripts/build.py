#!/usr/bin/env python3
"""Build and validate a native NetST release on macOS or Windows."""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
import re
import shutil
import stat
import struct
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
BUILD = ROOT / "build" / "pyinstaller"
APP_VERSION = "2.0.0"

REQUIRED_DISTRIBUTIONS = (
    ("PyQt6", "PyQt6"),
    ("PyQt6-Qt6", None),
    ("PyQt6-sip", None),
    ("PyQt6-WebEngine", "PyQt6.QtWebEngineWidgets"),
    ("PyQt6-WebEngine-Qt6", None),
    ("chardet", "chardet"),
    ("PyInstaller", "PyInstaller"),
    ("pyinstaller-hooks-contrib", None),
)


class BuildError(RuntimeError):
    """A release preflight, build, or validation step failed."""


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", subprocess.list2cmdline(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env)
    if result.returncode:
        raise BuildError(
            f"Command failed with exit code {result.returncode}: "
            f"{subprocess.list2cmdline(command)}"
        )


def _target() -> str:
    if not ((3, 10) <= sys.version_info[:2] <= (3, 12)):
        raise BuildError("Release builds require Python 3.10, 3.11, or 3.12")
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        if machine not in {"arm64", "aarch64"}:
            raise BuildError("macOS releases require native Apple Silicon Python")
        return "macos-arm64"
    if sys.platform.startswith("win"):
        if struct.calcsize("P") != 8 or machine not in {"amd64", "x86_64"}:
            raise BuildError("Windows releases require x86-64 Python")
        return "windows-x86_64"
    raise BuildError("Release builds are supported only on macOS and Windows")


def _check_dependencies() -> None:
    problems: list[str] = []
    installed: dict[str, str] = {}
    for distribution, module in REQUIRED_DISTRIBUTIONS:
        try:
            installed[distribution] = version(distribution)
        except PackageNotFoundError:
            problems.append(f"missing distribution: {distribution}")
            continue
        if module and importlib.util.find_spec(module) is None:
            problems.append(f"cannot import module: {module}")

    if problems:
        detail = "\n  - ".join(problems)
        raise BuildError(
            "Packaging environment is incomplete:\n  - " + detail
            + f"\nInstall it with:\n  {sys.executable} -m pip install -r "
              "requirements-build.txt"
        )
    print("Dependencies:", ", ".join(f"{k}={v}" for k, v in installed.items()))


def _check_bundle_inputs(target: str) -> None:
    common = [
        ROOT / "main_form.py",
        ROOT / "static" / "icon" / "netst.icns",
        ROOT / "static" / "icon" / "netst.ico",
        ROOT / "static" / "tcsbu" / "index.html",
    ]
    if target == "macos-arm64":
        platform_files = [
            ROOT / "lib" / "mac_arm64" / "McAN",
            ROOT / "lib" / "mac_arm64" / "fastHaN",
            ROOT / "lib" / "mac_arm64" / "muscle3",
            ROOT / "lib" / "mac_arm64" / "netst-rmst",
            ROOT / "lib" / "mac_arm64" / "mafft-mac" / "mafft.bat",
        ]
        spec = ROOT / "netst-mac-arm64.spec"
    else:
        platform_files = [
            ROOT / "lib" / "win" / "McAN.exe",
            ROOT / "lib" / "win" / "fastHaN_win_intel.exe",
            ROOT / "lib" / "win" / "muscle3.exe",
            ROOT / "lib" / "win" / "netst-rmst.exe",
            ROOT / "lib" / "win" / "mafft-win" / "mafft.bat",
        ]
        spec = ROOT / "netst-win.spec"

    missing = [str(path.relative_to(ROOT)) for path in common + platform_files + [spec]
               if not path.is_file()]
    if missing:
        raise BuildError(
            "Required packaging inputs are missing:\n  - " + "\n  - ".join(missing)
        )

    if target == "macos-arm64":
        not_executable = [str(path.relative_to(ROOT)) for path in platform_files
                          if not (path.stat().st_mode & stat.S_IXUSR)]
        if not_executable:
            raise BuildError(
                "Bundled macOS tools are not executable:\n  - "
                + "\n  - ".join(not_executable)
                + "\nRestore their executable git file mode before building."
            )


def _find_one(root: Path, name: str) -> bool:
    return any(path.name == name for path in root.rglob(name))


def _validate_output(target: str, onefile: bool) -> Path:
    if target == "macos-arm64":
        output = DIST / "NetST.app"
        executable = output / "Contents" / "MacOS" / "NetST"
        resource_root = output / "Contents" / "Resources"
    elif onefile:
        output = DIST / "NetST.exe"
        executable = output
        resource_root = output
    else:
        output = DIST / "NetST"
        executable = output / "NetST.exe"
        resource_root = output / "_internal"

    if not executable.is_file():
        raise BuildError(f"Expected executable was not created: {executable}")

    structural_checks: list[tuple[str, bool]] = []
    if not onefile:
        structural_checks.extend([
            ("QtWebEngine process", _find_one(output, "QtWebEngineProcess.exe")
             or _find_one(output, "QtWebEngineProcess")),
            ("QtWebEngine resources", _find_one(output, "qtwebengine_resources.pak")),
            ("tcsBU resources", (resource_root / "static" / "tcsbu" / "tcsBU.js").exists()),
            ("platform libraries", (resource_root / "lib").is_dir()),
            ("native RMST engine", _find_one(output, "netst-rmst.exe")
             or _find_one(output, "netst-rmst")),
        ])
    failed = [label for label, passed in structural_checks if not passed]
    if failed:
        raise BuildError("Package validation failed: " + ", ".join(failed))

    if not onefile:
        forbidden = {
            "qtwebengine_devtools_resources.pak",
            "libqpdf.dylib", "qpdf.dll",
            "libqtposition_nmea.dylib", "qtposition_nmea.dll",
            "Qt6Pdf.dll", "Qt6SerialPort.dll",
            "libcrypto.3.dylib", "libssl.3.dylib",
        }
        unexpected = sorted({path.name for path in output.rglob("*")
                             if path.name in forbidden})
        if unexpected:
            raise BuildError(
                "Package contains excluded optional Qt files: " + ", ".join(unexpected)
            )
        locale_packs = sorted(path.name for path in output.rglob("*.pak")
                              if "qtwebengine_locales" in path.parts)
        if locale_packs:
            raise BuildError(
                "Package contains excluded WebEngine locales: "
                + ", ".join(locale_packs)
            )
        qt_bindings = {
            path.name.split(".", 1)[0]
            for path in output.rglob("*")
            if path.is_file() and path.name.startswith("Qt")
               and (path.suffix in {".so", ".pyd"} or ".abi3.so" in path.name)
        }
        forbidden_bindings = {
            "Qt3DCore", "Qt3DRender", "QtBluetooth", "QtDBus",
            "QtDesigner", "QtHelp", "QtMultimedia", "QtMultimediaWidgets",
            "QtNfc", "QtOpenGL", "QtPositioning", "QtQml", "QtQuick",
            "QtQuick3D", "QtQuickWidgets", "QtRemoteObjects", "QtSensors",
            "QtSerialPort", "QtSql", "QtSvgWidgets", "QtTest",
            "QtTextToSpeech", "QtXml",
        }
        unexpected_bindings = sorted(qt_bindings & forbidden_bindings)
        if unexpected_bindings:
            raise BuildError(
                "Package contains excluded PyQt bindings: "
                + ", ".join(unexpected_bindings)
            )

    if target == "macos-arm64" and shutil.which("codesign"):
        _run(["codesign", "--verify", "--deep", "--strict", str(output)])
    return output


def build(args: argparse.Namespace) -> Path:
    target = _target()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", args.version):
        raise BuildError("--version must use numeric MAJOR.MINOR.PATCH form")
    if args.onefile and target != "windows-x86_64":
        raise BuildError("--onefile is available only for Windows")

    _check_dependencies()
    _check_bundle_inputs(target)

    env = os.environ.copy()
    env["NETST_VERSION"] = args.version
    env["NETST_ONEFILE"] = "1" if args.onefile else "0"
    # Keep PyInstaller's cache local to this checkout. This makes --clean
    # deterministic in CI/sandboxed environments and avoids modifying a user's
    # global Application Support/AppData cache.
    env["PYINSTALLER_CONFIG_DIR"] = str(BUILD / "cache")
    if args.codesign_identity:
        if target != "macos-arm64":
            raise BuildError("--codesign-identity applies only to macOS")
        entitlements = Path(args.entitlements).resolve()
        if not entitlements.is_file():
            raise BuildError(f"Entitlements file not found: {entitlements}")
        env["NETST_CODESIGN_IDENTITY"] = args.codesign_identity
        env["NETST_ENTITLEMENTS_FILE"] = str(entitlements)

    spec = "netst-mac-arm64.spec" if target == "macos-arm64" else "netst-win.spec"
    _run([
        sys.executable, "-m", "PyInstaller",
        "--clean", "--noconfirm",
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        spec,
    ], env=env)
    output = _validate_output(target, args.onefile)
    print(f"Release build passed all checks: {output}")
    return output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build NetST natively and validate the release package."
    )
    parser.add_argument("--version", default=APP_VERSION,
                        help=f"application version (default: {APP_VERSION})")
    parser.add_argument("--onefile", action="store_true",
                        help="build a Windows one-file executable (directory mode is recommended)")
    parser.add_argument("--codesign-identity",
                        help="macOS Developer ID Application identity")
    parser.add_argument(
        "--entitlements",
        default=str(ROOT / "scripts" / "macos-entitlements.plist"),
        help="macOS entitlements plist used with --codesign-identity",
    )
    return parser


def main() -> int:
    try:
        build(_parser().parse_args())
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
