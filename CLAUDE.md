# fcx — File Conversion Exchange

File conversion exchange for Linux. Converts documents, images, and audio
to PDF, text, markup, or other image formats by dispatching to system tools
(pandoc, ImageMagick, LibreOffice, etc.) through an extensible converter registry.

## Name and PyPI

- Package name: `fcx` (confirmed available on PyPI as of 2026-05-19)
- CLI command: `fcx`
- Publish to PyPI: yes

## Argument parsing

Use `docopt` (the one external Python dep allowed) — CLI spec lives in the
module docstring of `fcx/cli.py`.

## TARGET syntax (first positional arg)

```
SPEC[:METHOD[:PARAMS]]
```

- `SPEC` — output extension (`pdf`, `jpg`, …) or explicit output filepath
- `METHOD` — converter name or unique prefix, fuzzy-matched
- `PARAMS` — verbatim string passed to converter fn; converter owns parsing

Examples: `pdf`, `pdf:pandoc`, `jpg:crop:50x50`, `jpg:annotate:Draft v2`,
`report.pdf`, `report.pdf:pandoc`, `wav:16k`

Default SPEC when omitted: `pdf`

Output file when SPEC is an extension and no explicit OFILE:
- Merging ops (pdf, txt): `{first_input_basename}.{ext}` in CWD
- Per-file ops (img, same-format): `{each_input_basename}.{ext}` in CWD

## Same-format transforms (in-place)

When OEXT == input extension, input files are copied to a trash backup dir
before modification:

```
~/.local/share/Trash/files/fcx_YYYYMMDD_HHMMSS_OEXT/
~/.local/share/Trash/info/fcx_YYYYMMDD_HHMMSS_OEXT.trashinfo
```

Pure Python FreeDesktop trash implementation — no external tools needed.
`-O/--overwrite` skips the backup. `-R/--recover [EXT]` restores the most
recent matching backup into CWD.

## Converter registry and layering

Converters are `Converter` dataclass instances collected in `CONVERTERS` lists.
Three layers, merged at startup by `(Converter.name, Converter.to_format)` (later wins):

```
1. built-in   fcx/converters/*.py
2. system     /etc/xdg/fcx/converters/*.py
3. user       ~/.config/fcx/converters/*.py   ← highest priority
```

Same (name, to_format) → user version supersedes built-in. Unique key → both
available, user's listed first. `--methods TARGET` shows source layer for each entry.

## Converter files named by backend tool, not by format

```
fcx/converters/
  imagemagick.py   # convert, identify, mogrify (img↔img, in-place transforms)
  pandoc.py        # pandoc (→pdf/txt/md/rst/html from many formats)
  libreoffice.py   # loffice (office formats →pdf/txt)
  pdflatex.py      # pdflatex, makeglossaries, biber (tex→pdf)
  pdftools.py      # pdftotext, pdfjam (pdf→txt, merge)
  inkscape.py      # inkscape (svg→pdf/png)
  ffmpeg.py        # ffmpeg (audio→wav etc.)
  wkhtmltopdf.py   # wkhtmltopdf (html→pdf)
  builtin.py       # copy, via-pdf chain (no external deps)
```

## Converter language

Python-only. The `run()` helper makes shell commands as concise as bash.
Supporting shell converter files adds a second metadata format without
meaningful benefit.

## Converter dataclass

```python
@dataclass
class Converter:
    name: str                    # e.g. "imagemagick-crop"
    from_formats: tuple[str, ...]
    to_format: str               # == from_format → in-place transform
    deps: list[str]              # binary names checked on PATH
    params: str | None           # human-readable params description, or None
    fn: Callable[[Path, Path, str | None], None]
```

Merge key: `(Converter.name, Converter.to_format)`. Selection: first in merged
list whose deps are all on PATH. METHOD prefix in TARGET promotes matching
converter to front.

## Core helpers (fcx/core.py)

- `run(cmd, *, verbose, dry_run)` — logs `[CMD]`, streams/captures, raises on failure
- `parse_wxh(params)` → `(w, h)` — optional, for converters that need it
- `parse_kv(params)` → `dict` — optional, for key=val,key=val params

## CLI flags

```
-O --overwrite   skip trash backup for in-place transforms
-R --recover     restore most recent fcx_* dir from trash into CWD
-v --verbose     stream live stdout/stderr from shell commands
--dry-run        print commands without executing
-d --deps        check deps for all or named converters
-m --methods     list converters for a target ext
--inputs EXT     what input formats can produce this output?
--outputs EXT    what output formats can this input produce?
--init [TOOL]    copy built-in converter file(s) to ~/.config/fcx/converters/
                 with attribution header; user can then customise freely
```

## Merging vs per-file mode

| to_format        | mode          | notes                          |
|------------------|---------------|--------------------------------|
| pdf, txt         | merge         | all inputs → one output file   |
| == from_format   | per-file      | in-place, trash backup first   |
| anything else    | per-file      | each input → own output file   |

## Target formats supported (initial)

→ PDF, → TXT, → MD, → RST, → HTML, → PNG/JPG/any img, → WAV
In-place: jpg compression levels (l0–lb1), png compression, crop, cropabs,
annotate, version comparison set, montage.
