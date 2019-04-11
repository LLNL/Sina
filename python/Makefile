# The following environment variables can be used to change the behavior of
# building the virtual environment:
#
#   SINA_PIP_OPTIONS = Additional options to pip (e.g., '--no-index')
#   VENV         = Name of the Sina virtual environment (default 'venv')
#   VENV_OPTIONS = Additional options when the venv is created (e.g.,
#                  '--system-site-packages' to inherit system packages

# Determine if we are on an LC system based on the presence of the wheelhouse
# Using curl (versus 'wget --spider') despite being slower since former
# appears to be installed on Macs while latter is not.
# (Sources: https://stackoverflow.com/questions/12199059,
#  https://unix.stackexchange.com/questions/84814)
#
# Notice the use of curl's '-k' (or insecure) option to check access to the
# LC wheelhouse URI.
HAVE_WHEELHOUSE=$(shell if curl -sSfk -o /dev/null https://www-lc.llnl.gov/python/wheelhouse; then echo 1; else echo 0; fi)

# Workaround for pip install failing to recognize --trusted-host options
# in requirements files (see https://github.com/pypa/pip/issues/3799).
#
# WARNING: Adding --no-index option below can cause the build to fail on a
# Mac ("no such option --trusted-host"); whereas, leaving it out resulted
# in pythonhosted.org used to upgrade pip then the trusted host for the
# requirements file.
ifeq ($(HAVE_WHEELHOUSE),1)
  SINA_PIP_OPTIONS:=--trusted-host www-lc.llnl.gov $(SINA_PIP_OPTIONS)
else
  SINA_PIP_OPTIONS:=$(SINA_PIP_OPTIONS)
endif
export SINA_PIP_OPTIONS

# TODO: Pylint issues must be addressed before including it in the normal CI
# process.
#
# Define the pylint virtual environment since it is currently built and run
# for on-demand use and not part of the normal Sina process.
PYLINT_VENV=tests/pylint_venv

# Establish a path for the Pylint capability (until build issues are addressed)
PYLINT_PATH:=$(PYLINT_VENV)/bin:$(PATH)

# We'll also check if we have access to LC and internal wheelhouses
LC_WHEELHOUSE_DIR=/usr/gapps/python/wheelhouse

NO_LINKS_FILE=no-links.txt
LC_LINKS_FILE=lc-links.txt
LC_URL_FILE=lc-url-links.txt
LINKS_FILE=requirements/links.txt

# Work-around for LC Python 3.6 installation-related issues for testing purposes
LC_PYTHON3=/usr/apps/python-3.6.0/bin
HAVE_LC_PY3=$(shell if test -d $(LC_PYTHON3); then echo 1; else echo 0; fi)
ifeq ($(HAVE_LC_PY3),1)
  TEST_PATH:=$(LC_PYTHON3):$(PATH)
else
  TEST_PATH:=$(PATH)
endif

SHELL=/bin/bash

VENV?=venv
VACT=$(VENV)/bin/activate
PR_ACT="Enter 'source $(VACT)' or 'source $(VACT).csh' to activate the virtual env"

TEST_VENV=tests/test_venv

.PHONY: all
.PHONY: cassandra
.PHONY: clean
.PHONY: clean-files
.PHONY: clean-notebooks
.PHONY: clean-tests
.PHONY: clean-tests-venv
.PHONY: docs
.PHONY: install
.PHONY: jupyter
.PHONY: links
.PHONY: pep8
.PHONY: pylint
.PHONY: tests
.PHONY: test-jupyter

install: links
	@if test ! -d $(VENV); then \
	  echo "Making virtual environment in $(VENV)"; \
	  python -m virtualenv $(VENV_OPTIONS) $(VENV); \
	  set -e; \
	else \
	  echo "You already have the virtual environment $(VENV)"; \
	fi; \
	$(VENV)/bin/pip install $(SINA_PIP_OPTIONS) --upgrade pip setuptools; \
	$(VENV)/bin/pip install $(SINA_PIP_OPTIONS) -r requirements/development.txt; \
	echo $(PR_ACT)

all: clean docs tests

# Add cassandra to an existing virtual environment since it is optional.
cassandra:
	@if test ! -d $(VENV); then \
	  echo "You must create $(VENV) first. Run 'make install'"; \
	else \
	  echo "Installing cassandra in $(VENV)"; \
	  $(VENV)/bin/pip install $(SINA_PIP_OPTIONS) -r requirements/cassandra.txt; \
	fi

docs: install
	@$(VENV)/bin/tox -e docs

# Create the virtual environment if it does not already exist.  This process
# recursively calls make.
jupyter: links
	@if test ! -d $(VENV); then \
	  echo "Installing sina core in $(VENV)"; \
	  make --no-print-directory install VENV=$(VENV); \
	else \
	  echo "You already have the virtual environment $(VENV)"; \
	fi; \
	echo "Installing jupyter in $(VENV)"; \
	$(VENV)/bin/pip install $(SINA_PIP_OPTIONS) -r requirements/jupyter.txt; \

# Ensure the appropriate requirement links are established.  This is important
# for building and testing purposes.
links:
	@if [ $(HAVE_WHEELHOUSE) == 0 ]; then \
	  echo "No LC wheelhouse URL access: using $(NO_LINKS_FILE)"; \
	  ln -sf $(NO_LINKS_FILE) $(LINKS_FILE); \
	else \
	  if test -z "$(NETWORK)"; then \
	    if test -d $(LC_WHEELHOUSE_DIR); then \
	        echo "LC wheelhouse directory access: using $(LC_LINKS_FILE)"; \
	        ln -sf $(LC_LINKS_FILE) $(LINKS_FILE); \
	    else \
	        echo "NETWORK unspecified and no wheelhouse dir: using $(LC_URL_FILE)"; \
	        ln -sf $(LC_URL_FILE) $(LINKS_FILE); \
	    fi; \
	  else \
	    echo "NETWORK=$(NETWORK): using $(NO_LINKS_FILE)"; \
	    ln -sf $(NO_LINKS_FILE) $(LINKS_FILE); \
	  fi; \
	fi

# PEP8 is an optional check until we discuss which flake8 plugins we want to
# add (see SIBO-675).
pep8: export PATH=$(TEST_PATH)
pep8:
	@if test ! -d $(TEST_VENV); then \
	  echo "Making test virtual environment in $(TEST_VENV)"; \
	  make --no-print-directory install VENV=$(TEST_VENV); \
	else \
	  echo "You already have the test virtual environment $(TEST_VENV)"; \
	fi; \
	$(TEST_VENV)/bin/tox -e pep8

pylint: export PATH=$(PYLINT_PATH)
pylint:
	@echo "Creating $(PYLINT_VENV)"; \
	rm -rf $(PYLINT_VENV); \
	python -m virtualenv $(VENV_OPTIONS) $(PYLINT_VENV); \
	set -e; \
	$(PYLINT_VENV)/bin/pip install $(SINA_PIP_OPTIONS) --upgrade pip tox; \
	$(PYLINT_VENV)/bin/tox -e pylint

# Set up a clean test virtual environment before running tests.

# Recursively call make to ensure the work is done in the specified order
tests: export PATH=$(TEST_PATH)
tests: links
	@make --no-print-directory clean-tests-venv; \
	make --no-print-directory install VENV=$(TEST_VENV); \
	$(TEST_VENV)/bin/tox

# Recursively call make if it is necessary to create the test virtual environment.
test-jupyter: export PATH=$(TEST_PATH)
test-jupyter: links
	@if test ! -d $(TEST_VENV); then \
	  echo "Making the test virtual environment in $(TEST_VENV)"; \
	  make --no-print-directory install VENV=$(TEST_VENV); \
	else \
	  echo "You already have the test virtual environment $(TEST_VENV)"; \
	fi; \
	echo "Installing jupyter in $(TEST_VENV)"; \
	make --no-print-directory jupyter VENV=$(TEST_VENV); \
	echo "Running jupyter tests using $(TEST_VENV)"; \
	$(TEST_VENV)/bin/tox -e jupyter

# Recursively call make to ensure the work is done in the specified order
clean:
	@make --no-print-directory clean-notebooks; \
	make --no-print-directory clean-files

clean-files:  clean-tests
	@echo "Cleaning build files.."; \
	rm -rf build; \
	rm -f requirements/links.txt; \
	echo "Cleaning egg and $(VENV).."; \
	rm -rf sina.egg-info $(VENV); \
	echo "Cleaning python bytecode.."; \
	find . -name __pycache__ -o -name "*.pyc" -exec rm -rf {} \; >& /dev/null

# It is assumed any version/installation of Jupyter will properly remove outputs
# and that we do not want to have to [re-]install the virtual environment just
# to remove outputs from notebooks.
clean-notebooks:
	@echo "Removing any outputs from notebooks.."; \
	NOTEBOOKS=`find ../examples -name "*.ipynb" -print`; \
	JUPYTER_EXE=`which jupyter 2> /dev/null`; \
	NBCONVERT="--ClearOutputPreprocessor.enabled=True --log-level WARN --inplace"; \
	if test -f $(VENV)/bin/jupyter; then \
	  $(VENV)/bin/jupyter nbconvert $$NBCONVERT $$NOTEBOOKS; \
	elif test -n "$$JUPYTER_EXE" && test -f $$JUPYTER_EXE; then \
	  $$JUPYTER_EXE nbconvert $$NBCONVERT $$NOTEBOOKS; \
	else \
	  echo "Sina must be installed to clean notebooks.  Run 'make'."; \
	fi

# The tests target currently builds the docs so remove them too.
clean-tests: clean-tests-venv
	@echo "Cleaning files generated by test targets.."; \
	rm -rf .tox fake.sqlite nosetests*.xml* $(PYLINT_VENV); \
	echo "Cleaning tox-generated docs directories.."; \
	rm -rf docs/build docs/source/generated_docs; \
	echo "Cleaning example tests.."; \
	rm -rf tests/run_tests

clean-tests-venv:
	@echo "Removing generated test virtual environment.."; \
	rm -rf $(TEST_VENV)
