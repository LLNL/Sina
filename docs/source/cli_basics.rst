CLI Basics
==========

The Sina command line interface (CLI) is organized into three subcommands:
query, ingest, and export. To access these subcommands, make sure you're
currently in a virtual environment that has Sina and its dependencies
installed. You can access general help information using :code:`sina -h` or
subcommand-specific help with :code:`sina <subcommand_name> -h`. These commands are
largely backend-agnostic. While you may need to specify additional flags
(ex: providing a Cassandra keyspace if you do not have a default set), the
functionality between supported backends is otherwise identical.

Ingest
~~~~~~

The ingest subcommand is used for taking data from one source and inserting
it into one of Sina's supported backends. Currently, this means taking from a
JSON file and inserting it into either a sqlite file or a Cassandra instance.
To be ingested correctly, a JSON file needs to conform to the Mnoda schema.
For Mnoda examples and further information, see the
`Confluence page <https://lc.llnl.gov/confluence/display/SIBO/Mnoda/>`_.

A basic import would look like this::

  sina ingest --database somefile.sqlite to_import.json

This will import the contents of :code:`to_import.json` into a sqlite file called
:code:`somefile.sqlite`. If :code:`somefile.sqlite` does not already exist, it will be
created with all necessary schema information. In this case, because the
database has the file extension "sqlite" and the source has the extension
"json", Sina will infer that the information exists in a json format and should be stored
to a sqlite database. To specify a database and/or source type, include the
:code:`--database-type` and/or :code:`--source-type` flags::

  sina ingest --database somefile.sqlite --database-type sqlite to_import.json --source-type json

Cassandra databases currently cannot be inferred. They also have a third flag
associated with them, :code:`--keyspace`::

  sina ingest --database 127.0.0.1 --database-type cass --keyspace some_space to_import.json

Query
~~~~~

The query subcommand is used for querying data stored in a compatible backend.
Any supported backend following the Mnoda schema is queryable. **This includes
any backend created or updated using the ingest subcommand above.** Queries
are performed against various selectors (scalar data, associated documents, etc),
and are used to select entire records. For example::

  sina query --uri "foo.png" --database somefile.sqlite

This would return the raw form of any record found in :code:`somefile.sqlite` that's
associated with a document :code:`foo.png`. Including the :code:`--id` flag will return
only record ids for use in further processing. As another example::

  sina query --uri "foo.png" --scalar "xpos=0,volume=[3,5]" --id

This would return the ids of any records that are associated with :code:`foo.png`, have a scalar
named "xpos" with the value 0, and a scalar named "volume" whose value is between 3
and 5 (inclusive) from a default database defined elsewhere (when database flags
are not provided, a default will be used where supported).

This is only a small portion of the querying abilities available
through Sina; see the API section for more functionality. There *is* one more type
of query available through the CLI, raw queries, though these should be
used with caution, as they require knowledge of underlying schemas and
database technologies. An example raw query::

  sina query -r "Select value from scalar where name=xpos" --database somefile.sqlite

This returns the values of all scalars named "xpos". This query would work against SQL and
Cassandra backends.

Export
~~~~~~

The export subcommand is used for producing special subsets of data useful for analysis.
The only form of export currently supported is csv::

  sina export --database somefile.sqlite --target out.csv --scalars "volume,density" --records "rec_1,rec_2"

This would produce a csv file called :code:`out.csv` containing the values for
"density" and "volume" stored in :code:`somefile.sqlite` for records "rec_1" and "rec_2". That might look something like this::

  id,density,volume
  rec_1,12.2,400
  rec_2,14,299.5

  Note that scalar names will be organized alphabetically regardless of the order they're provided in.
