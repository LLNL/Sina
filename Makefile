SHELL=/bin/bash

VENV=venv
VACT=$(VENV)/bin/activate
PR_ACT="Enter 'source $(VACT)' or 'source $(VACT).csh' to activate the virtual env"

.PHONY: all clean docs install tests web_deps

install:
	@if test ! -d $(VENV); then \
	  echo "Making virtual environment in $(VENV)"; \
	  python -m virtualenv $(VENV); \
	  set -e; \
	else \
	  echo "You already have the virtual environment $(VENV)"; \
	fi; \
	$(VENV)/bin/pip install --upgrade pip; \
	$(VENV)/bin/pip install -r requirements.txt; \
	$(VENV)/bin/pip install -e .; \
	echo $(PR_ACT)

all: clean docs tests web_deps

docs: install
	@$(VENV)/bin/tox -e docs

tests:
	@tests/run_all_tests.sh

web_deps: install
	@($(VENV)/bin/pip install -r web-requirements.txt && \
	  echo "Web dependencies installed" && echo $(PR_ACT)) || \
	  echo "Unable to install web dependencies. Refer to README.md."

clean: clean-notebooks
	@rm -rf build docs/build docs/source/generated_docs .tox
	@rm -rf fake.sqlite nosetests.xml
	@rm -rf sina.egg-info $(VENV)
	@rm -rf tests/test_venv
	@find . -name "*.pyc" -exec rm -f {} \; >& /dev/null
	@find . -name __pycache__ -exec rm -rf {} \; >& /dev/null

clean-notebooks:
	@!(!(jupyter nbconvert --ClearOutputPreprocessor.enabled=True --log-level WARN --inplace \
			 examples/*/*.ipynb \
			 examples/*.ipynb) \
	   && echo "You must have Jupyter available; activate the sina venv or install it locally")
