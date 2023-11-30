"""Setup file for Sina. For project information, please see README."""
# !/usr/bin/env python

from setuptools import setup, find_packages

VERSION = "1.15.0"

setup(name='llnl-sina',
      version=VERSION,
      author='Siboka Team',
      author_email='weave-support@llnl.gov',
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
              'jupyter-client',
              'ipython<8.13',  # 8.13 seems to require Python 3.9 but not limit itself to >= it.
              'ipykernel',
              'ipywidgets',
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
          'sqlalchemy',  # API changes, to be investigated/updated for
          'sqlalchemy<2;python_version<"3"',
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
