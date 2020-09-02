"""Setup file for Sina. For project information, please see README."""
# !/usr/bin/env python

from setuptools import setup, find_packages

VERSION = __import__('sina').get_version()

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
        'jupyter:python_version<"3"': [
            'ipython>=5,<6',  # ipython 6 drops support for Python 2
            'ipykernel<5',
            'wcwidth<0.1.8',
            'tornado<5.1'
        ],
        'jupyter:python_version>="3"': [
            'ipython',
            'ipykernel>=5',
            'tornado<5.1'
        ],
        'jupyter': [
            'pyzmq<18',   # pyzmq 18.0 has bug on Python 3, use anything below
            'ipywidgets',
            'tabulate',
            'matplotlib'
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
        'enum34;python_version<"3.4"'
      ]
      )
