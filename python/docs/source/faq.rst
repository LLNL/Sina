Tips, FAQ, and Best Practices
=============================
.. faq:

This page covers misc. recommendations and optional guidelines for working with
the Sina schema. Nothing here is mandatory, but following these
recommendations where possible may lead to easier querying, simplified
ingestion, clearer pedigree, etc.

Tips and Best Practices
+++++++++++++++++++++++

Knowing when to use Sina
------------------------

Sina primarily exists to make physics simulation runs (which may include thousands of named data) easy to access and incorporate
into workflows, including workflows that are under development, without requiring familiarity with databases. Of course, it will
also work with other data sources, ex: wet lab experiments (as Sina's source-agnostic).

Sina may be useful if you're working on a code that already outputs Sina JSON (even without using the database side of things,
it should help with post-processing), or if you're working with many measurements at once, especially collaboratively and/or at
scales where individual inspection of runs becomes cumbersome. Sina's also handy if you want database-like performance without the
architectural lift. You may also want to use Sina if you want access to the interactive visualizations.


DataStores can be heterogenous
------------------------------

Sina can handle many types of Record within one datastore. The most important
consideration on deciding what to store together is how it'll be queried.
If, for example, you generate both msub info and data from application executions,
and you expect to need details from the msubs when handling the application data,
it makes sense to store them in the same datastore.

To contrast that, if you're doing two experiments that happen to use the same
code, but never want to see results from the first experiment mixed in with
the second, it may be more appropriate to use two datastores to avoid
"polluting" your results. You can always combine them later!


Common Sina file names: _sina.json
----------------------------------

The recommended naming convention is :code:`<somefilename>_sina.fileformat`, ex:
:code:`breakfast_simulations_sina.json`, or simply :code:`sina.json`. This makes
it easier to find sina files later without breaking syntax highlighting by
changing the file extension.

A full copy of each record is kept by Sina in order to preserve any
non-queryable data. If you're generating a file per record, you can
generally ingest and then delete the file, useful for saving on inodes.


Pythonic Record.data names are easier to query
----------------------------------------------

Wherever possible, data names should be valid Python variable names. This
allows them to be used as keyword arguments for queries:

.. code-block:: python

    recs.data_query(my_legal_data_name=foo, density=bar, name3=baz)

Avoid names like :code:`my/var/here` or :code:`2d_res` if you want to use this
more convenient form.


Use SI units when possible
--------------------------

If you're adding units to your data, we recommend SI with / for division and ^
for exponentiation. Unit enhancements/features added to Sina will focus
on this syntax.


Lists of scalars are treated as continuous
------------------------------------------

Scalar lists are stored for efficient querying of continuous values. If you're
using a scalar list as more of an enum, where you'll want to know things like
"is 3 in this list", versus something like "is at least one value in this list
greater than 3", then consider casting the enum values to strings.


Put long, unqueried strings in Record.user_defined
--------------------------------------------------

If you have a string datum that's many thousands of characters long, chances
are you're not querying on it--a very long string like that can cause
ingestion to fail if it's in the data section due to limitations in the backend
itself (ex: MySQL max row length), but can be safely stored in the :code:`user_defined`
field in a record. In general, though, consider keeping bulk data on the filesystem.


Frequently Asked Questions
++++++++++++++++++++++++++

Which backend should I use?
---------------------------

You'll generally want to use SQLite for smaller, more localized projects and MySQL as
you scale up and need concurrent writes (or many tens of thousands/millions of records).
Cassandra is a niche choice for large and specific use cases--reach out to
us directly if you think it's the backend for you!

SQLite:

 * Can live anywhere on the LC filesystem
 * Can freely have its permissions altered
 * Is trivial to stand up (the ingest commands will create a database for you)
 * Is ultimately just a file, with all the advantages that brings (give/take, copying, etc)
 * Has somewhat poorer query performance, becoming noticeable in the "millions of scalars" range
 * Faster serial inserts, no parallel inserts (or concurrent access in general)

MySQL:

 * Can be stood up quickly and easily on LC using LaunchIT
 * Is more powerful than SQLite and generally scales better
 * Allows for parallel access across hundreds of nodes (including safe parallel writes)
 * Functions very similarly to SQLite; you'll simply connect with a URL-like string instead of a filepath
 * Can have its permissions controlled by access to a config file
 * Does carry a networking cost (for very small workflows, SQLite may be faster)
 * Can be connected to across the CZ/RZ/etc. networks (ex: accessing a MySQL DB on Quartz from Catalyst), but does require connection to LC.

Cassandra:

 * Like MySQL, allows parallel access
 * In specific large-data cases, performs better than MySQL due to horizontal scaling--can handle tens of millions of scalars with sub-second query times
 * Can be accessed only on Cassandra hosts (Sonar, RZSonar, etc)
 * Permissions are handled by Sonar admins; Cassandra isn't typically exposed as an end-user capability
 * Requires some additional setup to create multiple keyspaces
 * Slower inserts
 * Is a radically different way of storing data; queries that may be performant on MySQL suffer much higher relative slowdown on Cassandra, without the tradeoffs being obvious to the user


What if I run into difficulties?
--------------------------------

Email us! Our most up-to-date contact info is listed in our toplevel README. Your questions help us improve this documentation!
