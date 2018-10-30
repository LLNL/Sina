.. _api-basics:

API Basics
==========

The Sina API is organized around Records and Relationships. A Record is
a piece of data conforming to the Mnoda JSON schema. It typically represents
something like a run, msub, or experiment (for examples, please see
the :ref:`mnoda`). Relationships (also documented in the schema) represent
the links between Records, such as which msub submitted which job.

While a Record can represent anything, there are special types of Records,
such as runs, that support additional queries. Any Record with a :code:`type`
equal to the name of a special type will be sorted somewhat differently
to allow for these queries. To see what types are available, please see the
`Model documentation <generated_docs/sina.model.html>`__

The API itself makes use of DAOs to streamline accessing data independently
of the backend. There's one "factory" object per supported backend, and this
factory can be used to create the DAOs used to interact with Records, special
Record types, and Relationships. For a simple demonstration::

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

This would result in a keyspace :code:`sruns_only` that contains all the :code:`"type": "srun"`
records from :code:`somefile.sqlite` (assuming that :code:`sruns_only` was previously
empty). Of course, this can also be used for passing between backends of
the same type, such as creating a new sqlite file containing a subset of a
larger one, ex: all the records with :code:`"type": "run"` with a scalar "volume" greater
than 400.

The remainder of this page will detail the basics of using these DAOs to
interact with Records and Relationships. It only covers a subset; for
documentation of all the methods available to each DAO, please see the
`DAO documentation <generated_docs/sina.dao.html>`__.


Filtering Records Based on Scalar Criteria
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Records can also be selected based on the scalars they contain. A Record "contains"
a scalar if the scalar is both named in its data dictionary and assigned a numerical value.
For example, :code:`"data": {"volume":{"value": 1.2}}` describes a scalar.
:code:`"data": {"version":{"value":"1.2"}}` does not. Scalar criteria can be
described
using either strings (see the `CLI query examples <cli_examples.html#query>`__)
or ScalarRanges, which are provided/documented in
`sina.utils <generated_docs/sina.utils.html>`__. In short, a ScalarRange represents
an interval, such as (0,1] or (,3), with two endpoints and
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
returned (boolean AND). If OR-like functionality is desired, see the next
section. Filtering on the ScalarRanges above::

  ...

  matched_records = record_dao.get_given_scalars((less_than_three,
                                                  gt_0_lte_1))


Combining Filters using "IDs Only" Logic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filtering methods (such as get_all_of_type, get_given_scalar, etc) take an
optional argument, :code:`ids_only`. If passed as :code:`True`, they'll return
only the ids of Records that fulfill their criteria, rather than the entire
Record. This is faster than assembling the entire Record object(s), and is also
the recommended way of combining queries or implementing more complex logic::

  ...

  ids_volume_filter = record_dao.get_given_scalar(less_than_three,
                                                  ids_only=True)
  ids_density_filter = record_dao.get_given_scalars(gt_0_lte_1,
                                                    ids_only=True)

  # This will print ids of all records whose volume is less than three or
  # whose density is in the range (0, 1], *but not both* (XOR)
  xor_recs = set(ids_volume_filter).symmetric_difference(ids_density_filter)
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


Math-Based Queries
~~~~~~~~~~~~~~~~~~

Because of the potential complexity of queries based on equation criteria
(ex: (math.pi * r**2 * h)/3 >= 100), there is no one single DAO
method covering them. However, they're fairly straightforward to implement
using some additional Python logic. Example scripts have been provided in the
demo/apis folder (cass_equation.py and sql_equation.py) that will print a
list of all record ids found in some database that fulfill some equation-based
criterion.


Working with Records, Runs, Etc. as Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The methods detailed above return Records; full descriptions are available in
the `model documentation <generated_docs/sina.model.html>`__, but
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
