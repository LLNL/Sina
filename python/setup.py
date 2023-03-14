"""Setup file for Sina. For project information, please see README."""
# !/usr/bin/env python

from setuptools import setup, find_packages

VERSION = "1.13.0"

setup(name='llnl-sina',
      version=VERSION,
      author='Siboka Team',
      author_email='siboka@llnl.gov',
      packages=find_packages(),
      description='Simulation INsight and Analysis',
      long_description=open('README.md').read(),
      entry_points={
        'console_scripts': [
            'sina = sina.cli.driver:main'
        ]
      },
      extras_require={
        'cassandra': [
            'cassandra-driver',
        ],
        'jupyter': [
            # More recent nbconverts cause jinja "missing python.tpl" errors.
            'nbconvert<=5.4.0',
            # and nbconvert in general isn't compatible with recent mistunes.
            'mistune<2',
            # Older nbconvert requires older Tornado.
            'tornado<5.1',
            'ipython<8',  # Required for Python 3.7 (LC machine version)
            'ipykernel>=5',
            'ipywidgets',
            # Newer numpys (1.22, 1.23) seem to have an issue with up-to-date setuptools
            'numpy<1.22',
            'matplotlib',
            'tabulate'
        ],
        'cli_tools': [
            'deepdiff',
            'texttable'
        ],
        'mysql': [
            'mysql-connector-python',
        ]
      },
      install_requires=[
        'six',
        'sqlalchemy',
        'enum34;python_version<"3.4"',
        'orjson;python_version>="3.6" and platform_machine!="ppc64le"',
        'ujson;python_version>="3.6" and platform_machine=="ppc64le"',
        'ujson<4;python_version<"3.6" and platform_machine!="ppc64le"',
        'freetype-py;platform_system=="Darwin"',
      ],
      license='MIT',
      classifiers=[
          'Development Status :: 5 - Production/Stable',


          # Pick your license as you wish (should match "license" above)
          'License :: OSI Approved :: MIT License',

          # Specify the Python versions you support here.
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7'
      ],
      )
