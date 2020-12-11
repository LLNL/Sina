.. _api-basics:

API Basics
==========
.. note
    This page documents the major concepts of Sina's API; for a hands-on
    tutorial, see the Jupyter notebooks detailed in the README.

Major API Concepts
~~~~~~~~~~~~~~~~~~
The Sina API is organized around Records and Relationships.
A Record typically represents something like a run, msub, or experiment, while a
Relationship represents a link between Records, such as which msub submitted which
job. Records and Relationships are both valid JSON objects, and are documented
further in the :ref:`sina_schema`. Sina's API allows users to store, query, and retrieve
these objects from several backends, including SQL and Cassandra, using
backend-agnostic Python.


Special Record Types
####################
While a Record can represent anything, there are special types of Records,
such as Runs, that support additional queries. Any Record with a :code:`type`
equal to the name of a special type will be sorted somewhat differently
to allow for these queries. To see what types are available, please see the
`Model documentation <generated_docs/sina.model.html>`__

Basic Access
############
You start by creating a DataStore, which will connect to your backend of
choice and expose many functions for interacting with the Records and
Relationships stored within. For a simple demonstration::

  from sina.datastore import create_datastore

  ds = create_datastore(db_path="somefile.sqlite")
  all_sruns = ds.records.find_with_type("srun")

This would set :code:`all_sruns` to a list of all the records contained in
:code:`somefile.sqlite` with :code:`"type": "srun"`. You can easily pass data
between supported backends::

  ...

  cass_ds=create_datastore(keyspace="sruns_only")
  cass_ds.records.insert(all_sruns)

This would result in a keyspace (essentially a Cassandra database)
:code:`sruns_only` that contains all the :code:`"type": "srun"` records found
in :code:`somefile.sqlite` (assuming that :code:`sruns_only` was previously
empty). Of course, this can also be used for passing between backends of
the same type, such as creating a new sqlite file containing a subset of a
larger one, ex: all the records with :code:`"type": "run"` with a scalar "volume" greater
than 400.

The remainder of this page will detail the basics of using DataStores to
interact with Records and Relationships. It only covers a subset; for
documentation of all the methods available, please see the
`DataStore documentation <generated_docs/sina.datastore.html>`__.


Filtering Records Based on Their Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Basic Filtration
################
Records have a :code:`data` field that holds the experimental data they're
associated with. This can be inputs, outputs, start times, etc. This data
is queryable, and can be used to find Records fitting criteria. For example, let's
say we're interested in all Records with a :code:`final_volume` of 310 and with
a :code:`quadrant` of "NW"::

  records = ds.records.find_with_data(final_volume=310, quadrant="NW")

This will find all the records record_dao knows about (so those in
:code:`somefile.sqlite`) that fit our specifications.

IMPORTANT NOTE: when providing multiple criteria, only entries fulfilling all criteria
will be returned (boolean AND). If OR-like functionality is desired, see the next
section, :ref:`Ids_Only`.

Filtering on a Range
####################
Perhaps we don't want a :code:`final_volume` of 310 exactly, but rather one
between 200 and 311. DataRanges allow us to specify this. They follow the Python
convention of min-inclusive, max-exclusive, but this can be altered::

  from sina.utils import DataRange

  # data_query is aliased to get_given_data, they're interchangeable
  records = ds.records.find_with_data(final_volume=DataRange(200, 311),
                                   final_acceleration=DataRange(min=12,
                                                                max=20,
                                                                min_inclusive=False,
                                                                max_inclusive=True),
                                   schema=DataRange(max="bb_12"),
                                   quadrant="NW")

Now we've found the ids of all Records that have a :code:`final_volume` >= 200
and < 310, a :code:`final_acceleration` > 12 and <= 20, a :code:`schema`
that comes before "bb_12" alphabetically, and a :code:`quadrant` = "NW". For an
interactive demo, see examples/fukushima/fukushima_subsecting_data.ipynb.

Filtering on Lists
##################
Because there are several possible ways a list might match some criteria,
the syntax for performing the query is slightly different. Let's say we want all
Records fulfilling a criterion for :code:`velocity`, a timeseries. In this case,
we want a velocity that's never gone above 50::

  from sina.utils import all_in

  records = ds.records.find_with_data(velocity=all_in(DataRange(max=50)))

A slightly different set of queries applies to string list data. Let's say
we want all Records where "strength_1" or "strength_2" were included in
:code:`active_packages`::

  from sina.utils import has_any

  records = ds.records.find_with_data(active_packages=has_any("strength_1", "strength_2"))

This is the general syntax for list queries in Sina. Supported queries are:

+------------------------------------------------------------------------------------------------+
| Scalar List Queries                                                                            |
+============+===================================================================================+
| all_in     | Takes a DataRange. All values in this datum must be within the DataRange.         |
+------------+-----------------------------------------------------------------------------------+
| any_in     | Takes a DataRange. At least one value in this datum must be within the DataRange. |
+------------+-----------------------------------------------------------------------------------+

