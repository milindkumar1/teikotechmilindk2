PYTHON ?= python

.PHONY: setup pipeline dashboard test

setup:
	$(PYTHON) -m pip install -r requirements.txt

pipeline:
	$(PYTHON) load_data.py
	$(PYTHON) run_analysis.py

dashboard:
	$(PYTHON) -m streamlit run dashboard.py --server.address=0.0.0.0 --server.port=$${PORT:-8501}

test:
	$(PYTHON) -m pytest

