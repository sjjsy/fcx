"""fcx — File Converter Exchange

Convert files to a different format or apply in-place transforms.
Inputs are merged (pdf, txt) or converted individually (img, same-format).

Usage:
  fcx (-d | --deps)    [EXT ...]
  fcx (-m | --methods) OEXT [OEXT ...]
  fcx (-i | --inputs)  OEXT [OEXT ...]
  fcx (-o | --outputs) IEXT [IEXT ...]
  fcx (-R | --recover) [EXT]
  fcx (-I | --init)    [TOOL]
  fcx [options] [ARGS ...]
  fcx -h | --help
  fcx --version

Options:
  -h --help        Show this screen.
  --version        Show version.
  -I --init        List built-in converter files or copy TOOL to user config dir.
  -d --deps        Check deps for all converters, or filter by EXT(s).
  -m --methods     List converters for each output OEXT.
  -i --inputs      List source formats that produce each output OEXT.
  -o --outputs     List output formats each input IEXT can produce.
  -R --recover     Restore most-recent fcx backup from Trash into CWD.
  -O --overwrite   Skip trash backup for same-format (in-place) transforms.
  -v --verbose     Stream live stdout/stderr from every shell command.
  --dry-run        Print commands without executing.

TARGET syntax:
  The first positional argument is treated as TARGET when it does not name an
  existing file on disk.  It takes the form  SPEC[:METHOD[:PARAMS]]  where:

    SPEC     Output extension (pdf, txt, png, jpg, wav, ...) or explicit output
             file path (report.pdf, out/notes.txt, ...).
             Omit entirely to default to "pdf".
    METHOD   Name or unique prefix of the converter to prefer, e.g.
             pandoc, loffice, wk, l1, crop.  Fuzzy prefix-matched against
             converter names; falls back to the next available converter.
    PARAMS   Parameter string passed verbatim to the converter function.
             Some converters require it (e.g. crop:50x50, annotate:Draft v2).

  Examples:
    pdf                  pdf:pandoc            jpg:l1
    jpg:crop:50x50       jpg:annotate:Draft v2 report.pdf:loffice
    wav:16k

Output file naming:
  SPEC is a path  → that is the output file.
  SPEC is an ext, merge mode (→pdf/txt)  → {first_input_stem}.{ext} in CWD.
  SPEC is an ext, per-file mode          → {each_input_stem}.{ext} in CWD.
  Same-format transform                  → input file path (in-place).

Trash backup (same-format transforms):
  Before in-place transforms, inputs are copied to:
    ~/.local/share/Trash/files/fcx_YYYYMMDD_HHMMSS_EXT/
  with a matching .trashinfo sidecar.  No external tools needed.
  Use -R / --recover to restore the most recent backup into CWD.
  Use -O / --overwrite to skip the backup entirely.

Examples:
  fcx report.pdf intro.pdf chapter.docx diagram.svg   # merge → pdf
  fcx pdf report.pdf intro.pdf chapter.docx           # same, explicit ext
  fcx txt notes.txt paper.pdf slides.pptx             # merge → txt
  fcx png *.svg                                       # batch svg → png
  fcx report.pdf:pandoc chapter.md appendix.md        # force pandoc
  fcx jpg:l1 photos/*.jpg                             # compress to trash
  fcx jpg:l1 -O photos/*.jpg                          # compress, no backup
  fcx jpg:crop:50x50 photos/*.jpg                     # center-crop 50%
  fcx jpg:annotate:Draft v2 *.jpg                     # annotate all
  fcx wav:16k recordings/*.mp3                        # audio → 16 kHz mono
  fcx -R                                              # recover last backup
  fcx -R jpg                                          # recover last jpg backup
  fcx -d                                              # check all deps
  fcx -d pdf                                          # check →pdf converter deps
  fcx -m pdf                                          # list all →pdf converters
  fcx -o docx                                         # what can docx become?
  fcx -i pdf                                          # what converts to pdf?
  fcx -I                                              # list built-in converter files
  fcx -I pandoc                                       # copy pandoc.py to user config dir
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Optional

from docopt import docopt

from . import __version__
from . import color
from . import core


# ── TARGET parsing ────────────────────────────────────────────────────────────

def _parse_target(target: str):
    """Parse 'SPEC[:METHOD[:PARAMS]]' → (spec, method, params)."""
    parts = target.split(":", 2)
    spec = parts[0] if parts else "pdf"
    method = parts[1] if len(parts) > 1 else None
    params = parts[2] if len(parts) > 2 else None
    return spec, method or None, params


def _split_positionals(args: list):
    """Split positionals into (target_str, files).

    The first element is TARGET if it does not name an existing file on disk
    AND it looks like a SPEC (extension or path with extension, optionally
    followed by :METHOD or :METHOD:PARAMS).
    """
    if not args:
        return None, []

    first = args[0]
    # Treat as TARGET if it does not exist as a file on disk
    if not Path(first).exists():
        return first, args[1:]
    return None, args


def _output_ext(spec: str) -> Optional[str]:
    """Extract extension from SPEC (e.g. 'pdf', 'report.pdf' → 'pdf')."""
    p = Path(spec)
    if p.suffix:
        return p.suffix.lstrip(".").lower()
    return spec.lower()


# ── Command implementations ───────────────────────────────────────────────────

def _cmd_convert(positionals: list, overwrite: bool) -> int:
    convs = core.load_converters()

    target_str, files = _split_positionals(positionals)
    if target_str is None:
        target_str = "pdf"

    if not files:
        print(f"{color.red('[ERROR]')} No input files specified.", file=sys.stderr)
        return 1

    spec, method, params = _parse_target(target_str)
    to_ext = _output_ext(spec)
    spec_is_path = bool(Path(spec).suffix)

    file_paths = [Path(f) for f in files]
    for fp in file_paths:
        if not fp.exists():
            print(f"{color.red('[ERROR]')} Input file not found: {fp}", file=sys.stderr)
            return 1

    explicit_output = Path(spec) if spec_is_path else None

    from collections import Counter
    ext_counts = Counter(fp.suffix.lstrip(".").lower() for fp in file_paths)
    input_ext = ext_counts.most_common(1)[0][0] if ext_counts else ""

    conv, layer = core.select_converter(convs, input_ext, to_ext, method)
    if conv is None:
        print(
            f"{color.red('[ERROR]')} No converter available for {input_ext!r} → {to_ext!r}"
            + (f" (method: {method!r})" if method else ""),
            file=sys.stderr,
        )
        print("Tip: run  fcx -d  to check which tools are installed.", file=sys.stderr)
        return 1

    mode = core.resolve_mode(conv, input_ext)

    def _print_convert(inputs, out):
        src = "  ".join(str(f) for f in inputs)
        print(f"{color.cyan('[CONVERT]')} {src} → {out}  {color.dim(f'[{conv.name}]')}")

    if mode == "merge":
        out_path = explicit_output or (Path.cwd() / f"{file_paths[0].stem}.{to_ext}")
        _print_convert(file_paths, out_path)
        try:
            conv.fn(file_paths, out_path, params)
        except RuntimeError as exc:
            print(f"{color.red('[ERROR]')} {exc}", file=sys.stderr)
            return 1

    elif mode == "in-place":
        if not overwrite:
            core.trash_backup(file_paths, to_ext)
        for fp in file_paths:
            if fp.suffix.lstrip(".").lower() != input_ext:
                continue
            out_path = explicit_output or fp
            _print_convert([fp], out_path)
            try:
                conv.fn([fp], out_path, params)
            except RuntimeError as exc:
                print(f"{color.red('[ERROR]')} {fp}: {exc}", file=sys.stderr)
                return 1

    else:  # per-file
        for fp in file_paths:
            out_path = explicit_output or (Path.cwd() / f"{fp.stem}.{to_ext}")
            _print_convert([fp], out_path)
            try:
                conv.fn([fp], out_path, params)
            except RuntimeError as exc:
                print(f"{color.red('[ERROR]')} {fp}: {exc}", file=sys.stderr)
                return 1

    return 0


def _cmd_deps(targets: list) -> int:
    convs = core.load_converters()
    if targets:
        filtered = []
        for t in targets:
            to_ext = _output_ext(t)
            from_ext = t.lower().lstrip(".")
            subset = [
                (c, l) for c, l in convs
                if c.to_format == to_ext or from_ext in c.from_formats
            ]
            filtered.extend(subset)
        convs = filtered or convs

    seen = set()
    for conv, layer in convs:
        if conv.name in seen:
            continue
        seen.add(conv.name)
        from_str = ",".join(conv.from_formats)
        print(f"\n{conv.name}  ({from_str} → {conv.to_format})  {color.dim(f'[{layer}]')}")
        if not conv.deps:
            print(f"  {color.dim('(no external deps)')}")
            continue
        for dep in conv.deps:
            ok, path, ver = core.dep_info(dep)
            mark = color.green("✓") if ok else color.red("✗")
            loc = color.dim(f"  {path}") if ok else ""
            ver_str = color.dim(f"  {ver[:60]}") if ver else ""
            print(f"  {mark}  {dep:<16}{loc}{ver_str}")
    return 0


def _cmd_methods(targets: list) -> int:
    if not targets:
        print(f"{color.red('[ERROR]')} Specify at least one output extension.", file=sys.stderr)
        return 1
    convs = core.load_converters()
    for t in targets:
        to_ext = _output_ext(t)
        print(f"\n→ {to_ext}")
        matched = [(c, l) for c, l in convs if c.to_format == to_ext]
        if not matched:
            print(f"  {color.dim('(no converters registered)')}")
            continue
        all_froms = sorted({f for c, _ in matched for f in c.from_formats})
        first_selected = set()
        for from_ext in all_froms:
            c, _ = core.select_converter(convs, from_ext, to_ext)
            if c:
                first_selected.add(c.name)

        for conv, layer in matched:
            deps_ok = all(shutil.which(d) for d in conv.deps)
            mark = color.green("✓") if deps_ok else color.red("✗")
            dep_str = ", ".join(
                f"{d} {color.green('✓') if shutil.which(d) else color.red('✗')}"
                for d in conv.deps
            ) or color.dim("(none)")
            params_str = conv.params or color.dim("(none)")
            selected_tag = f"  {color.green('← would be selected')}" if conv.name in first_selected else ""
            print(
                f"  {mark}  {conv.name:<30}  deps: {dep_str:<40}"
                f"  params: {params_str[:40]:<42}  {color.dim(f'[{layer}]')}{selected_tag}"
            )
    return 0


def _cmd_inputs(exts: list) -> int:
    if not exts:
        print(f"{color.red('[ERROR]')} Specify at least one output extension.", file=sys.stderr)
        return 1
    convs = core.load_converters()
    for ext in exts:
        to_ext = ext.lower().lstrip(".")
        matched = [(c, l) for c, l in convs if c.to_format == to_ext]
        from_formats = sorted({f for c, _ in matched for f in c.from_formats})
        print(f"→ {to_ext}:  {', '.join(from_formats) or color.dim('(none)')}")
    return 0


def _cmd_outputs(exts: list) -> int:
    if not exts:
        print(f"{color.red('[ERROR]')} Specify at least one input extension.", file=sys.stderr)
        return 1
    convs = core.load_converters()
    for ext in exts:
        from_ext = ext.lower().lstrip(".")
        to_formats = sorted({c.to_format for c, _ in convs if from_ext in c.from_formats})
        print(f"{from_ext} →:  {', '.join(to_formats) or color.dim('(none)')}")
    return 0


def _cmd_recover(ext_list: list) -> int:
    core.recover_from_trash(ext_list[0] if ext_list else None)
    return 0


def _cmd_init(tool: Optional[str]) -> int:
    builtin_dir = Path(__file__).parent / "converters"
    user_dir = Path("~/.config/fcx/converters").expanduser()

    if tool is None:
        print("Built-in converter files (use -I TOOL to copy one to user config):")
        for f in sorted(builtin_dir.glob("*.py")):
            if not f.name.startswith("_"):
                print(f"  {f.stem}")
        print(f"\nUser config dir: {user_dir}")
        return 0

    tool = tool.lower().rstrip(".py")
    src = builtin_dir / f"{tool}.py"
    if not src.exists():
        print(f"{color.red('[ERROR]')} No built-in converter: {tool!r}", file=sys.stderr)
        print("Run  fcx -I  to list available files.", file=sys.stderr)
        return 1

    user_dir.mkdir(parents=True, exist_ok=True)
    dst = user_dir / f"{tool}.py"

    header = (
        f"# fcx user override — {tool}.py\n"
        f"# Copied from built-in by:  fcx -I {tool}\n"
        f"# Edit freely.  Delete this file to revert to the built-in version.\n"
        f"# Built-in source: {src}\n\n"
    )
    dst.write_text(header + src.read_text())
    print(f"{color.cyan('[INIT]')} Written: {dst}")
    return 0


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = docopt(__doc__, version=__version__)

    core.verbose = args["--verbose"]
    core.dry_run = args["--dry-run"]

    if args["--deps"]:
        sys.exit(_cmd_deps(args["EXT"] or []))
    elif args["--methods"]:
        sys.exit(_cmd_methods(args["OEXT"] or []))
    elif args["--inputs"]:
        sys.exit(_cmd_inputs(args["OEXT"] or []))
    elif args["--outputs"]:
        sys.exit(_cmd_outputs(args["IEXT"] or []))
    elif args["--recover"]:
        sys.exit(_cmd_recover(args["EXT"] or []))
    elif args["--init"]:
        sys.exit(_cmd_init(args["TOOL"]))
    else:
        sys.exit(_cmd_convert(args["ARGS"] or [], overwrite=args["--overwrite"]))
