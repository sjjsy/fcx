"""Built-in converters: copy passthrough and via-pdf chain. No external deps."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from fcx.core import Converter, run, select_converter, load_converters


# ── copy ──────────────────────────────────────────────────────────────────────

def _copy_merge(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    if len(srcs) == 1:
        shutil.copy2(srcs[0], dst)
        return
    raise RuntimeError(
        "builtin-copy cannot merge multiple files; install pdfjam for PDF merging."
    )


def _copy_txt(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    """Concatenate text/markup files into one output."""
    parts = []
    for src in srcs:
        parts.append(src.read_text(errors="replace"))
    dst.write_text("\n\n".join(parts))


# ── via-pdf chain ─────────────────────────────────────────────────────────────

def _via_pdf(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    """Convert any supported format → txt by chaining: input → pdf → txt."""
    convs = load_converters()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_pdf = Path(tmp) / "out.pdf"

        # Step 1: to pdf
        input_ext = srcs[0].suffix.lstrip(".").lower()
        pdf_conv, _ = select_converter(convs, input_ext, "pdf")
        if pdf_conv is None:
            raise RuntimeError(f"No converter available: {input_ext} → pdf")
        pdf_conv.fn(srcs, tmp_pdf, params)

        # Step 2: pdf to txt
        txt_conv, _ = select_converter(convs, "pdf", "txt")
        if txt_conv is None:
            raise RuntimeError("No converter available: pdf → txt (install poppler-utils)")
        txt_conv.fn([tmp_pdf], dst, params)


CONVERTERS = [
    Converter(
        name="builtin-copy-pdf",
        from_formats=("pdf",),
        to_format="pdf",
        deps=[],
        params=None,
        fn=_copy_merge,
    ),
    Converter(
        name="builtin-copy-txt",
        from_formats=("txt", "md", "rst"),
        to_format="txt",
        deps=[],
        params=None,
        fn=_copy_txt,
        mode="merge",
    ),
    Converter(
        name="builtin-via-pdf",
        from_formats=(
            "docx", "odt", "pptx", "ppt", "xlsx", "xls", "rtf",
            "md", "rst", "html", "xhtml", "tex", "svg", "jpg", "png",
        ),
        to_format="txt",
        deps=[],
        params=None,
        fn=_via_pdf,
        mode="merge",
    ),
]
