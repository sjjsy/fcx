"""PDF tools: pdftotext (pdf → txt) and pdfjam (pdf merge)."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from fcx.core import Converter, run


def _pdftotext(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    if len(srcs) == 1:
        run(["pdftotext", str(srcs[0]), str(dst)])
        return
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for i, src in enumerate(srcs):
            out = Path(tmp) / f"part{i:04d}.txt"
            run(["pdftotext", str(src), str(out)])
            parts.append(out.read_text(errors="replace"))
        dst.write_text("\n\n".join(parts))


def _pdfjam(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["pdfjam"] + [str(s) for s in srcs] + ["--outfile", str(dst)])


CONVERTERS = [
    Converter(
        name="pdftotext",
        from_formats=("pdf",),
        to_format="txt",
        deps=["pdftotext"],
        params=None,
        fn=_pdftotext,
        mode="merge",
    ),
    Converter(
        name="pdfjam",
        from_formats=("pdf",),
        to_format="pdf",
        deps=["pdfjam"],
        params=None,
        fn=_pdfjam,
        mode="merge",
    ),
]
