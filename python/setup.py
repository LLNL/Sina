"""Setup file for Sina. For project information, please see README."""
# !/usr/bin/env python

from setuptools import setup, find_packages

VERSION = "1.9.5"

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
            'wcwidth<0.1.8',
            'ipython>=5,<6',  # ipython 6 drops support for Python 2
            'ipykernel<5',
            'matplotlib<3.0'
        ],
        'jupyter:python_version>="3"': [
            'nbconvert<=5.4.0',
            'ipython',
            'ipykernel>=5',
            'matplotlib',
        ],
        'jupyter': [
            'pyzmq<18',   # pyzmq 18.0 has bug on Python 3, use anything below
            'ipywidgets',
            'tabulate',
            'tornado<5.1'  # Tornado 5.1 gets stuck in a loop
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
        'ujson;python_version<"3.6" and platform_machine!="ppc64le"',
      ],
      license='MIT',
      classifiers=[
          'Development Status :: 5 - Production/Stable',


          # Pick your license as you wish (should match "license" above)
          'License :: OSI Approved :: MIT License',

          # Specify the Python versions you support here. In particular, ensure
          # that you indicate whether you support Python 2, Python 3 or both.
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7'
      ],
      )
