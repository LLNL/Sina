.. _api-basics:

API Basics
==========

Major API Concepts
~~~~~~~~~~~~~~~~~~
The Sina API is organized around Records and Relationships.
A Record typically represents something like a run, msub, or experiment, while a
Relationship represents a link between Records, such as which msub submitted which
job. Records and Relationships are both valid JSON objects, and are documented
further in the :ref:`mnoda`. Sina's API allows users to store, query, and retrieve
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
The API makes use of "DAOs" (Data Access Objects) to streamline accessing data
independently of the backend. There's one "factory" object per supported backend,
and this factory can be used to create the DAOs used to interact with Records,
special Record types, and Relationships. For a simple demonstration::

  import sina.datastores.sql as sina_sql

  factory = sina_sql.DAOFactory(db_path="somefile.sqlite")
  record_dao = factory.createRecordDAO()
  all_sruns = record_dao.get_all_of_type("srun")

This would set :code:`all_sruns` to a list of all the records contained in
:code:`somefile.sqlite` with :code:`"type": "srun"`. The DAOs and factories
provide a layer of abstraction that allows you to easily pass information
between supported backends::

  ...

  import sina.datastores.cass as sina_cass

  factory=sina_cass.DAOFactory(keyspace="sruns_only")
  record_dao = factory.createRecordDAO()
  record_dao.insert_many(all_sruns)

This would result in a keyspace (essentially a Cassandra database)
:code:`sruns_only` that contains all the :code:`"type": "srun"` records found
in :code:`somefile.sqlite` (assuming that :code:`sruns_only` was previously
empty). Of course, this can also be used for passing between backends of
the same type, such as creating a new sqlite file containing a subset of a
larger one, ex: all the records with :code:`"type": "run"` with a scalar "volume" greater
than 400.

The remainder of this page will detail the basics of using these DAOs to
interact with Records and Relationships. It only covers a subset; for
documentation of all the methods available to each DAO, please see the
`DAO documentation <generated_docs/sina.dao.html>`__.


Filtering Records Based on Their Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Records have a :code:`data` field that holds the experimental data they're
associated with. This can be inputs, outputs, start times, etc. This data
is queryable, and can be used to find Records fitting criteria. For example, let's
say we're interested in all Records with a :code:`final_volume` of 310 and with
a :code:`quadrant` of "NW"::

  records = record_dao.get_given_data(final_volume=310, quadrant="NW")

This will find all the records record_dao knows about (so those in
:code:`somefile.sqlite`) that fit our specifications. Of course, sometimes we're
interested in data within a range::

  from sina.utils import DataRange

  # data_query is aliased to get_given_data, they're interchangeable
  records = record_dao.data_query(final_volume=DataRange(200,310),
                                  final_acceleration=DataRange(max=20,
                                                               min=12,
                                                               min_inclusive=False,
                                                               max_inclusive=True),
                                  schema=DataRange(max="bb_12"),
                                  quadrant="NW")

Now we've found the ids of all Records that have a :code:`final_volume` >= 200
and < 310, a :code:`final_acceleration` > 12 and <= 20, a :code:`schema`
that comes before "bb_12" alphabetically, and a :code:`quadrant` = "NW". For an
interactive demo, see examples/fukushima/fukushima_subsecting_data.ipynb.

NOTE: when providing multiple criteria, only entries fulfilling all criteria
will be returned (boolean AND). If OR-like functionality is desired, see the next
section.


Combining Filters using "IDs Only" Logic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filtering methods (such as get_all_of_type and get_given_document_uri) take an
optional argument, :code:`ids_only`. If passed as :code:`True`, they'll return
only the ids of Records that fulfill their criteria, rather than the entire
Record. This is faster than assembling the entire Record object(s), and is also
the recommended way of combining queries or implementing more complex logic::

  ...

  type_filter = record_dao.get_all_of_type("msubs", ids_only=True)
  file_filter = record_dao.get_given_document_uri("mock_msub_out.txt", ids_only=True)

  # This will print ids of all records which are msubs or are associated with
  # a file "mock_msub_out.txt", **but not both** (exclusive OR)
  xor_recs = set(type_filter).symmetric_difference(file_filter)
  print(xor_recs)


Getting Specific Data for Many Scalars
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You may want, for example, to get the final_speed and shape of each
Record matching the above criteria. Rather than building Record objects for
all matches and then selecting only the data you want, you can use
get_data_for_records() to find specific data entries across a list of Records::

 ...

 desired_data = ["final_speed", "shape"]

 data = record_dao.get_data_for_records(id_list = xor_recs,
                                        data_list = desired_data)

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

   record = record_dao.get("my_record_id")
   records_list = record_dao.get_many(["my_first_record", "my_second_record"])

Full descriptions are available in
`model documentation <generated_docs/sina.model.html>`__, but
as a quick overview, Records and their subtypes (Runs, etc.) all
have, at minimum, an :code:`id` and :code:`type`. These and
additional optional fields (such as the Record's data and files) can be
accessed as object attributes::

 ...
 run_spam = record_dao.get(id="spam")

 print(run.type)
 print(run.data["egg_count"]["value"])
 print(run.data["egg_count"]["units"])
 run.data["egg_count"]["value"] = 12
 del run.data["bad_eggs"]
 for file in run.files:
     print(file.get("mimetype"))

You can also assign additional fields not officially supported by the Mnoda
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
  from sina.datastores.sql import sql

  factory = sql.DAOFactory(db_path='path_to_sqlite_file')

  start_val = 12
  my_record = Record(id="some_id",
                     type="some_type",
                     data={"start_val": {"value": start_val}},
                     files=[{"uri": "bar/baz.qux", "tags": ["output"]}])

  my_record.data["return_time"] = {"value": my_func(start_val),
                                   "units": "ms"}

  my_other_record = Record("another_id", "some_type")
  record_dao = factory.createRecordDAO()
  record_dao.insert_many([my_record, my_other_record])

  my_run = Run(id="some_run_id",
               application="some_application",
               user="John Doe",
               data={"oof": {"value": 21}},
               files=[{"uri":"bar/baz.qux"}])

  run_dao = factory.createRunDAO()
  run_dao.insert(my_run)

Note that the (sub)type of Record is important--use the right constructor and
DAO or, if you won't know the type in advance, consider using the CLI
importer.


Deleting Records
~~~~~~~~~~~~~~~~

To delete a Record entirely from one of Sina's backends::

  ...
  my_record_to_delete = Record("fodder", "fodder_type")
  record_dao.insert(my_record_to_delete)

  # This would print 1
  print(len(list(record_dao.get_all_of_type("fodder_type"))))

  record_dao.delete("fodder")

  # This would print 0
  print(len(list(record_dao.get_all_of_type("fodder_type"))))

Be careful, as the deletion will include every Relationship the Record is
mentioned in, all the scalar data associated with that Record, etc. There is
also a mass deletion method that takes a list of ids to delete,
:code:`delete_many()`.
