"""Core helpers: Converter dataclass, run(), trash backup, registry loading."""
from __future__ import annotations

import importlib.util
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from . import color

# ── Global runtime flags (set by cli.py before any conversion) ──
verbose: bool = False
dry_run: bool = False


@dataclass
class Converter:
    name: str
    from_formats: tuple
    to_format: str
    deps: list
    params: Optional[str]
    fn: Callable[[List[Path], Path, Optional[str]], None]
    mode: str = "auto"
    # mode values:
    #   "auto"     – merge when to_format in (pdf,txt); in-place when to==from; else per-file
    #   "merge"    – all inputs → one output (no in-place backup)
    #   "per-file" – one input → one output, no trash backup
    #   "in-place" – per-file with trash backup


# ── Shell command runner ──────────────────────────────────────────────────────

def run(cmd: list, *, capture: bool = False) -> str:
    print(f"{color.yellow('[CMD]')} {shlex.join(str(c) for c in cmd)}")
    if dry_run:
        return ""
    if verbose:
        proc = subprocess.run(cmd)
    else:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        if not verbose:
            err = (proc.stderr or b"").decode(errors="replace").strip()
            if err:
                print(err, file=sys.stderr)
        raise RuntimeError(
            f"Command failed (exit {proc.returncode}): {shlex.join(str(c) for c in cmd)}"
        )
    return proc.stdout.decode(errors="replace") if capture and not verbose else ""


# ── Parameter parsers ─────────────────────────────────────────────────────────

def parse_wxh(params: str) -> Tuple[int, int]:
    """Parse 'WxH' string → (w, h) integers. Raises ValueError on bad input."""
    if not params:
        raise ValueError("Expected WxH parameter (e.g. 50x50)")
    parts = params.strip().lower().split("x", 1)
    if len(parts) != 2:
        raise ValueError(f"Expected WxH, got: {params!r}")
    return int(parts[0]), int(parts[1])


def parse_kv(params: str) -> dict:
    """Parse 'key=val,key2=val2' → dict. Values may contain '='."""
    if not params:
        return {}
    result = {}
    for item in params.split(","):
        if "=" in item:
            k, _, v = item.partition("=")
            result[k.strip()] = v.strip()
        else:
            result[item.strip()] = ""
    return result


# ── FreeDesktop Trash implementation ─────────────────────────────────────────

_TRASH_FILES = Path("~/.local/share/Trash/files").expanduser()
_TRASH_INFO = Path("~/.local/share/Trash/info").expanduser()


