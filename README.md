# fcx — File Conversion Exchange

fcx is a file conversion exchange for Linux — one command routes your files to the right backend (pandoc, ImageMagick, LibreOffice, Inkscape…) through an extensible converter registry.

[![PyPI](https://img.shields.io/pypi/v/fcx?color=green)](https://pypi.org/project/fcx/)

## Motivation

Linux power users who regularly convert files face a fragmented landscape: `pandoc` for documents, `convert` for images, `loffice --headless` for Office files, `pdftotext` for PDF extraction, `ffmpeg` for audio. Each tool has a different interface, different flag conventions, and different merging semantics. Scripting across them requires memorising or looking up the invocation for every combination.

`fcx` provides a single, consistent command for all of these:

```bash
fcx report.pdf intro.pdf chapter.docx diagram.svg   # merge to pdf
fcx jpg:l2 photos/*.jpg                             # batch compress
fcx wav:16k recordings/*.mp3                        # audio normalisation
```

The tool is especially useful in Makefiles, shell scripts, and AI coding agent pipelines where you want one deterministic command to handle whatever input format you have.

## Installation

```bash
pip3 install fcx

# or in an isolated environment
pipx install fcx

# upgrade
pip3 install --upgrade fcx
```

### From source

```bash
git clone https://github.com/sjjsy/fcx.git
cd fcx
pip3 install -e .
```

## Quick start

```bash
fcx chapter.md appendix.md          # → chapter.pdf (merge via pandoc)
fcx txt notes.md paper.pdf          # → notes.txt  (merge, pandoc + pdftotext)
fcx png *.svg                       # → per-file PNG (inkscape or ImageMagick)
fcx jpg:l1 photos/*.jpg             # compress in-place, backup to Trash
fcx jpg:crop:50x50 *.jpg            # center-crop 50% each axis, backup to Trash
fcx wav:16k recordings/*.mp3        # → per-file 16 kHz mono WAV
fcx -R                              # recover last in-place backup from Trash
```

## System requirements

`fcx` itself requires only Python 3.8+ and `docopt`. Converters require their respective backend tools:

| Tool | Purpose | Install |
|------|---------|---------|
| [pandoc](https://pandoc.org/) | md/rst/html/docx → pdf/txt/md/rst/html | `apt install pandoc` |
| [ImageMagick](https://imagemagick.org/) | image ↔ image, →pdf, in-place transforms | `apt install imagemagick` |
| [LibreOffice](https://www.libreoffice.org/) | docx/pptx/xlsx/odt → pdf/txt | `apt install libreoffice` |
| [wkhtmltopdf](https://wkhtmltopdf.org/) | html → pdf (also used by pandoc) | `apt install wkhtmltopdf` |
| [Inkscape](https://inkscape.org/) | svg → pdf/png | `apt install inkscape` |
| [pdflatex](https://tug.org/texlive/) | tex/tikz → pdf | `apt install texlive-latex-base` |
| [poppler-utils](https://poppler.freedesktop.org/) | pdf → txt (`pdftotext`), pdf merge (`pdfjam`) | `apt install poppler-utils` |
| [ffmpeg](https://ffmpeg.org/) | audio/video → wav | `apt install ffmpeg` |
| [jpegoptim](https://github.com/tjko/jpegoptim) | JPG lossy compression | `apt install jpegoptim` |
| [jpegtran](http://jpegclub.org/jpegtran/) | JPG lossless optimisation | `apt install libjpeg-turbo-progs` |
| [optipng](https://optipng.sourceforge.net/) | PNG optimisation | `apt install optipng` |

Only the tools needed for your conversions need to be installed. Use `fcx -d` to check what is available.

## CLI reference

```
Usage:
  fcx [options] [ARGS ...]
  fcx -h | --help
  fcx --version

Options:
  -O --overwrite   Skip trash backup for same-format (in-place) transforms.
  -h --help        Show this screen.
  --version        Show version.
  -I --init        Copy built-in converter file(s) to ~/.config/fcx/converters/.
  -d --deps        Check deps for all converters, or for named TARGET ext(s).
  -m --methods     List all converters for each TARGET ext.
  -i --inputs      List input extensions that can produce each output ext.
  -o --outputs     List output extensions producible from each input ext.
  -R --recover     Restore most-recent fcx backup from Trash into CWD.
  -O --overwrite   Skip trash backup for same-format (in-place) transforms.
  -v --verbose     Stream live stdout/stderr from every shell command.
  --dry-run        Print commands without executing.
```

## TARGET syntax

```
SPEC[:METHOD[:PARAMS]]
```

| Part | Description |
|------|-------------|
| `SPEC` | Output extension (`pdf`, `jpg`, …) or explicit output path (`report.pdf`). Omit to default to `pdf`. |
| `METHOD` | Name or unique prefix of the converter to prefer (e.g. `pandoc`, `l1`, `crop`). Fuzzy prefix-matched; falls back to the next available converter. |
| `PARAMS` | Parameter string passed verbatim to the converter. Some converters require it. |

**Examples:**

| TARGET | Meaning |
|--------|---------|
| `pdf` | Convert to PDF using best available converter |
| `pdf:pandoc` | Force pandoc (or pandoc-wk if available) |
| `jpg:l1` | In-place JPG compression at quality 85 |
| `jpg:crop:50x50` | Center-crop to 50% of each axis |
| `jpg:annotate:Draft v2` | Overlay label "Draft v2" |
| `report.pdf` | Output to explicit path `report.pdf` |
| `wav:16k` | Convert audio to 16 kHz mono WAV |

## Merge vs per-file mode

| to_format | mode | notes |
|-----------|------|-------|
| `pdf`, `txt` | **merge** | all inputs → one output file |
| same as input | **in-place** | per-file, trash backup first |
| anything else | **per-file** | each input → own output file |

### Output naming

- `SPEC` is a path → that is the output file
- Merge mode → `{first_input_stem}.{ext}` in CWD
- Per-file mode → `{each_input_stem}.{ext}` in CWD
- In-place → modifies the input file in-place

## In-place transforms and trash backup

When the output format matches the input format, `fcx` runs an in-place transform. Before modifying anything it copies all input files to a timestamped FreeDesktop Trash directory:

```
~/.local/share/Trash/files/fcx_20260519_143022_jpg/
~/.local/share/Trash/info/fcx_20260519_143022_jpg.trashinfo
```

The backup is pure Python — no external trash tools needed. Recovery is one command:

```bash
fcx -R         # restore most recent backup into CWD
fcx -R jpg     # restore most recent jpg backup
fcx -O ...     # skip backup entirely (--overwrite)
```

## Registered converters

### → PDF (merge mode)

| From formats | Converter | Backend | Notes |
|---|---|---|---|
| `pdf` | builtin-copy-pdf | — | Passthrough / copy |
| `jpg`, `png`, `gif`, `bmp`, `tiff`, `webp` | imagemagick | `convert` | Direct image→PDF |
| `svg` | inkscape-pdf | `inkscape` | High-fidelity vector |
| `svg` | imagemagick-svg-pdf | `convert` | Fallback |
| `docx`, `odt`, `pptx`, `xls`, `xlsx`, `rtf`, `csv` | libreoffice | `loffice --headless` | |
| `md`, `rst`, `html`, `xhtml`, `docx`, `rtf`, `txt` | pandoc-wk | `pandoc` + `wkhtmltopdf` | Best pandoc output |
| `md`, `rst`, `html`, `tex`, `csv`, … | pandoc | `pandoc` | Fallback |
| `html`, `xhtml`, `htm` | wkhtmltopdf | `wkhtmltopdf` | |
| `tex`, `tikz` | pdflatex | `pdflatex` | Auto-runs biber/makeglossaries |

### → TXT (merge mode)

| From formats | Converter | Backend |
|---|---|---|
| `txt`, `md`, `rst` | builtin-copy-txt | — |
| `pdf` | pdftotext | `pdftotext` |
| any above | builtin-via-pdf | chains →pdf, then pdftotext |

### → Markup (merge mode)

| To format | Converter | Backend |
|---|---|---|
| `md` | pandoc-md | `pandoc` |
| `rst` | pandoc-rst | `pandoc` |
| `html` | pandoc-html | `pandoc` |

### → Image format conversion (per-file)

| From | To | Converter | Backend |
|---|---|---|---|
| `svg` | `pdf` | inkscape-pdf | `inkscape` |
| `svg` | `png` | inkscape-png | `inkscape` |
| `svg` | `jpg` | inkscape-jpg | `inkscape` + `convert` |
| any image | `png` | imagemagick-to-img | `convert` |
| any image | `jpg` | imagemagick-to-jpg | `convert` |

### → JPG in-place transforms (per-file, trash backup)

| METHOD | Deps | Effect |
|--------|------|--------|
| `l0` | `jpegtran` | Lossless optimise + progressive |
| `l1` | `jpegoptim` | q 85 |
| `l2` | `jpegoptim`, `convert` | q 75; resize if > 2666 px |
| `l3` | `jpegoptim`, `convert` | q 60; resize if > 800 px |
| `luh` | `convert` | Fit 3840×2160, q 90 |
| `lum` | `convert` | Fit 3840×2160, q 60 |
| `lul` | `convert` | Fit 3840×2160, q 40 |
| `lfh` | `convert` | Fit 1920×1080, q 90 |
| `lfm` | `convert` | Fit 1920×1080, q 60 |
| `lfl` | `convert` | Fit 1920×1080, q 40 |
| `lm` | `convert` | Fit 800×800, q 60 |
| `lb1` | `convert` | B&W document binarise |
| `crop` | `convert`, `identify` | Center-crop percentage per axis (`PARAMS: WxH`) |
| `cropabs` | `convert`, `identify` | Center-crop in pixels (`PARAMS: WxH`) |
| `annotate` | `convert`, `identify` | Overlay text label at bottom (`PARAMS: text`) |
| `version` | `convert`, `jpegtran`, `jpegoptim` | Creates `ver/` with l0–l3 comparison set |
| `montage` | `convert` | Square-crop + assemble montage grid (`PARAMS: cell_px`) |

### → PNG in-place transforms

| METHOD | Deps | Effect |
|--------|------|--------|
| `l0-png` | `optipng` | Lossless optimise |
| `l1-png` | `optipng` | Aggressive lossless optimise |
| `l2-png` | `optipng`, `convert` | Resize if > 2666 px |
| `l3-png` | `optipng`, `convert` | Resize if > 800 px |
| `lb1-png` | `convert` | B&W document binarise |
| `crop-png` | `convert`, `identify` | Center-crop percentage (`PARAMS: WxH`) |
| `cropabs-png` | `convert`, `identify` | Center-crop in pixels (`PARAMS: WxH`) |
| `annotate-png` | `convert`, `identify` | Overlay text label |

### → WAV (per-file)

| From formats | Converter | Backend | Effect |
|---|---|---|---|
| `mp3`, `m4a`, `ogg`, `flac`, `aac`, `opus`, `wma`, `wav`, `mp4`, … | ffmpeg-16k | `ffmpeg` | 16 kHz mono WAV |

## Checking what is available

```bash
fcx -d                   # all converters and their deps
fcx -d pdf               # deps for →pdf converters only
fcx -m pdf               # list all →pdf converters, which would be selected
fcx -m jpg               # list all →jpg converters
fcx -i pdf               # what input formats can produce pdf?
fcx -o docx              # what output formats can docx produce?
```

## Extending fcx

Converters live in `CONVERTERS` lists inside Python files. Three layers are merged at startup — later layers win for same-named converters; unique names coexist with user/system versions listed first:

```
1. built-in   fcx/converters/*.py         (ships with fcx)
2. system     /etc/xdg/fcx/converters/*.py
3. user       ~/.config/fcx/converters/*.py   ← highest priority
```

### Add a custom converter

Copy a built-in converter file to your user config dir:

```bash
fcx -I pandoc              # copies pandoc.py to ~/.config/fcx/converters/pandoc.py
fcx -I                     # list all built-in converter files
```

Then edit the copy. Delete the file to revert to the built-in.

### Write one from scratch

Create `~/.config/fcx/converters/mytools.py`:

```python
from pathlib import Path
from typing import List, Optional
from fcx.core import Converter, run

def _my_converter(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["mytool", "--output", str(dst)] + [str(s) for s in srcs])

CONVERTERS = [
    Converter(
        name="mytool",
        from_formats=("md",),
        to_format="pdf",
        deps=["mytool"],
        params=None,
        fn=_my_converter,
        mode="merge",     # "merge" | "per-file" | "in-place" | "auto"
    ),
]
```

Verify: `fcx -d pdf` and `fcx -m pdf`.

### Converter dataclass

```python
@dataclass
class Converter:
    name: str                 # matched by METHOD prefix in TARGET
    from_formats: tuple       # input extensions (lowercase, no dot)
    to_format: str            # output extension
    deps: list                # binary names checked on PATH
    params: str | None        # human-readable PARAMS description, or None
    fn: Callable              # fn(srcs: list[Path], dst: Path, params: str | None)
    mode: str = "auto"        # dispatch mode (see above)
```

### Dispatch mode

| mode | behaviour |
|------|-----------|
| `"auto"` | merge if to_format in (pdf, txt); in-place if to==from; else per-file |
| `"merge"` | all inputs passed to fn at once, one output |
| `"per-file"` | fn called once per input, no trash backup |
| `"in-place"` | fn called once per input, trash backup before first call |

## Verbose and dry-run

```bash
fcx -v jpg:l1 photo.jpg     # stream live output from jpegoptim
fcx --dry-run pdf *.md      # print commands without running them
```

## Examples

```bash
# Document conversion
fcx report.pdf chapter.md appendix.md      # merge md → pdf
fcx txt notes.pdf slides.pptx              # merge to txt
fcx html document.docx                     # docx → html via pandoc

# Image conversion
fcx png *.svg                              # batch svg → png (inkscape)
fcx jpg diagram.svg                        # svg → jpg

# In-place image compression (all backed up to Trash first)
fcx jpg:l1 photos/*.jpg                    # compress to q85
fcx jpg:l2 photos/*.jpg                    # q75, resize if > 2666px
fcx jpg:l3 -O photos/*.jpg                 # q60, no backup (--overwrite)
fcx jpg:luh portraits/*.jpg                # fit 4K UHD, q90

# In-place image transforms
fcx jpg:crop:75x75 thumbnails/*.jpg        # center-crop to 75%
fcx jpg:cropabs:800x800 pics/*.jpg         # center-crop to 800×800px
fcx jpg:annotate:Draft *.jpg               # overlay label "Draft"
fcx jpg:lb1 scans/*.jpg                    # binarise to B&W document

# PNG optimisation
fcx png:l1-png images/*.png                # aggressive lossless optimise
fcx png:crop-png:80x80 icons/*.png         # center-crop PNGs

# Comparison sets and montage
fcx jpg:version photo.jpg                  # creates ver/ with l0–l3 comparison
fcx jpg:montage *.jpg                      # assemble 300×300 montage grid

# Audio
fcx wav:16k recordings/*.mp3               # 16 kHz mono WAV for ASR
fcx wav:16k interview.m4a                  # single file

# Dependency check
fcx -d                                     # all converters
fcx -d jpg                                 # only jpg-related converters

# Discovery
fcx -m pdf                                 # what converters exist for →pdf?
fcx -i pdf                                 # what can be converted to pdf?
fcx -o docx                                # what can docx become?

# Recovery
fcx -R                                     # restore last backup
fcx -R jpg                                 # restore last jpg backup
```

## Contributing

Fork the repository and open a pull request. Adding converters for new backend tools is the most welcome contribution — each converter file is self-contained and easy to write.

## License

GNU Affero General Public License v3.0 — see [LICENSE](LICENSE).

---

## Related projects

`fcx` sits at the intersection of document conversion and image processing automation. The tables below place it in context.

### Document conversion backends

These are the system tools that `fcx` dispatches to. Each has a different sweet spot; `fcx` selects the best available one automatically.

| Tool | License | Best for | Used in fcx |
|------|---------|---------|-------------|
| [pandoc](https://github.com/jgm/pandoc) | GPL-2 | Universal markup converter; md/rst/html/docx → pdf/html/txt and 50+ formats | **Yes** — `pandoc`, `pandoc-wk` |
| [LibreOffice](https://www.libreoffice.org/) | MPL-2 | Office formats (docx/pptx/xlsx/odt) headless conversion | **Yes** — `libreoffice` (via `loffice --headless`) |
| [wkhtmltopdf](https://github.com/wkhtmltopdf/wkhtmltopdf) | LGPL-3 | HTML → PDF with full CSS/JS rendering (WebKit engine) | **Yes** — `wkhtmltopdf` |
| [ImageMagick](https://github.com/ImageMagick/ImageMagick) | Apache-2 | Image ↔ image, raster → PDF, compositing | **Yes** — `convert`, `identify`, `montage` |
| [Inkscape](https://gitlab.com/inkscape/inkscape) | GPL-3 | SVG → PDF/PNG with full vector fidelity | **Yes** — `inkscape --export-type` |
| [pdflatex / TeX Live](https://tug.org/texlive/) | Mixed/Free | TeX → PDF with bibliography and glossary management | **Yes** — `pdflatex`, `biber`, `makeglossaries` |
| [poppler-utils](https://poppler.freedesktop.org/) | GPL-2 | PDF text extraction (`pdftotext`), PDF merge (`pdfjam`) | **Yes** — `pdftotext`, `pdfjam` |
| [ffmpeg](https://ffmpeg.org/) | LGPL-2.1 | Audio/video format conversion | **Yes** — `ffmpeg-16k` |
| [jpegoptim](https://github.com/tjko/jpegoptim) | GPL-2 | Lossy JPG compression with quality targets | **Yes** — `l1`–`l3` converters |
| [jpegtran](http://jpegclub.org/jpegtran/) | BSD | Lossless JPG transform and optimisation | **Yes** — `l0` converter |
| [optipng](https://optipng.sourceforge.net/) | zlib/libpng | Lossless PNG compression | **Yes** — `l0-png`–`l3-png` |
| [Weasyprint](https://weasyprint.org/) | BSD | HTML → PDF via Python (no Qt/WebKit); CSS Paged Media | No — alternative to wkhtmltopdf |
| [unoconv](https://github.com/unoconv/unoconv) | GPL-2 | LibreOffice UNO bridge; similar to `loffice --headless` | No — superseded by loffice --headless |

### Python document conversion libraries

Pure Python or wrapper libraries that avoid shelling out. `fcx` prefers system tools for flexibility but these are useful when you need embedded conversion.

| Library | License | Stars | Best for |
|---------|---------|-------|---------|
| [pypandoc](https://github.com/JessicaTegner/pypandoc) | MIT | 1.3k | Python wrapper around pandoc; supports all pandoc formats |
| [docx2pdf](https://github.com/AlJohri/docx2pdf) | MIT | 2.1k | DOCX → PDF on macOS (Word) / Linux (LibreOffice) |
| [img2pdf](https://github.com/josch/img2pdf) | LGPL-3 | 1.0k | Lossless image → PDF; preserves original pixels without re-encoding |
| [pdf2image](https://github.com/Belval/pdf2image) | MIT | 1.8k | PDF → PIL Image objects via poppler |
| [python-pptx](https://github.com/scanny/python-pptx) | MIT | 2.6k | Read/write PPTX; no built-in PDF export |
| [pymupdf](https://github.com/pymupdf/PyMuPDF) | AGPL-3 / commercial | 4.8k | High-speed PDF/XPS/EPUB rendering, extraction, annotation |
| [weasyprint](https://github.com/Kozea/WeasyPrint) | BSD | 7.1k | HTML/CSS → PDF in Python; CSS Paged Media support |

### Batch file conversion tools

CLI and GUI tools that wrap multiple conversion backends — the category closest to `fcx` itself.

| Tool | Type | Platform | License | Formats | Notes |
|------|------|----------|---------|---------|-------|
| **fcx** (this) | CLI | Linux | AGPL-3 | docs, images, audio | Extensible registry; in-place transforms; trash backup; scriptable |
| [fileConverter](https://github.com/Tichau/FileConverter) | GUI | Windows | GPL-3 | images, audio, video, docs | Right-click shell extension; uses ffmpeg/ImageMagick |
| [unoconv](https://github.com/unoconv/unoconv) | CLI | Linux/macOS | GPL-2 | office formats only | LibreOffice UNO bridge; no longer actively maintained |
| [pandoc](https://github.com/jgm/pandoc) | CLI | Any | GPL-2 | markup/docs only | The gold standard for document conversion; no images or audio |
| [Converseen](https://converseen.fasterland.net/) | GUI | Linux/Windows | GPL-3 | images only | Qt/ImageMagick batch image converter |
| [Kramdown-AsciiDoc](https://github.com/asciidoctor/kramdown-asciidoc) | CLI | Any | MIT | md → asciidoc | Single format pair, deep conversion fidelity |

### Image optimisation CLIs

Tools focused on reducing image file size. `fcx` wraps these under a consistent interface with trash backup.

| Tool | License | Algorithm | In fcx |
|------|---------|-----------|--------|
| [jpegoptim](https://github.com/tjko/jpegoptim) | GPL-2 | Progressive JPEG; quality targets; strips metadata | **Yes** — `l1`, `l2`, `l3` |
| [jpegtran](http://jpegclub.org/jpegtran/) | BSD | Lossless DCT operations; progressive scan | **Yes** — `l0` |
| [optipng](https://optipng.sourceforge.net/) | zlib | Lossless PNG deflate optimisation | **Yes** — `l0-png`–`l3-png` |
| [pngquant](https://pngquant.org/) | GPL-3 | Lossy PNG palette quantisation (often 60–80% savings) | No — lossy; would fit a future `l1-png` lossy variant |
| [oxipng](https://github.com/shssoichiro/oxipng) | MIT | Multi-threaded lossless PNG (Rust); faster than optipng | No — could replace optipng as a future built-in |
| [Squoosh CLI](https://github.com/GoogleChromeLabs/squoosh) | Apache-2 | WASM-based multi-format image optimisation | No — Node.js dependency |
| [ImageOptim-CLI](https://github.com/JamieMason/ImageOptim-CLI) | MIT | Orchestrates multiple tools (jpegtran, pngquant, …) | No — macOS-native tools |
