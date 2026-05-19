"""Inkscape converters: SVG → PDF / PNG / JPG."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fcx.core import Converter, run


def _svg_pdf(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["inkscape", "--export-type=pdf",
         f"--export-filename={dst}", str(srcs[0])])


def _svg_png(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["inkscape", "--export-type=png",
         f"--export-filename={dst}", str(srcs[0])])


def _svg_jpg(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    # Inkscape exports PNG; pipe through convert for JPG
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_png = tmp.name
    run(["inkscape", "--export-type=png",
         f"--export-filename={tmp_png}", str(srcs[0])])
    run(["convert", tmp_png, str(dst)])
    import os
    os.unlink(tmp_png)


CONVERTERS = [
    Converter(
        name="inkscape-pdf",
        from_formats=("svg",),
        to_format="pdf",
        deps=["inkscape"],
        params=None,
        fn=_svg_pdf,
    ),
    Converter(
        name="inkscape-png",
        from_formats=("svg",),
        to_format="png",
        deps=["inkscape"],
        params=None,
        fn=_svg_png,
    ),
    Converter(
        name="inkscape-jpg",
        from_formats=("svg",),
        to_format="jpg",
        deps=["inkscape", "convert"],
        params=None,
        fn=_svg_jpg,
    ),
]
