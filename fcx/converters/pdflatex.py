"""pdflatex converter: TeX/TikZ → PDF with optional biber/makeglossaries passes."""
from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from fcx import core


def _run(cmd: list, cwd=None) -> None:
    print(f"[CMD] {shlex.join(str(c) for c in cmd)}")
    if core.dry_run:
        return
    kw = {}
    if cwd:
        kw["cwd"] = str(cwd)
    if core.verbose:
        proc = subprocess.run(cmd, **kw)
    else:
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw
        )
    if proc.returncode != 0:
        if not core.verbose:
            err = (getattr(proc, "stderr", b"") or b"").decode(errors="replace").strip()
            if err:
                print(err, file=sys.stderr)
        raise RuntimeError(
            f"Command failed (exit {proc.returncode}): {shlex.join(str(c) for c in cmd)}"
        )


def _pdflatex(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    src = srcs[0]
    content = src.read_text(errors="replace")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for sibling in src.parent.iterdir():
            if sibling.is_file():
                shutil.copy2(sibling, tmp_dir / sibling.name)

        tex_file = tmp_dir / src.name
        base = tex_file.stem

        def _latex():
            _run(["pdflatex", "-interaction=nonstopmode",
                  "-output-directory", str(tmp_dir), str(tex_file)],
                 cwd=tmp_dir)

        _latex()

        needs_biber = "\\addbibresource" in content or "\\bibliography" in content
        needs_glossaries = "\\makeglossaries" in content

        if needs_biber:
            if shutil.which("biber"):
                _run(["biber", base], cwd=tmp_dir)
            elif shutil.which("bibtex"):
                _run(["bibtex", base], cwd=tmp_dir)

        if needs_glossaries:
            _run(["makeglossaries", base], cwd=tmp_dir)

        if needs_biber or needs_glossaries:
            _latex()
            _latex()

        pdf_out = tmp_dir / f"{base}.pdf"
        if not pdf_out.exists():
            raise RuntimeError(f"pdflatex did not produce {base}.pdf")
        shutil.copy2(pdf_out, dst)


CONVERTERS = [
    core.Converter(
        name="pdflatex",
        from_formats=("tex", "tikz"),
        to_format="pdf",
        deps=["pdflatex"],
        params=None,
        fn=_pdflatex,
        mode="per-file",
    ),
]
