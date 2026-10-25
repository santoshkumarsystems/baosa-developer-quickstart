#!/usr/bin/env bash
set -e

cd "$HOME/Projects/baosa-developer-quickstart"
source .venv/bin/activate
python -m streamlit run app.py
