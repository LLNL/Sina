# The following environment variables can be used to change the behavior of
# building the virtual environment:
#
#   PYTHON           = Specify non-default python (e.g., python3)
#   SINA_PIP_OPTIONS = Additional options to pip (e.g., '--no-index')
#   VENV             = Name of the Sina virtual environment (default 'venv')
#   VENV_OPTIONS     = Additional options when the venv is created (e.g.,
#                      '--system-site-packages' to inherit system packages

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

# Determine whether being run for Python 2 or Python 3 since it affects virtual
# virtual environment commands.
PYTHON?=python
export PYTHON
PYVERSION=$(shell $(PYTHON) -c 'import sys; print(sys.version_info[0])')
ifeq ($(PYVERSION),2)
  PYTHON_VENV_OPTION:=virtualenv
  # Setuptools dropped Py2 support in 45
  SETUPTOOLS_INSTALL="setuptools<45.0.0"
else
  PYTHON_VENV_OPTION:=venv
  SETUPTOOLS_INSTALL=--upgrade setuptools
endif

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
.PHONY: cli_tools
.PHONY: clean
.PHONY: clean-files
.PHONY: clean-notebooks
.PHONY: clean-tests
.PHONY: clean-tests-venv
.PHONY: docs
.PHONY: flake8
.PHONY: install
.PHONY: jupyter
.PHONY: pep8
.PHONY: pylint
.PHONY: tests
.PHONY: test-cassandra
.PHONY: test-cli_tools
.PHONY: test-core
.PHONY: test-jupyter
.PHONY: wheel

install: $(LINKS_FILE)
	@if test ! -d $(VENV); then \
	  echo "Making virtual environment in $(VENV)"; \
	  $(PYTHON) -m $(PYTHON_VENV_OPTION) $(VENV_OPTIONS) $(VENV); \
	  set -e; \
	else \
	  echo "You already have the virtual environment $(VENV)"; \
	fi; \
	if test -d $(VENV); then \
	    $(VENV)/bin/pip install $(SINA_PIP_OPTIONS) --upgrade pip; \
	    $(VENV)/bin/pip install $(SINA_PIP_OPTIONS) $(SETUPTOOLS_INSTALL); \
	    $(VENV)/bin/pip install $(SINA_PIP_OPTIONS) -r requirements/development.txt; \
	    echo $(PR_ACT); \
	else \
	  echo "Failed to create the virtual environment $(VENV)"; \
	fi

all: clean docs tests

# Add cassandra dependencies to an existing virtual environment, where one is
# created through a recursive call to make if it does not exist.
cassandra: $(LINKS_FILE)
	@if test ! -d $(VENV); then \
	  echo "Making the test virtual environment in $(VENV)"; \
	  make --no-print-directory install VENV=$(VENV); \
	else \
	  echo "You already have the test virtual environment $(VENV)"; \
	fi; \
	echo "Installing cassandra in $(VENV)"; \
	$(VENV)/bin/pip install $(SINA_PIP_OPTIONS) -r requirements/cassandra.txt

# Add mysql dependencies to an existing virtual environment, where one is
# created through a recursive call to make if it does not exist.
mysql: $(LINKS_FILE)
	@if test ! -d $(VENV); then \
	  echo "Making the test virtual environment in $(VENV)"; \
	  make --no-print-directory install VENV=$(VENV); \
	else \
	  echo "You already have the test virtual environment $(VENV)"; \
	fi; \
	echo "Installing mysql in $(VENV)"; \
	$(VENV)/bin/pip install $(SINA_PIP_OPTIONS) -r requirements/mysql.txt

