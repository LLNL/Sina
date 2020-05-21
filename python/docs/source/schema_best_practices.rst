.. _schema_best_practices:

Sina Schema Tips, Tricks, and Best Practices
============================================

This page covers recommendations and optional guidelines for working with
the Sina schema. Nothing here is mandatory, but following these
recommendations where possible may lead to easier querying, simplified
ingestion, clearer pedigree, etc.


Backend/Database
----------------

Sina can handle many types of Record within one database. The most important
consideration on deciding what to store together is how it'll be queried.
If, for example, you generate both msub info and runs, and you expect to need details
from the msubs when handling the runs, it makes sense to store them together.
To contrast that, if you're doing two experiments that happen to use the same
code, but never want to see results from the first experiment mixed in with
the second, it may be more appropriate to use a database apiece.


Document/File
-------------

The recommended naming convention is :code:`<somefilename>_sina.fileformat`, ex:
:code:`breakfast_simulations_sina.json`. This makes it easier to find sina files
later without breaking syntax highlighting by changing the file extension.

A full copy of each record is kept by Sina in order to preserve any
non-queryable data. If you're generating a document per record, you can
generally ingest and then dump the file, useful for saving on inodes.


Record
-------

If you don't have a preexisting convention for naming simulation runs/etc
uniquely, Unix timestamp, PID, and UUID in some combination can form a nice
base. You can also use a :code:`local_id` to let Sina name the records on ingestion
if you're not worried about human readability.


Relationship
------------

Use the grammatical "active voice" when assigning predicates.
A "passive voice" :code:`predicate` like "contained by", "corrected by", or
"launched by" reverses the normal direction of relations. The sample
Relationships are all in the preferred active voice:

  * task_1 contains run_22
  * task_1 contains run_23
  * overlay_12 corrects sample_14
  * msub_3 launches job_3


Data
----

Wherever possible, data names should be valid Python variable names. This
allows them to be used as keyword arguments for queries:

.. code-block:: python

    recs.data_query(my_legal_data_name=foo, density=bar, name3=baz)

Avoid names like :code:`my/var/here` or :code:`2d_res` if you want to use this
more convenient form.

Be aware that scalar lists are stored for efficient querying of continuous
values. If you're using a scalar list as more of an enum, where you'll want to
know things like "is 3 in this list", versus something like "is at least one
value in this list greater than 3", then consider casting the enum values to
strings.

For units, we recommend SI with / for division and ^ for exponentiation. This
format may have future support in Sina.


User Defined
------------

If you have a string datum that's many thousands of characters long, chances
are you're not querying on it--a very long string like that can cause
ingestion to fail if it's in the data section due to row size limitations, but
can be safely stored in User Defined. In general, though, consider keeping
bulk data on the filesystem.
