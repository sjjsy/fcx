"""LibreOffice converters: office formats → pdf / txt."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional

from fcx.core import Converter, run

_OFFICE_FORMATS = ("docx", "doc", "odt", "pptx", "ppt", "odp", "xlsx", "xls", "ods", "rtf", "csv")


def _loffice_pdf(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for src in srcs:
            run(["loffice", "--headless", "--convert-to", "pdf",
                 "--outdir", tmp, str(src)])
        tmp_pdfs = list(Path(tmp).glob("*.pdf"))
        if not tmp_pdfs:
            raise RuntimeError("loffice produced no PDF output")
        if len(tmp_pdfs) == 1:
            import shutil
            shutil.copy2(tmp_pdfs[0], dst)
        else:
            # Multiple PDF outputs: try to merge with pdfjam, else copy first
            try:
                run(["pdfjam"] + [str(p) for p in sorted(tmp_pdfs)] + ["--outfile", str(dst)])
            except Exception:
                import shutil
                shutil.copy2(sorted(tmp_pdfs)[0], dst)


def _loffice_txt(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        parts = []
        for src in srcs:
            run(["loffice", "--headless", "--convert-to", "txt:Text",
                 "--outdir", tmp, str(src)])
        txt_files = sorted(Path(tmp).glob("*.txt"))
        parts = [f.read_text(errors="replace") for f in txt_files]
        dst.write_text("\n\n".join(parts))


CONVERTERS = [
    Converter(
        name="libreoffice",
        from_formats=_OFFICE_FORMATS,
        to_format="pdf",
        deps=["loffice"],
        params=None,
        fn=_loffice_pdf,
        mode="merge",
    ),
    Converter(
        name="libreoffice-txt",
        from_formats=_OFFICE_FORMATS,
        to_format="txt",
        deps=["loffice"],
        params=None,
        fn=_loffice_txt,
        mode="merge",
    ),
]
