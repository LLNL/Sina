Overview
========

Sina allows codes to store, query, and visualize their data through an easy-to-use Python
API. Data that fits its recognized schema can be ingested into one or more supported backends;
Sina's API is independent of backend and gives users the benefits of a database without
requiring knowledge of one, allowing queries to be expressed in pure Python. Visualizations
are also provided through Python--see the python/examples folder for demo Jupyter notebooks.  

Sina is intended especially for use with run metadata, allowing users to easily and efficiently
find simulation runs that match some criteria.

Sina's code comes in two parts. The "cpp" component is an API for use in C++ codes that allows
them to write data in Sina's recognized format. The remainder of Sina is found in
the "python" directory, and includes all the functionality for handling and
ingesting data, visualizing it through Jupyter, etc.

Please see the READMEs included in those folders for more information on each
component.


Getting Started
===============
Sina's two parts each have their own setup information. See the
[Python README](python/README.md) or [C++ README](cpp/README.md)
depending on your needs.


Getting Involved
================
Sina is still growing, and users' questions, comments, and contributions help
guide its evolution. We welcome involvement.


Contact Info
------------
You can reach our team at siboka@llnl.gov.

Contributing
------------
Contributions should be submitted as a pull request pointing to the develop branch,
and must pass Sina's CI process; to run the same checks locally, use `make test` for
whichever component you're working on.

Contributions must be made under the same license as Sina (see the bottom of this file).


Release and License
===================

Sina is distributed under the terms of the MIT license; new contributions must be
made under this license.

SPDX-License-Identifier: MIT

LLNL-CODE-769899
