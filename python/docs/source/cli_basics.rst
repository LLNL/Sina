CLI Basics
==========

.. warning::
    Sina's command line interface (CLI) is undergoing a major overhaul. For
    now, it's recommended to use it mostly as a convenient, code-free way of
    ingesting data. Its querying and export capabilities are out of date, and due to
    the scale of the refactor, intermediate changes aren't added to the docs.
    For now, please consider this page likely out of date--if you run into
    any difficulties using the CLI, reach out to us!

The Sina command line interface (CLI) acts as a simplified and less feature-rich
companion to the API; its primary use is ingesting data, but it supports three
subcommands: query, ingest, and export. To access these subcommands, make sure you're
currently in a virtual environment that has Sina and its dependencies
installed. You can access general help information using :code:`sina -h` or
subcommand-specific help with :code:`sina <subcommand_name> -h`. These commands are
largely backend-agnostic. While you may need to specify additional flags, the
functionality between supported backends is otherwise identical.

Inspect
~~~~~~~

Sina json is usually output as a single line. If you'd like to inspect it at
the command line, python's inbuild json tool is invaluable::

    python -m json.tool some_sina.json prettyprinted_sina.json

This will separate everything onto its own line for easy manual inspection.


Ingest
~~~~~~

The ingest subcommand is used for taking data from one source and inserting
it into one of Sina's supported backends.

To be ingested correctly, a JSON file needs to conform to the Sina schema.
For Sina schema examples and further information, see the
`Confluence page <https://lc.llnl.gov/confluence/display/SIBO/Sina+JSON+Schema/>`_.

A basic import would look like this::

  sina ingest --database somefile.sqlite myfile_sina.json

This will import the contents of :code:`to_import.json` into a sqlite file called
:code:`somefile.sqlite`. If :code:`somefile.sqlite` does not already exist, it will be
created with all necessary schema information. In this case, because the
database has the file extension "sqlite" and the source has the extension
"json", Sina will infer that the information exists in a json format and should be stored
to a sqlite database. To specify a database and/or source type, include the
:code:`--database-type` and/or :code:`--source-type` flags::

  sina ingest --database somefile.sqlite --database-type sqlite myfile_sina.json --source-type json

If ingesting many files at once, the usual command line tricks will work (with a more formal solution
coming with the CLI refresh)::

  sina ingest -d somefile.sqlite `find ../run-myrun*/*/myfile_sina.json | tr '\n' ',' | sed 's/,$//' | sed -z '$ s/\n$//'`


Query
~~~~~

The query subcommand is used for querying data stored in a compatible backend.
Any supported backend following the Sina schema is queryable. **This includes
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

This returns the values of all scalars named "xpos".

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
