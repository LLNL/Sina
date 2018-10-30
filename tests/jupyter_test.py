"""
Tests for example Jupyter Notebooks.

Sources:
1) Parameterized unit test generation follows the post by Guy at:
    https://stackoverflow.com/questions/32899/\
        how-do-you-generate-dynamic-parametrized-unit-tests-in-python
2) Execution tests are a variant of the function found at:
    https://blog.thedataincubator.com/2016/06/testing-jupyter-notebooks
"""
import collections
import nbformat
import os
import subprocess
import tempfile
import unittest

# Path to the examples directory containing Jupyter notebooks to be tested.
#
# Use the directory for this file as the basis until the need for another
# mechanism arises.
EXAMPLES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             "../examples"))

# Python magics template filename
MAGICS_TEMPLATE = "pythonmagics.tpl"


def _build_pep8_output(result):
    """
    Build the PEP8 output based on flake8 results.

    :param result: output from flake8
    :returns list of flake8 output lines by error
    """
    # Aggregate individual errors by error
    _dict = collections.defaultdict(list)
    for line in result.split("\n"):
        if line:
            parts = line.replace("(", ":").split(":")

            # Restore the colon in a 'missing whitespace' error if removed
            error = parts[3].strip()
            key = "{}:'".format(error) if error.endswith("after '") else error

            _dict[key].append("{} ({})".format(parts[1], parts[2]))

    # Build the output as one error per entry
    return ["{}: {}".format(k, ", ".join(_dict[k])) for k in
            sorted(_dict.keys())]


def _execute_notebook(path):
    """
    Execute a notebook and collect any output errors.

    :param path: fully qualified path to the notebook
    :returns (parsed notebook object, execution errors)
    """
    notebook = None
    errors = []
    try:
        with tempfile.NamedTemporaryFile(suffix=".ipynb") as fout:
            args = ["jupyter", "nbconvert", "--to", "notebook", "--execute",
                    "--ExecutePreprocessor.timeout=-1", "--log-level=ERROR",
                    "--output", fout.name, path]
            subprocess.check_call(args)

            fout.seek(0)
            notebook = nbformat.read(fout, nbformat.current_nbformat)

            # Does the notebook conform to the current format schema?
            nbformat.validate(notebook)

            errors = [output for cell in notebook.cells if "outputs" in cell
                      for output in cell["outputs"] if
                      output.output_type == "error"]

    except subprocess.CalledProcessError:
        raise RuntimeError("Failed to convert or run {}. Refer to associated "
                           "error output above.". format(path))

    return notebook, errors


def _find_notebooks():
    """
    Find all of the notebooks in the repository examples directory.

    :returns pathname list
    """
    try:
        files = []
        child = subprocess.Popen("find {} -name '*.ipynb' -print".
                                 format(EXAMPLES_PATH), shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        (_stdoutdata, _stderrdata) = child.communicate()

        # Skip checkpoint notebooks in generated subdirectories
        files = sorted([filename for filename in _stdoutdata.split("\n")[:-1]
                        if filename.find(".ipynb_checkpoints") < 0])

    except Exception as exc:
        print("ERROR: {}: {}".format(exc.__class__.__name__, str(exc)))
        files = []

    return files


def _is_compliant_notebook(path):
    """
    Check the notebook style against PEP8 requirements.

    :param path: fully qualified path to the notebook
    :returns True if the notebook is compliant, False otherwise
    """
    dirname, basename = os.path.split(path)

    # Jupyter nbconvert automatically appends ".py" to the path PLUS we need
    # an easy way to tell .gitignore to ignore the generated files and the
    # Makefile to remove them.  So base the generated file name on the full
    # notebook name.
    testbase = os.path.join(dirname, "test_{}".format(basename))
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


def _write_magics_template():
    """
    Write the python template to skip cell magic statements.
    """
    with open(MAGICS_TEMPLATE, "w") as outfile:
        outfile.write("""\
{% extends 'python.tpl'%}
# Magics removal source: https://github.com/ipython/ipython/issues/3707/
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
                nb, errors = _execute_notebook(filename)
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
            _write_magics_template()
            for filename in files:
                test_name = "test_%s" % \
                    os.path.splitext(os.path.basename(filename))[0]
                _dict["{}_exec".format(test_name)] = gen_test_exec(filename)

                # TODO: SIBO-481: Uncomment to enable flake8 test generation
                # _dict["{}_style".format(test_name)] = gen_test_style(filename)

        return type.__new__(meta, name, bases, _dict)


class TestNotebooks(unittest.TestCase):
    """Class for performing basic tests of example Jupyter Notebooks."""
    __metaclass__ = TestJupyterNotebooks

    @classmethod
    def tearDownClass(cls):
        if os.path.isfile(MAGICS_TEMPLATE):
            os.remove(MAGICS_TEMPLATE)
