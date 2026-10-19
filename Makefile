PYTHON ?= python

.PHONY: setup pipeline dashboard

setup:
	$(PYTHON) -m pip install -r requirements.txt

# load_data.py creates the tables from scratch, so remove the old database first
pipeline:
	rm -f teiko.db
	$(PYTHON) load_data.py
	$(PYTHON) initial_analysis.py
	$(PYTHON) statistical_analysis.py
	$(PYTHON) data_subset_analysis.py

dashboard:
	$(PYTHON) -m streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