# Add command line tool dependencies to an existing virtual environment, where
# one is created through a recursive call to make if it does not exist.
#
# Note: Use of underscore in the target name ensures deploy.sh can readily
# process options.
cli_tools: $(LINKS_FILE)
	@if test ! -d $(VENV); then \
	  echo "Installing sina core in $(VENV)"; \
	  make --no-print-directory install VENV=$(VENV); \
	else \
	  echo "You already have the virtual environment $(VENV)"; \
	fi; \
	echo "Installing Sina's commandline tool dependencies in $(VENV)"; \
	$(VENV)/bin/pip install $(PIP_OPTIONS) -r requirements/cli_tools.txt

docs: install
	@$(VENV)/bin/tox -e docs

# Add flake8 dependencies to an existing test virtual environment, where
# one is created through a recursive call to make if it does not exist.
flake8: export PATH=$(TEST_PATH)
flake8: $(LINKS_FILE)
	@if test ! -d $(TEST_VENV); then \
	  echo "Making the test virtual environment in $(TEST_VENV)"; \
	  make --no-print-directory install VENV=$(TEST_VENV); \
	else \
	  echo "You already have the test virtual environment $(TEST_VENV)"; \
	fi; \
	echo "Running flake8 tests using $(TEST_VENV)"; \
	$(TEST_VENV)/bin/tox -e flake8

# Add jupyter dependencies to an existing virtual environment, where one is
# created through a recursive call to make if it does not exist.
jupyter: $(LINKS_FILE)
	@if test ! -d $(VENV); then \
	  echo "Installing sina core in $(VENV)"; \
	  make --no-print-directory install VENV=$(VENV); \
	else \
	  echo "You already have the virtual environment $(VENV)"; \
	fi; \
	echo "Installing jupyter in $(VENV)"; \
	$(VENV)/bin/pip install $(SINA_PIP_OPTIONS) -r requirements/jupyter.txt
	$(VENV)/bin/jupyter nbextension install widgetsnbextension --user --py
	$(VENV)/bin/jupyter nbextension enable widgetsnbextension --user --py

# Ensure the appropriate requirement links are established.  This is important
# for building and testing purposes.
$(LINKS_FILE):
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

# Add pep8 dependencies to an existing test virtual environment, where one is
# created through a recursive call to make if it does not exist.
#
# PEP8 is an optional check until we discuss which flake8 plugins we want to
# add (see SIBO-675).
pep8: export PATH=$(TEST_PATH)
pep8: $(LINKS_FILE)
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
	$(PYTHON) -m $(PYTHON_VENV_OPTION) $(VENV_OPTIONS) $(PYLINT_VENV); \
	set -e; \
	$(PYLINT_VENV)/bin/pip install $(SINA_PIP_OPTIONS) --upgrade pip tox; \
	$(PYLINT_VENV)/bin/tox -e pylint

# Set up a clean test virtual environment before running tests by making
# recursive calls to make to ensure the work is done in the specified order.
tests: export PATH=$(TEST_PATH)
tests: $(LINKS_FILE)
	@make --no-print-directory clean-tests-venv; \
	make --no-print-directory install VENV=$(TEST_VENV); \
	$(TEST_VENV)/bin/tox

# Run cassandra tests, which depend on a suitably configured test virtual
# environment.
test-cassandra: export PATH=$(TEST_PATH)
test-cassandra:
	@if test ! -d $(TEST_VENV); then \
	  echo "The test virtual environment $(TEST_VENV) is required.  Be sure to add Cassandra if it is to be included."; \
	else \
	  echo "Running cassandra tests using $(TEST_VENV)"; \
	  $(TEST_VENV)/bin/tox -e cassandra; \
	fi

# Run mysql tests, which depend on a suitably configured test virtual
# environment.
test-mysql: export PATH=$(TEST_PATH)
test-mysql:
	@if test ! -d $(TEST_VENV); then \
	  echo "The test virtual environment $(TEST_VENV) is required.  Be sure to add mysql if it is to be included."; \
	else \
	  echo "Running mysql tests using $(TEST_VENV)"; \
	  $(TEST_VENV)/bin/tox -e mysql; \
	fi

