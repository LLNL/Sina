API Basics
==========

The Sina API is organized around Records and Relationships. A Record is
a piece of data conforming to the Mnoda JSON schema. It typically represents
something like a run, msub, or experiment. For examples, please see the
`Confluence page <https://lc.llnl.gov/confluence/display/SIBO/Mnoda/>`_.

While a Record can represent anything, there are specific types of Records
(such as Runs) that support special, additional queries. Any Record with a
:code:`type` equal to one of these types will be sorted somewhat differently
to allow for these special queries. To see what special types are available, please see the
`DAO documentation <generated_docs/sina.dao.html>`__


A Relationship is a triple of subject, predicate, and object, describing how
Records are related. For example, experiment_1 (subject) contains (predicate) run_24 (object).


The API itself makes use of DAOs to streamline accessing data independently
of the backend. There's one "factory" object per supported backend, and this
factory can be used to create the DAOs used to interact with Records, specific
Record types, and Relationships. For a simple demonstration::

  import sina.datastores.sql as sina_sql

  factory = sina_sql.DAOFactory(db_path="somefile.sqlite")
  record_dao = factory.createRecordDAO()
  all_sruns = record_dao.get_all_of_type("srun")

This would set all_sruns to a list of all the records contained in
:code:`somefile.sqlite` with :code:`"type": "srun"`. The DAOs and factories
provide a layer of abstraction that allows you to easily pass information
between supported backends::

  ...
  all_sruns = record_dao.get_all_of_type("srun")

  import sina.datastores.cass as sina_cass

  factory=sina_cass.DAOFactory(keyspace="sruns_only")
  record_dao = factory.createRecordDAO()
  record_dao.insert_many(all_sruns)

This would result in a keyspace :code:`sruns_only` that contains all the :code:`"type": "srun"`
records from :code:`somefile.sqlite` (assuming that :code:`sruns_only` was previously
empty). Of course, this can also be used for passing between backends of
the same type, such as creating a new sqlite file containing a subset of a
larger one, ex: all the records with :code:`"type": "run"` with a scalar "volume" greater
than 400. For examples of all the filters present, please see the
`DAO documentation <generated_docs/sina.dao.html>`__.


Inserting Records and Relationships Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can use Sina's API to insert objects into its databases directly, allowing
databases to grow as a script progresses, rather than writing to file and
ingesting all at once later on.

**SQLite does not support concurrent modification**, so you should never
perform parallel inserts with that backend!

Inserting objects is otherwise straightforward::

  ...
  from sina.model import Record, Run
  from sina.datastores.sql import sql

  factory = sql.DAOFactory(db_path='path_to_sqlite_file')

  my_record = Record(id="some_id",
                     type="some_type",
                     data=[{"name":"foo", "value": 12}],
                     files=[{"uri":"bar/baz.qux", "tags":["output"]}])

  my_other_record = Record("another_id", "some_type")
  record_dao = factory.createRecordDAO()
  record_dao.insert_many([my_record, my_other_record])

  my_run = Run(id="some_run_id",
               application="some_application",
               user="John Doe",
               data=[{"name":"oof", "value": 21}],
               files=[{"uri":"bar/baz.qux"}])

  run_dao = factory.createRunDAO()
  run_dao.insert(my_run)

Note that the (sub)type of Record is important--use the right constructor and
DAO or, if you won't know the type in advance, consider using the CLI
importer.


Filtering Based on Scalar Criteria
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Records can also be selected based on the scalars they contain. A Record "contains"
a scalar if the scalar is both named in its data list and assigned a numerical value.
For example, :code:`"data": {"volume":{"value": 1.2}}` describes a scalar.
:code:`"data": {"version":{"value":"1.2"}}` does not. Scalar criteria can be 
described
using either strings (see the `CLI query examples <cli_examples.html#query>`__)
or ScalarRanges, which are provided/documented in
`sina.utils <generated_docs/sina.utils.html>`__. In short, a ScalarRange represents
a basic mathematical interval, such as (0,1] or (,3), with two endpoints and
inclusive/exclusive designators for each. Infinite endpoints are indicated by
leaving the endpoint unspecified, or equivalently specifying it as None.::

  from sina.utils import ScalarRange

  # (,3), or x < 3
  # endpoints are exclusive by default
  less_than_three = ScalarRange(name='volume',
                                right_num=3)

  # (0,1], or x > 0 and x <= 1
  gt_0_lte_1 = ScalarRange(name='density',
                           left_num=0,
                           right_num=1,
                           right_inclusive=True)

  print(str(less_than_three) + ', ' + str(gt_0_lte_1))

ScalarRanges (or, again, properly-formatted strings) can be fed to Record DAOs
and related (Runs, etc) in order to filter based on the represented criteria.
When providing multiple criteria, only entries fulfilling all criteria will be
returned (boolean AND). If OR-like functionality is desired, it might be
emulated by loading :code:`id` s into sets, etc, then using the DAO's
:code:`get_many()` method. Filtering on the ScalarRanges above::

  ...

  matched_records = record_dao.get_given_scalars((less_than_three,
                                                  gt_0_lte_1))


Math-Based Queries
~~~~~~~~~~~~~~~~~~

Because of the potential complexity of queries based on equation criteria
(ex: (math.pi * r**2 * h)/3 >= 100), there is no one single DAO
method covering them. However, they're fairly straightforward to implement
using some additional Python logic. Example scripts have been provided in the
demo/apis folder (cass_equation.py and sql_equation.py) that will print a
list of all record ids found in some database that fulfill some equation-based
criterion.


Working with Records, Runs, Etc.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The objects returned by the DAOs can be used for further processing. Full
descriptions of object attributes are available in the
`model documentation <generated_docs/sina.model.html>`__, but Records and their
supported special types (runs, etc) all have, at minimum, three attributes:
:code:`id`, :code:`type`, and :code:`raw`. The :code:`id` is mostly used for
locating Records within a backend, and the type for sorting them, but as
Mnoda-compliant objects are JSON-based, a Record's raw provides easy access
to its contents::

  import sina.datastores.sql as sina_sql

  # First, we get all Records associated with a document of interest
  factory = sina_sql.DAOFactory(db_path="somefile.sqlite")
  record_dao = factory.createRecordDAO()
  doc_records = record_dao.get_given_document_uri("results/final_graph.%")

  import json

  # Then, we can extract specific fields from those records
  for record in doc_records:
    print(record.raw.get("graph_author"))

This snippet would find all Records in :code:`somefile.sqlite` that have some
file of interest mentioned in their file list. Note the use of :code:`%` as
a wildcard character--this would return Records associated with
"results/final_graph.png", "results/final_graph.gif", etc. Once we have our
list of Records, we have direct access to all information through the raw
attribute. Here, we use it to print a special toplevel field ("graph_author")
that the Mnoda schema wouldn't recognize. Of course, this can be used for much
more, such as editing Records and then inserting them into a new, "clean"
database, providing specific scalar sets to other applications, etc. For common
cases, such as accessing all files belonging to a Record, there are convenience
methods::

  print(record_dao.get_files("my_record_id"))

This snippet would print a list of files associated with the record whose
:code:`id="my_record_id"` For a full list of convenience methods,
please see the `DAO documentation <generated_docs/sina.dao.html>`__.