def trash_backup(files: list, oext: str) -> Path:
    """Copy files to a timestamped FreeDesktop Trash directory. Returns backup dir path."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if dry_run:
        backup_dir = _TRASH_FILES / f"fcx_{stamp}_{oext}"
        print(f"{color.cyan('[TRASH]')} (dry-run) would back up {len(files)} file(s) to {backup_dir}")
        return backup_dir
    backup_name = f"fcx_{stamp}_{oext}"
    backup_dir = _TRASH_FILES / backup_name

    _TRASH_FILES.mkdir(parents=True, exist_ok=True)
    _TRASH_INFO.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        shutil.copy2(f, backup_dir / Path(f).name)

    # Write .trashinfo sidecar
    info_path = _TRASH_INFO / f"{backup_name}.trashinfo"
    info_path.write_text(
        "[Trash Info]\n"
        f"Path={backup_dir}\n"
        f"DeletionDate={datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n"
    )
    print(f"{color.cyan('[TRASH]')} {backup_dir}  ({len(files)} file(s) backed up)")
    return backup_dir


def recover_from_trash(ext: Optional[str] = None) -> None:
    """Move the most recent fcx_* backup from Trash into CWD."""
    if not _TRASH_FILES.exists():
        print("No fcx backups found in Trash.")
        return

    candidates = sorted(
        [d for d in _TRASH_FILES.iterdir()
         if d.is_dir() and d.name.startswith("fcx_")
         and (ext is None or ext.lower() in d.name.lower())],
        key=lambda d: d.name,
        reverse=True,
    )
    if not candidates:
        what = f"fcx_*_{ext}*" if ext else "fcx_*"
        print(f"No matching Trash directories ({what}).")
        return

    src = candidates[0]
    dst = Path.cwd() / src.name
    shutil.move(str(src), str(dst))
    print(f"{color.cyan('[RECOVER]')} {src.name} → {dst}")

    info_file = _TRASH_INFO / f"{src.name}.trashinfo"
    if info_file.exists():
        info_file.unlink()


# ── Converter registry ────────────────────────────────────────────────────────

def _load_layer(directory: Path) -> list:
    """Load CONVERTERS lists from all .py files in directory."""
    converters = []
    if not directory.is_dir():
        return converters
    for py_file in sorted(directory.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(
            f"fcx_ext_{py_file.stem}", py_file
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as exc:
            print(f"{color.yellow('[WARN]')} Failed to load {py_file}: {exc}", file=sys.stderr)
            continue
        if hasattr(mod, "CONVERTERS"):
            converters.extend(mod.CONVERTERS)
    return converters


def load_converters() -> list:
    """Return merged converter list as [(Converter, layer_str), ...].

    Three layers merged by (Converter.name, Converter.to_format) — same name
    for different output formats are distinct entries. Later layers win for the
    same key. Unique keys from system/user layers are prepended (highest priority).
    """
    builtin_dir = Path(__file__).parent / "converters"
    system_dir = Path("/etc/xdg/fcx/converters")
    user_dir = Path("~/.config/fcx/converters").expanduser()

    builtin_convs = [(c, "built-in") for c in _load_layer(builtin_dir)]
    system_convs = [(c, "system") for c in _load_layer(system_dir)]
    user_convs = [(c, "user") for c in _load_layer(user_dir)]

    # Build ordered map: (name, to_format) → (Converter, layer)
    order: list = []
    registry: dict = {}

    for conv, layer in builtin_convs:
        key = (conv.name, conv.to_format)
        registry[key] = (conv, layer)
        order.append(key)

    for conv, layer in system_convs:
        key = (conv.name, conv.to_format)
        if key in registry:
            registry[key] = (conv, layer)  # replace, keep position
        else:
            registry[key] = (conv, layer)
            order.insert(0, key)            # unique → prepend

    for conv, layer in user_convs:
        key = (conv.name, conv.to_format)
        if key in registry:
            registry[key] = (conv, layer)  # replace, keep position
        else:
            registry[key] = (conv, layer)
            order.insert(0, key)            # unique → prepend

    return [(registry[k][0], registry[k][1]) for k in order]


def select_converter(convs: list, from_ext: str, to_ext: str, method: Optional[str] = None):
    """Return (Converter, layer) for best available match, or (None, None)."""
    from_ext = from_ext.lower().lstrip(".")
    to_ext = to_ext.lower().lstrip(".")

    candidates = [
        (c, layer) for c, layer in convs
        if from_ext in c.from_formats and c.to_format == to_ext
    ]

    if method:
        m = method.lower()
        preferred = [(c, l) for c, l in candidates
                     if c.name.lower().startswith(m) or m in c.name.lower()]
        rest = [(c, l) for c, l in candidates if (c, l) not in preferred]
        candidates = preferred + rest

    for conv, layer in candidates:
        if all(shutil.which(dep) for dep in conv.deps):
            return conv, layer

    return None, None


def resolve_mode(converter: "Converter", input_ext: str) -> str:
    """Resolve effective dispatch mode for a converter + input extension."""
    if converter.mode != "auto":
        return converter.mode
    if converter.to_format in ("pdf", "txt"):
        return "merge"
    if converter.to_format == input_ext.lower().lstrip("."):
        return "in-place"
    return "per-file"


def dep_info(dep: str) -> tuple:
    """Return (available: bool, path: str, version: str)."""
    path = shutil.which(dep)
    if not path:
        return False, "", ""
    try:
        result = subprocess.run(
            [dep, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        ver_line = (result.stdout or result.stderr or "").split("\n")[0].strip()
    except Exception:
        ver_line = ""
    return True, path, ver_line