# Run command line tools tests, which depend on a suitably configured test
# virtual environment.
#
# Note: Use of underscore in the target name ensures deploy.sh can readily
# process options.
test-cli_tools: export PATH=$(TEST_PATH)
test-cli_tools: $(LINKS_FILE)
	@if test ! -d $(TEST_VENV); then \
	  echo "The test virtual environment $(TEST_VENV) is required.  Be sure to add cli_tools if they are to be included."; \
	else \
	  echo "Running cli_tools tests $(TEST_VENV)"; \
          $(TEST_VENV)/bin/tox -e cli_tools; \
	fi

# Run the core Sina tests, which depend on the basic virtual environment so
# it can be created if necessary using a recursive call to make.
test-core: export PATH=$(TEST_PATH)
test-core: $(LINKS_FILE)
	@if test ! -d $(TEST_VENV); then \
          echo "Making the test virtual environment in $(TEST_VENV)"; \
          make --no-print-directory install VENV=$(TEST_VENV); \
	fi; \
	echo "Running core tests $(TEST_VENV)"; \
        $(TEST_VENV)/bin/tox -e core


# Run jupyter tests, which depend on a suitably configured test virtual
# environment.
test-jupyter: export PATH=$(TEST_PATH)
test-jupyter: $(LINKS_FILE)
	@if test ! -d $(TEST_VENV); then \
	  echo "The test virtual environment $(TEST_VENV) is required.  Be sure to add jupyter if it is to be included."; \
	else \
	  echo "Running jupyter tests using $(TEST_VENV)"; \
	  $(TEST_VENV)/bin/tox -e jupyter; \
	fi

# Create the Sina wheel
wheel:
	@echo "Creating the sina wheel"; \
	rm -rf ./wheel dist; \
	$(PYTHON) -m $(PYTHON_VENV_OPTION) $(VENV_OPTIONS) ./wheel; \
	wheel/bin/pip install $(SINA_PIP_OPTIONS) --upgrade pip wheel; \
	wheel/bin/pip install $(SINA_PIP_OPTIONS) $(SETUPTOOLS_INSTALL); \
	wheel/bin/python setup.py bdist_wheel --universal; \
	wheel/bin/python setup.py sdist --formats=gztar; \
	rm -rf ./wheel

# Publish Sina to pypi. For this to work, you have to have an account on
# pypi.org. For the latest instructions, please see
# https://packaging.python.org/tutorials/packaging-projects/#uploading-the-distribution-archives
publish:
	@echo "Publishing Sina to Pypi"
	$(PYTHON) -m $(PYTHON_VENV_OPTION) $(VENV_OPTIONS) distvenv
	distvenv/bin/pip install $(SINA_PIP_OPTIONS) --upgrade pip
	distvenv/bin/pip install $(SINA_PIP_OPTIONS) $(SETUPTOOLS_INSTALL) twine
	distvenv/bin/twine upload dist/*

# Set up a clean branch, recursively calling make to clean up notebooks and
# files as needed.
clean:
	@make --no-print-directory clean-notebooks; \
	make --no-print-directory clean-tests; \
	make --no-print-directory clean-build

clean-docs:
	@echo "Cleaning tox-generated docs directories.."; \
	rm -rf docs/build docs/source/generated_docs

clean-build:
	@echo "Cleaning build and distribution files.."; \
	rm -rf build dist wheel; \
	rm -f $(LINKS_FILE); \
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
	  echo "Sina must be installed with Jupyter to clean notebooks."; \
	fi

# The tests target currently builds the docs so remove them too.
clean-tests: clean-docs clean-tests-venv
	@echo "Cleaning files generated by test targets.."; \
	rm -rf .tox fake.sqlite nosetests*.xml* $(PYLINT_VENV); \
	echo "Cleaning example tests.."; \
	rm -rf tests/run_tests

clean-tests-venv:
	@echo "Removing generated test virtual environment.."; \
	rm -rf $(TEST_VENV)
