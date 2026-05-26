"""ImageMagick converters: image format conversion and in-place transforms."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from fcx.core import Converter, run, parse_wxh


# ── helpers ───────────────────────────────────────────────────────────────────

def _dims(path: Path):
    from fcx import core as _core
    if _core.dry_run:
        return 1920, 1080  # safe placeholder dimensions in dry-run
    result = subprocess.run(
        ["identify", "-format", "%wx%h", str(path)],
        capture_output=True, text=True, check=True,
    )
    w, h = result.stdout.strip().split("x")
    return int(w), int(h)


def _resize_if_larger(src: Path, dst: Path, max_px: int, quality: int) -> None:
    w, h = _dims(src)
    if max(w, h) > max_px:
        run(["convert", str(src), "-resize", f"{max_px}x{max_px}>",
             "-quality", str(quality), str(dst)])
    else:
        run(["convert", str(src), "-quality", str(quality), str(dst)])


# ── format conversion ─────────────────────────────────────────────────────────

def _any_to_any(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["convert", str(srcs[0]), str(dst)])


def _imgs_to_pdf(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["convert"] + [str(s) for s in srcs] + [str(dst)])


def _svg_to_img(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["convert", str(srcs[0]), str(dst)])


def _fit(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    """Convert and resize to fit within WxH box, e.g. params='600x600'."""
    pw, ph = parse_wxh(params or "1920x1920")
    run(["convert", str(srcs[0]), "-resize", f"{pw}x{ph}>", str(dst)])


# ── JPG in-place compression ─────────────────────────────────────────────────

def _l0_jpg(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    run(["jpegtran", "-optimize", "-progressive", "-outfile", str(tmp_path), str(srcs[0])])
    shutil.move(str(tmp_path), str(dst))


def _l1_jpg(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    if srcs[0] != dst:
        shutil.copy2(srcs[0], dst)
    run(["jpegoptim", "-m85", str(dst)])


def _l2_jpg(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    _resize_if_larger(srcs[0], tmp_path, 2666, 75)
    run(["jpegoptim", "-m75", str(tmp_path)])
    shutil.move(str(tmp_path), str(dst))


def _l3_jpg(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    _resize_if_larger(srcs[0], tmp_path, 800, 60)
    run(["jpegoptim", "-m60", str(tmp_path)])
    shutil.move(str(tmp_path), str(dst))


def _fit_jpg(fit_w: int, fit_h: int, quality: int):
    def _fn(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
        run(["convert", str(srcs[0]),
             "-resize", f"{fit_w}x{fit_h}>",
             "-quality", str(quality),
             str(dst)])
    return _fn


def _lb1_jpg(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["convert", str(srcs[0]),
         "-colorspace", "gray", "-threshold", "50%", str(dst)])


# ── PNG in-place compression ──────────────────────────────────────────────────

def _l0_png(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    if srcs[0] != dst:
        shutil.copy2(srcs[0], dst)
    run(["optipng", "-o2", str(dst)])


def _l1_png(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    if srcs[0] != dst:
        shutil.copy2(srcs[0], dst)
    run(["optipng", "-o4", str(dst)])


def _l2_png(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    w, h = _dims(srcs[0])
    if max(w, h) > 2666:
        run(["convert", str(srcs[0]), "-resize", "2666x2666>", str(tmp_path)])
    else:
        shutil.copy2(srcs[0], tmp_path)
    run(["optipng", "-o4", str(tmp_path)])
    shutil.move(str(tmp_path), str(dst))


def _l3_png(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    w, h = _dims(srcs[0])
    if max(w, h) > 800:
        run(["convert", str(srcs[0]), "-resize", "800x800>", str(tmp_path)])
    else:
        shutil.copy2(srcs[0], tmp_path)
    run(["optipng", "-o4", str(tmp_path)])
    shutil.move(str(tmp_path), str(dst))


def _lb1_png(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["convert", str(srcs[0]),
         "-colorspace", "gray", "-threshold", "50%", str(dst)])


# ── Crop transforms ───────────────────────────────────────────────────────────

def _crop(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    """Center-crop by percentage per axis. params: 'WxH' e.g. '50x50'."""
    pw, ph = parse_wxh(params or "50x50")
    w, h = _dims(srcs[0])
    cw = int(w * pw / 100)
    ch = int(h * ph / 100)
    ox = (w - cw) // 2
    oy = (h - ch) // 2
    run(["convert", str(srcs[0]),
         "-crop", f"{cw}x{ch}+{ox}+{oy}", "+repage", str(dst)])


def _cropabs(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    """Center-crop by absolute pixels. params: 'WxH' e.g. '800x600'."""
    pw, ph = parse_wxh(params or "800x600")
    w, h = _dims(srcs[0])
    ox = max(0, (w - pw) // 2)
    oy = max(0, (h - ph) // 2)
    run(["convert", str(srcs[0]),
         "-crop", f"{pw}x{ph}+{ox}+{oy}", "+repage", str(dst)])


# ── Annotate ──────────────────────────────────────────────────────────────────

def _annotate(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    """Overlay a text label in the bottom of the image."""
    text = params or "untitled"
    w, _ = _dims(srcs[0])
    pointsize = max(16, w // 40)
    run(["convert", str(srcs[0]),
         "-gravity", "South",
         "-background", "rgba(0,0,0,0.5)",
         "-fill", "white",
         "-pointsize", str(pointsize),
         "-annotate", "+0+10", text,
         str(dst)])


# ── Version comparison set ────────────────────────────────────────────────────

def _version(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    """Create ver/ subdirectory with l0–l3 quality comparison variants."""
    src = srcs[0]
    ver_dir = src.parent / "ver"
    ver_dir.mkdir(exist_ok=True)

    def _out(suffix):
        return ver_dir / f"{src.stem}-{suffix}{src.suffix}"

    # l0: lossless jpegtran
    l0 = _out("l0")
    shutil.copy2(src, l0)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    run(["jpegtran", "-optimize", "-progressive", "-outfile", str(tmp_path), str(l0)])
    shutil.move(str(tmp_path), str(l0))

    # l1: q85
    l1 = _out("l1")
    shutil.copy2(src, l1)
    run(["jpegoptim", "-m85", str(l1)])

    # l2: q75, resize if > 2666px
    l2 = _out("l2")
    _resize_if_larger(src, l2, 2666, 75)
    run(["jpegoptim", "-m75", str(l2)])

    # l3: q60, resize if > 800px
    l3 = _out("l3")
    _resize_if_larger(src, l3, 800, 60)
    run(["jpegoptim", "-m60", str(l3)])

    print(f"[VERSION] created {ver_dir}")


# ── Montage ───────────────────────────────────────────────────────────────────

def _montage(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    """Square-crop all inputs and assemble into an ImageMagick montage grid."""
    size = int(params) if params and params.isdigit() else 300
    run(["montage"]
        + [str(s) for s in srcs]
        + ["-geometry", f"{size}x{size}+2+2",
           "-gravity", "Center",
           str(dst)])


# ── CONVERTERS list ──────────────────────────────────────────────────────────

_IMG_FORMATS = ("jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp", "heic")
_IMG_FROM = tuple(f for f in _IMG_FORMATS if f not in ("jpeg",))

CONVERTERS = [
    # ── Format conversion ──
    Converter(
        name="imagemagick",
        from_formats=("jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "webp"),
        to_format="pdf",
        deps=["convert"],
        params=None,
        fn=_imgs_to_pdf,
        mode="merge",
    ),
    Converter(
        name="imagemagick-svg-pdf",
        from_formats=("svg",),
        to_format="pdf",
        deps=["convert"],
        params=None,
        fn=_any_to_any,
    ),
    Converter(
        name="imagemagick-to-img",
        from_formats=_IMG_FROM + ("svg",),
        to_format="png",
        deps=["convert"],
        params=None,
        fn=_any_to_any,
    ),
    Converter(
        name="imagemagick-to-jpg",
        from_formats=_IMG_FROM + ("svg",),
        to_format="jpg",
        deps=["convert"],
        params=None,
        fn=_any_to_any,
    ),
    Converter(
        name="fit",
        from_formats=_IMG_FROM + ("svg",),
        to_format="png",
        deps=["convert"],
        params="WxH  max bounding box, e.g. 600x600",
        fn=_fit,
    ),
    Converter(
        name="fit",
        from_formats=_IMG_FROM + ("svg",),
        to_format="jpg",
        deps=["convert"],
        params="WxH  max bounding box, e.g. 600x600",
        fn=_fit,
    ),

    # ── JPG in-place transforms ──
    Converter(
        name="l0",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["jpegtran"],
        params=None,
        fn=_l0_jpg,
        mode="in-place",
    ),
    Converter(
        name="l1",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["jpegoptim"],
        params=None,
        fn=_l1_jpg,
        mode="in-place",
    ),
    Converter(
        name="l2",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["jpegoptim", "convert"],
        params=None,
        fn=_l2_jpg,
        mode="in-place",
    ),
    Converter(
        name="l3",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["jpegoptim", "convert"],
        params=None,
        fn=_l3_jpg,
        mode="in-place",
    ),
    Converter(
        name="luh",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert"],
        params=None,
        fn=_fit_jpg(3840, 2160, 90),
        mode="in-place",
    ),
    Converter(
        name="lum",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert"],
        params=None,
        fn=_fit_jpg(3840, 2160, 60),
        mode="in-place",
    ),
    Converter(
        name="lul",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert"],
        params=None,
        fn=_fit_jpg(3840, 2160, 40),
        mode="in-place",
    ),
    Converter(
        name="lfh",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert"],
        params=None,
        fn=_fit_jpg(1920, 1080, 90),
        mode="in-place",
    ),
    Converter(
        name="lfm",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert"],
        params=None,
        fn=_fit_jpg(1920, 1080, 60),
        mode="in-place",
    ),
    Converter(
        name="lfl",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert"],
        params=None,
        fn=_fit_jpg(1920, 1080, 40),
        mode="in-place",
    ),
    Converter(
        name="lm",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert"],
        params=None,
        fn=_fit_jpg(800, 800, 60),
        mode="in-place",
    ),
    Converter(
        name="lb1",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert"],
        params=None,
        fn=_lb1_jpg,
        mode="in-place",
    ),

    # ── PNG in-place transforms ──
    Converter(
        name="l0-png",
        from_formats=("png",),
        to_format="png",
        deps=["optipng"],
        params=None,
        fn=_l0_png,
        mode="in-place",
    ),
    Converter(
        name="l1-png",
        from_formats=("png",),
        to_format="png",
        deps=["optipng"],
        params=None,
        fn=_l1_png,
        mode="in-place",
    ),
    Converter(
        name="l2-png",
        from_formats=("png",),
        to_format="png",
        deps=["optipng", "convert"],
        params=None,
        fn=_l2_png,
        mode="in-place",
    ),
    Converter(
        name="l3-png",
        from_formats=("png",),
        to_format="png",
        deps=["optipng", "convert"],
        params=None,
        fn=_l3_png,
        mode="in-place",
    ),
    Converter(
        name="lb1-png",
        from_formats=("png",),
        to_format="png",
        deps=["convert"],
        params=None,
        fn=_lb1_png,
        mode="in-place",
    ),

    # ── Geometric / visual transforms (jpg + png) ──
    Converter(
        name="crop",
        from_formats=("jpg", "jpeg", "png"),
        to_format="jpg",
        deps=["convert", "identify"],
        params="WxH  center-crop percentage per axis, e.g. 50x50",
        fn=_crop,
        mode="in-place",
    ),
    Converter(
        name="crop-png",
        from_formats=("png",),
        to_format="png",
        deps=["convert", "identify"],
        params="WxH  center-crop percentage per axis, e.g. 50x50",
        fn=_crop,
        mode="in-place",
    ),
    Converter(
        name="cropabs",
        from_formats=("jpg", "jpeg", "png"),
        to_format="jpg",
        deps=["convert", "identify"],
        params="WxH  center-crop in pixels, e.g. 800x600",
        fn=_cropabs,
        mode="in-place",
    ),
    Converter(
        name="cropabs-png",
        from_formats=("png",),
        to_format="png",
        deps=["convert", "identify"],
        params="WxH  center-crop in pixels, e.g. 800x600",
        fn=_cropabs,
        mode="in-place",
    ),
    Converter(
        name="annotate",
        from_formats=("jpg", "jpeg", "png"),
        to_format="jpg",
        deps=["convert", "identify"],
        params="text  label to overlay at image bottom",
        fn=_annotate,
        mode="in-place",
    ),
    Converter(
        name="annotate-png",
        from_formats=("png",),
        to_format="png",
        deps=["convert", "identify"],
        params="text  label to overlay at image bottom",
        fn=_annotate,
        mode="in-place",
    ),
    Converter(
        name="version",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert", "jpegtran", "jpegoptim"],
        params=None,
        fn=_version,
        mode="in-place",
    ),
    Converter(
        name="montage",
        from_formats=("jpg", "jpeg"),
        to_format="jpg",
        deps=["convert"],
        params="N  cell size in pixels (default 300)",
        fn=_montage,
        mode="merge",
    ),
]
