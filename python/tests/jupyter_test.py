"""
Tests for example Jupyter Notebooks, which include:
- executing them on the default or, if relevant, a test database; and
- performing flake8 checks on them (once re-enabled).

Sources:
1) Parameterized unit test generation follows the post by Guy at:
    https://stackoverflow.com/questions/32899/\
        how-do-you-generate-dynamic-parametrized-unit-tests-in-python
2) Execution tests are a variant of the function found at:
    https://blog.thedataincubator.com/2016/06/testing-jupyter-notebooks
3) Execution tests via the API at:
    https://nbconvert.readthedocs.io/en/latest/execute_api.html
"""
import collections
import io
from nbconvert.preprocessors import ExecutePreprocessor
import nbformat
import os
import shutil
from six import with_metaclass
import subprocess
import unittest

# Assumed root directory for examples, etc.
#
# Use the directory for this file as the basis until the need for another
# mechanism arises.
DIR_ROOT = os.path.dirname(__file__)

# Path to the directory for running notebooks
RUN_PATH = os.path.abspath(os.path.join(DIR_ROOT, "..", "tests",
                                        "run_tests", "notebooks"))

# Path to the examples directory containing Jupyter notebooks to be tested.
EXAMPLES_PATH = os.path.abspath(os.path.join(DIR_ROOT, "../..", "examples"))

# Python magics template filename
MAGICS_TEMPLATE = os.path.abspath(os.path.join(RUN_PATH, "pythonmagics.tpl"))

# Jupyter Notebook test kernel name
SINA_TEST_KERNEL = os.getenv("SINA_TEST_KERNEL")
SINA_KERNEL = "sina" if SINA_TEST_KERNEL is None else SINA_TEST_KERNEL


def _build_pep8_output(result):
    """
    Build the PEP8 output based on flake8 results.

    Flake8 output results conform to the following format:

      <filename>:<line number>:<column number>: <issue code> <issue desc>

    with some issues providing more details in the description within
    parentheses.

    :param result: output from flake8
    :returns: list of flake8 output lines by error
    """
    # Aggregate individual errors by error
    _dict = collections.defaultdict(list)
    for line in result.split("\n"):
        if line:
            # Preserve only the code and brief description for each issue to
            # facilitate aggregating the results.  For example,
            #
            #    E501 line too long (178 > 79 characters) -> E501 line too long
            #    E303 too many blank lines (4) -> E303 too many blank lines
            parts = line.replace("(", ":").split(":")
            line_num, col_num, base_issue = parts[1:4]

            # Strip the whitespace around the base <issue code> <description>.
            #
            # Also restore the missing colon, stripped above, if the issue
            # was 'missing whitespace' surrounding a colon.
            issue = base_issue.strip()
            key = "{}:'".format(issue) if issue.endswith("after '") else issue

            _dict[key].append("{} ({})".format(line_num, col_num))

    # Build the output as one issue per entry
    return ["{}: {}".format(k, ", ".join(_dict[k])) for k in
            sorted(_dict.keys())]


def _execute_notebook(path):
    """
    Execute a notebook and collect any output errors.

    Using the API to help reduce the amount of output and better associate
    errors with the kernel and notebook.

    :param path: fully qualified path to the notebook
    :returns: list of execution errors
    """
    errors = []

    try:
        notebook = _read_notebook(path)
    except Exception as _exception:
        return ['{}: {}: Reading {}: {}'.format(_exception.__class__.__name__,
                SINA_KERNEL, path, str(_exception))]

    try:
        # Does the notebook conform to the current format schema?
        nbformat.validate(notebook)
    except Exception as _exception:
        errors.append('{}: {}: Validating {}: {}'.
                      format(_exception.__class__.__name__, SINA_KERNEL, path,
                             str(_exception)))

    try:
        exec_preprocessor = ExecutePreprocessor(timeout=-1,
                                                kernel_name=SINA_KERNEL)
        exec_preprocessor.preprocess(notebook, {'metadata': {'path': '.'}})
    except Exception as _exception:
        errors.append('{}: {}: Running {}: {}'.
                      format(_exception.__class__.__name__, SINA_KERNEL, path,
                             str(_exception)))
    finally:
        _, basename = os.path.split(path)
        execname = os.path.join(RUN_PATH, "execute_{}".format(basename))
        try:
            with io.open(execname, mode='wt', encoding='utf-8') as fout:
                nbformat.write(notebook, fout)
        except Exception as _exception:
            errors.append('{}: {}: Writing {}: {}'.
                          format(_exception.__class__.__name__, SINA_KERNEL,
                                 execname, str(_exception)))
            return errors

        if os.path.isfile(execname):
            try:
                notebook = _read_notebook(execname)
                for cell in notebook.cells:
                    if "outputs" in cell:
                        for output in cell["outputs"]:
                            if output.output_type == "error":
                                errors.append('{}: {}: {}'.
                                              format(SINA_TEST_KERNEL,
                                                     output.ename,
                                                     output.evalue))
            except Exception as _exception:
                errors.append('{}: {}: Checking for errors in {}: {}'.
                              format(_exception.__class__.__name__, SINA_KERNEL,
                                     execname, str(_exception)))
            if len(errors) <= 0:
                os.remove(execname)

    return errors


