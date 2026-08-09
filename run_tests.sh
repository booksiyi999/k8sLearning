#!/bin/bash
cd /home/admin/k8s-quest/backend
uv venv .venv --python 3.12 2>/dev/null
uv pip install -e ".[dev]" --python .venv/bin/python 2>&1 | tail -5
.venv/bin/python -m pytest tests/qa_attack_misjudge.py tests/qa_attack_ch17_ch28_concepts.py tests/qa_attack_terminal_security.py -v --tb=short 2>&1 | head -150
