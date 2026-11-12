"""Copy the files needed by the API-first architecture from fi_ai_mas_llm_dataset/data_pack into data/.

Usage: python scripts/prepare_data.py
The source folder is left untouched. Re-running overwrites the copies.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "fi_ai_mas_llm_dataset" / "data_pack" / "data"
DST = ROOT / "data"

# (source relative to SRC, destination relative to DST)
FILES = [
    ("kb/menu.csv", "raw/menu/menu.csv"),
    ("kb/faq.csv", "raw/faq/faq.csv"),
    ("kb/docs/doc_sections_manifest.json", "raw/documents/doc_sections_manifest.json"),
    ("eval/rag_eval_20.json", "evaluation/rag_eval_20.json"),
    ("eval/tts_cases.json", "evaluation/tts_cases.json"),
    ("router/router_test.json", "evaluation/router_test.json"),
]
DOC_SUFFIXES = {".docx", ".pdf"}
EMPTY_DIRS = ["processed", "inbox"]


def main() -> int:
    pairs = [(SRC / s, DST / d) for s, d in FILES]
    pairs += [
        (p, DST / "raw" / "documents" / p.name)
        for p in sorted((SRC / "kb" / "docs").iterdir())
        if p.suffix.lower() in DOC_SUFFIXES
    ]

    missing = [str(s) for s, _ in pairs if not s.is_file()]
    if missing:
        print("Missing source files:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1

    for src, dst in pairs:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"copied {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")

    for name in EMPTY_DIRS:
        (DST / name).mkdir(parents=True, exist_ok=True)

    print(f"Done: {len(pairs)} files copied into {DST.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

