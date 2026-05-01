#!/usr/bin/env python3
"""Build the NeurIPS PDF report and clean up temporary files.

Usage:
    uv run python reports/neurips/build_pdf.py

Keeps:
    - datathon_report.pdf
    - datathon_report.tex
    - references.bib
    - neurips_2025.sty
    - figures/*.pdf
    - *.py scripts

Removes:
    - All .aux, .log, .out, .bbl, .blg, .synctex.gz files
"""

import subprocess
import sys
from pathlib import Path

REPORT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = REPORT_DIR.parent.parent.resolve()
TEX_FILE = REPORT_DIR / "datathon_report.tex"


def run(cmd: list[str], desc: str, cwd: Path = REPORT_DIR) -> None:
    print(f"  → {desc}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"ERROR: {desc} failed")
        print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
        sys.exit(1)


def main() -> None:
    if not TEX_FILE.exists():
        print(f"ERROR: {TEX_FILE} not found")
        sys.exit(1)

    print("Building NeurIPS report...")

    # 1. Generate figures
    print("\n[1/4] Generating figures...")
    run([sys.executable, "-m", "src.datathon.report_figures"], "Generate figures", cwd=REPO_ROOT)

    # 2. Clean old intermediates
    print("\n[2/4] Cleaning old intermediates...")
    for ext in ("aux", "log", "out", "bbl", "blg", "synctex.gz"):
        for f in REPORT_DIR.glob(f"*.{ext}"):
            f.unlink()

    # 3. Compile LaTeX (pdflatex → bibtex → pdflatex → pdflatex)
    print("\n[3/4] Compiling LaTeX...")
    run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", str(TEX_FILE.name)], "pdflatex (1)")
    run(["bibtex", "datathon_report"], "bibtex")
    run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", str(TEX_FILE.name)], "pdflatex (2)")
    run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", str(TEX_FILE.name)], "pdflatex (3)")

    # 4. Clean intermediates again (keep only PDF, tex, bib, sty, figure PDFs, py scripts)
    print("\n[4/4] Cleaning temporary files...")
    keep_names = {
        "datathon_report.pdf",
        "datathon_report.tex",
        "references.bib",
        "neurips_2025.sty",
        "build_pdf.py",
        "verify_data.py",
    }
    for f in REPORT_DIR.iterdir():
        if f.is_file() and f.name not in keep_names and not f.name.endswith(".py"):
            f.unlink()
            print(f"    removed {f.name}")

    pdf = REPORT_DIR / "datathon_report.pdf"
    if pdf.exists():
        size_kb = pdf.stat().st_size / 1024
        print(f"\n✅ Build complete: {pdf} ({size_kb:.0f} KB)")
    else:
        print("\n❌ Build failed: PDF not found")
        sys.exit(1)


if __name__ == "__main__":
    main()
