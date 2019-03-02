"""Setup file for Sina. For project information, please see README."""
# !/usr/bin/env python

from setuptools import setup, find_packages

version = __import__('sina').get_version()

setup(name='sina',
      # namespace_packages=['sina_api','sina_cli','sina_model'],
      version=version,
      author='Daniel Laney, Jessica Semler, Joseph Eklund, Rebecca Haluska',
      packages=find_packages(),
      entry_points={
        'console_scripts': [
            'sina = sina.launcher:main'
        ]
      },
      extras_require={
        'jupyter': [
            'ipykernel<5;python_version<"3"',
            'ipykernel>=5;python_version>="3"',
            'pyzmq<18',
            'ipywidgets',
            'tabulate',
            'matplotlib'
        ]
      },
      install_requires=[
        'six',
        'sqlalchemy',
        'cassandra-driver',
        'deepdiff',
        'texttable'
      ]
      )
