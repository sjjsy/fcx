"""Pandoc converters: documents → pdf / txt / md / rst / html."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fcx.core import Converter, run

_PANDOC_IN = ("md", "rst", "html", "xhtml", "docx", "odt", "rtf", "tex", "txt", "csv")


def _pandoc_pdf_wk(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["pandoc"]
        + [str(s) for s in srcs]
        + ["--pdf-engine=wkhtmltopdf", "-o", str(dst)])


def _pandoc_pdf(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["pandoc"]
        + [str(s) for s in srcs]
        + ["-o", str(dst)])


def _pandoc_txt(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["pandoc", "--to=plain"]
        + [str(s) for s in srcs]
        + ["-o", str(dst)])


def _pandoc_md(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["pandoc", "--to=markdown"]
        + [str(s) for s in srcs]
        + ["-o", str(dst)])


def _pandoc_rst(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["pandoc", "--to=rst"]
        + [str(s) for s in srcs]
        + ["-o", str(dst)])


def _pandoc_html(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    run(["pandoc", "--to=html", "--standalone"]
        + [str(s) for s in srcs]
        + ["-o", str(dst)])


CONVERTERS = [
    Converter(
        name="pandoc-wk",
        from_formats=("md", "rst", "html", "xhtml", "docx", "odt", "rtf", "txt"),
        to_format="pdf",
        deps=["pandoc", "wkhtmltopdf"],
        params=None,
        fn=_pandoc_pdf_wk,
        mode="merge",
    ),
    Converter(
        name="pandoc",
        from_formats=_PANDOC_IN,
        to_format="pdf",
        deps=["pandoc"],
        params=None,
        fn=_pandoc_pdf,
        mode="merge",
    ),
    Converter(
        name="pandoc-txt",
        from_formats=_PANDOC_IN,
        to_format="txt",
        deps=["pandoc"],
        params=None,
        fn=_pandoc_txt,
        mode="merge",
    ),
    Converter(
        name="pandoc-md",
        from_formats=_PANDOC_IN,
        to_format="md",
        deps=["pandoc"],
        params=None,
        fn=_pandoc_md,
        mode="merge",
    ),
    Converter(
        name="pandoc-rst",
        from_formats=_PANDOC_IN,
        to_format="rst",
        deps=["pandoc"],
        params=None,
        fn=_pandoc_rst,
        mode="merge",
    ),
    Converter(
        name="pandoc-html",
        from_formats=_PANDOC_IN,
        to_format="html",
        deps=["pandoc"],
        params=None,
        fn=_pandoc_html,
        mode="merge",
    ),
]
