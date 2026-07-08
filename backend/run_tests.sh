#!/bin/bash
cd /root/.openclaw/workspace/sentiment-analysis/backend
source venv/bin/activate
export PYTHONPATH=/root/.openclaw/workspace/sentiment-analysis:/root/.openclaw/workspace/sentiment-analysis/backend:$PYTHONPATH
python tests/test_full_validation.py
