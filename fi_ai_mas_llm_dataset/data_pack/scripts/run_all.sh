#!/usr/bin/env bash
# Sinh lai toan bo du lieu (deterministic, seed co dinh) roi kiem tra.
set -euo pipefail
cd "$(dirname "$0")"
python3 gen_kb.py        # menu.csv, faq.csv, faq_topics.json
python3 gen_docs.py      # docs/*.docx|pdf + doc_sections_manifest.json
python3 gen_router.py    # router_*.json (can faq_topics.json)
python3 gen_cache.py     # intent_extraction, cache_seed, cache_eval_500
python3 gen_tts.py       # tts_cases.json
python3 gen_eval.py      # rag_eval_20.json (can faq.csv + manifest)
python3 validate.py
