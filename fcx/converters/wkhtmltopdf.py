"""wkhtmltopdf converter: HTML / XHTML → PDF."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from fcx.core import Converter, run


def _wk_pdf(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    if len(srcs) == 1:
        run(["wkhtmltopdf", str(srcs[0]), str(dst)])
        return
    with tempfile.TemporaryDirectory() as tmp:
        tmp_pdfs = []
        for i, src in enumerate(srcs):
            out = Path(tmp) / f"part{i:04d}.pdf"
            run(["wkhtmltopdf", str(src), str(out)])
            tmp_pdfs.append(out)
        if shutil.which("pdfjam"):
            run(["pdfjam"] + [str(p) for p in tmp_pdfs] + ["--outfile", str(dst)])
        else:
            run(["convert"] + [str(p) for p in tmp_pdfs] + [str(dst)])


CONVERTERS = [
    Converter(
        name="wkhtmltopdf",
        from_formats=("html", "xhtml", "htm"),
        to_format="pdf",
        deps=["wkhtmltopdf"],
        params=None,
        fn=_wk_pdf,
        mode="merge",
    ),
]