+--------------------------------------------------------------------------------------------+
| String List Queries                                                                        |
+============+===============================================================================+
| has_all    | Takes one or more strings. All strings must be present in this datum.         |
+------------+-------------------------------------------------------------------------------+
| has_any    | Takes one or more strings. At least one string must be present in this datum. |
+------------+-------------------------------------------------------------------------------+


See examples/basic_usage.ipynb for list queries in use.

.. _Ids_Only:

Combining Filters using "IDs Only" Logic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filtering methods (such as find_with_type and find_with_file_uri) take an
optional argument, :code:`ids_only`. If passed as :code:`True`, they'll return
only the ids of Records that fulfill their criteria, rather than the entire
Record. This is faster than assembling the entire Record object(s), and is also
the recommended way of combining queries or implementing more complex logic::

  ...

  type_filter = ds.records.find_with_type("msubs", ids_only=True)
  file_filter = ds.records.find_with_file_uri("mock_msub_out.txt", ids_only=True)

  # This will print ids of all records which are msubs or are associated with
  # a file "mock_msub_out.txt", **but not both** (exclusive OR)
  xor_recs = set(type_filter).symmetric_difference(file_filter)
  print(xor_recs)


Getting Specific Data for Many Records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You may want, for example, to get the :code:`final_speed` and :code:`shape` of
each Record matching the above criteria. Rather than building Record objects for
all matches and then selecting only the data you want, you can use
get_data_for_records() to find specific data entries across a list of Records::

 ...

 desired_data = ["final_speed", "shape"]

 data = ds.records.get_data(id_list = xor_recs, data_list = desired_data)

 for id in data:
     msg = "For record {}: final speed {}, shape {}"
     print(msg.format(id,
                      data[id]["final_speed"]["value"],
                      data[id]["shape"]["value"]))

NOTE: Some machines enforce a limit on the number of variables per SQL
statement, generally around 999. If you run into issues selecting data for
large numbers of Records, consider using the Cassandra backend, or simply split
your get_data_for_records call to use smaller chunks of Records.


Working with Records, Runs, Etc. as Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Given the id of a Record, you can get the entire Record as a Python object using::

   # get() takes one or more ids
   record = ds.records.get("my_record_id")
   records_list = ds.records.get(["my_first_record", "my_second_record"])

Full descriptions are available in
`model documentation <generated_docs/sina.model.html>`__, but
as a quick overview, Records have, at minimum, an :code:`id` and :code:`type`.
These and additional optional fields (such as the Record's data and files) can be
accessed as object attributes::

 ...
 run_spam = ds.records.get(id="spam")

 print(run.type)
 print(run.data["egg_count"]["value"])
 print(run.data["egg_count"]["units"])
 run.data["egg_count"]["value"] = 12
 del run.data["bad_eggs"]
 for file in run.files:
     print(file.get("mimetype"))

You can also assign additional fields not officially supported by the Sina
schema and not "seen" by the DAOs. While this isn't normally recommended (in
case we implement something with the same name), you may find it useful,
particularly if you have a very specific name in mind::

 run["nonqueried_data_for_bob"]["spam_flavor"] = "concerning"

That said, consider whether the :code:`user_defined` field might be a better fit,
as it's guaranteed to be safe, as well as omitted from the DAO queries::

 run.user_defined["spam_flavor"] = "concerning"


Inserting Records and Relationships Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use Sina's API to insert objects into its databases directly, allowing
databases to grow as a script progresses, rather than writing to file and
ingesting all at once later on.

**SQLite does not support concurrent modification**, so you should never
perform unlocked parallel inserts with that backend!

Inserting objects is otherwise straightforward::

  ...
  from sina.model import Record, Run
  from sina.datastore import create_datastore

  datastore = create_datastore(db_path='path_to_sqlite_file')
  recs = datastore.records

  start_val = 12
  my_record = Record(id="some_id",
                     type="some_type",
                     data={"start_val": {"value": start_val}},
                     files=[{"uri": "bar/baz.qux", "tags": ["output"]}])

  my_record.data["return_time"] = {"value": my_func(start_val),
                                   "units": "ms"}

  my_other_record = Record("another_id", "some_type")

  # Like get(), insert() takes one or more ids.
  recs.insert([my_record, my_other_record])


Deleting Records
~~~~~~~~~~~~~~~~

To delete a Record entirely from one of Sina's backends::

  ...
  my_record_to_delete = Record("fodder", "fodder_type")
  recs.insert(my_record_to_delete)

  # This would print 1
  print(len(list(recs.find_with_type("fodder_type"))))

  # Like get() and insert(), delete() takes one or more ids.
  recs.delete("fodder")

  # This would print 0
  print(len(list(recs.find_with_type("fodder_type"))))

Be careful, as the deletion will include every Relationship the Record is
mentioned in, all the scalar data associated with that Record, etc.