def _find_notebooks():
    """
    Find all of the notebooks in the repository examples directory.

    :returns: pathname list
    """
    child = subprocess.Popen("find {} -name '*.ipynb' -print".
                             format(EXAMPLES_PATH), shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True)
    (_stdoutdata, _) = child.communicate()

    # Skip checkpoint notebooks in generated subdirectories
    return sorted([filename for filename in _stdoutdata.split("\n")[:-1]
                  if filename.find(".ipynb_checkpoints") < 0])


def _is_compliant_notebook(path):
    """
    Check the notebook style against PEP8 requirements.

    :param path: fully qualified path to the notebook
    :returns: True if the notebook is compliant, False otherwise
    """
    _, basename = os.path.split(path)

    # Jupyter nbconvert automatically appends ".py" to the path PLUS we need
    # an easy way to tell .gitignore to ignore the generated files and the
    # Makefile to remove them.  So base the generated file name on the full
    # notebook name.
    testbase = os.path.join(RUN_PATH, "test_{}".format(basename))
    testname = "{}.py".format(testbase)

    try:
        args = ["jupyter", "nbconvert", "--to", "python", "--log-level=ERROR",
                "--PythonExporter.exclude_input_prompt=True",
                "--PythonExporter.exclude_markdown=True",
                "--template={}".format(MAGICS_TEMPLATE), "--output", testbase,
                path]
        subprocess.check_call(args)

    except subprocess.CalledProcessError:
        if os.path.isfile(testname):
            os.remove(testname)
        raise RuntimeError("Failed to create {}".format(testname))

    try:
        #
        # Ignore the following error(s):
        # - E303 too many blank lines (always a problem with the notebooks)
        # - E501 line too long (problem with cell magic cells)
        # - W391 blank line at end of file (apparently result of conversion)
        #
        # and set the max length to be the same we use for our tests.
        args = ["flake8", "--ignore=E303,E501,W391", testname, "; exit 0"]
        result = subprocess.check_output(" ".join(args), shell=True,
                                         stderr=subprocess.STDOUT)

        if os.path.isfile(testname):
            if result:
                with open(testname, "a") as outfile:
                    outfile.write("\n#################\n")
                    outfile.write("# Flake8 Output #\n")
                    outfile.write("#################\n")
                    for line in _build_pep8_output(result):
                        outfile.write("#  {}\n".format(line))
            else:
                os.remove(testname)

    except subprocess.CalledProcessError:
        raise RuntimeError("Failed to perform flake8 checks on {}".
                           format(path))

    return len(result) <= 0


def _read_notebook(path):
    """
    Read the noteook from the specified file path.

    :param path: fully qualified path to the notebook
    :returns: the notebook
    """
    try:
        with open(path) as fout:
            notebook = nbformat.read(fout, nbformat.current_nbformat)
    except Exception as _exception:
        _exception.args += ("reading {}".format(path),)
        raise

    return notebook


def _write_magics_template():
    """
    Write the python template to skip cell magic statements.

    This template is used to tell nbconvert to comment out get_ipython calls
    it adds for cell magic statements (e.g., calling bash).  This is necessary
    so flake8 does not generate an F821 error (undefined name), for the call.
    """
    with open(MAGICS_TEMPLATE, "w") as outfile:
        outfile.write("""\
{% extends 'python.tpl'%}
## Source @shett044: https://github.com/ipython/ipython/issues/3707/
## Comment magic statement
{% block codecell %}
{{ super().replace('get_ipython','# get_ipython')
                   if "get_ipython" in super() else super() }}
{% endblock codecell %}
""")


class TestJupyterNotebooks(type):
    """Jupyter Notebook metaclass."""

    def __new__(meta, name, bases, _dict):
        """
        Class constructor (i.e., allocates memory).

        :param meta: meta class
        :param name: unittest class name
        :param bases: base class(es) (i.e., unittest.case.TestCase)
        :param _dict: class attributes dictionary
        """
        def gen_test_exec(filename):
            """
            Notebook execution test constructor.

            :param filename: fully qualifed notebook path
            """
            def test_exec(self):
                errors = _execute_notebook(filename)
                # Indent output of each error (if any)
                self.assertEqual(errors, [], "Execution errors detect in "
                                 "{}:\n  {}".format(filename, "\n  ".
                                                    join(errors)))
            return test_exec

        def gen_test_style(filename):
            """
            Notebook PEP8 style check test constructor.

            :param filename: fully qualifed notebook path
            """
            def test_style(self):
                self.assertTrue(_is_compliant_notebook(filename), "Style "
                                "errors detected in {}. Refer to associated "
                                "test script for details.".format(filename))
            return test_style

        files = _find_notebooks()
        if len(files) > 0:
            for filename in files:
                test_name = "test_%s" % \
                    os.path.splitext(os.path.basename(filename))[0]
                _dict["{}_exec".format(test_name)] = gen_test_exec(filename)
                _dict["{}_style".format(test_name)] = gen_test_style(filename)

        return type.__new__(meta, name, bases, _dict)


class TestNotebooks(with_metaclass(TestJupyterNotebooks, unittest.TestCase)):
    """Class for performing basic tests of example Jupyter Notebooks."""

    @classmethod
    def setUpClass(cls):
        """Set up notebook tests."""
        if os.path.isdir(RUN_PATH):
            shutil.rmtree(RUN_PATH, True)

        os.makedirs(RUN_PATH)
        _write_magics_template()

    @classmethod
    def tearDownClass(cls):
        """Tear down notebook tests."""
        if os.path.isfile(MAGICS_TEMPLATE):
            os.remove(MAGICS_TEMPLATE)
