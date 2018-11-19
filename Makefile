SHELL=/bin/bash

VENV=venv
VACT=$(VENV)/bin/activate
PR_ACT="Enter 'source $(VACT)' or 'source $(VACT).csh' to activate the virtual env"

.PHONY: all clean clean-files clean-notebooks clean-tests docs install tests web_deps

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
	$(VENV)/bin/pip install -e .[jupyter]; \
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

# WARNING: Order is very important
clean: clean-notebooks clean-files 

clean-files:  clean-tests
	@rm -rf build docs/build docs/source/generated_docs
	@rm -rf sina.egg-info $(VENV)
	@find . -name "*.pyc" -exec rm -f {} \; >& /dev/null
	@find . -name __pycache__ -exec rm -rf {} \; >& /dev/null

# It is assumed any version/installation of Jupyter will properly remove outputs
# and that we do not want to have to [re-]install the virtual environment just
# to remove outputs from notebooks.
clean-notebooks:
	@NOTEBOOKS=`find examples -name "*.ipynb" -print`; \
	JUPYTER_EXE=`which jupyter 2> /dev/null`; \
	NBCONVERT="--ClearOutputPreprocessor.enabled=True --log-level WARN --inplace"; \
	if test -f $(VENV)/bin/jupyter; then \
	  $(VENV)/bin/jupyter nbconvert $$NBCONVERT $$NOTEBOOKS; \
	elif test -n "$$JUPYTER_EXE" && test -f $$JUPYTER_EXE; then \
	  $$JUPYTER_EXE nbconvert $$NBCONVERT $$NOTEBOOKS; \
	else \
	  echo "Sina must be installed.  Run 'make'."; \
	fi

clean-tests:
	@rm -rf .tox fake.sqlite nosetests*.xml*
	@rm -rf tests/test_venv
	@rm -rf tests/run_tests
