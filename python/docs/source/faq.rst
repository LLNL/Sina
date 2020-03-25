Frequently Asked Questions
==========================

Which backend should I use?
---------------------------

You'll generally want to use SQL for smaller, more localized projects.
Cassandra is useful when handling larger sets (millions of scalars or more).
SQL:

 * Can live anywhere on the LC filesystem
 * Can freely have its permissions altered
 * Is trivial to stand up (the ingest commands will create a database for you)
 * Is ultimately just a file, with all the advantages that brings (give/take, copying, etc)
 * Has somewhat poorer query performance, becoming noticeable in the "millions of scalars" range
 * Faster serial inserts, no parallel inserts (or concurrent access in general)

Cassandra:

 * Can be accessed only through Cassandra hosts (Sonar, RZSonar, etc)
 * Permissions are handled by Sonar admins
 * Requires some additional setup to create multiple keyspaces
 * Handles millions of entries while maintaining sub-second query times
 * Slower serial inserts due to network latency, but can be parallelized
 * Concurrent access is supported natively


What does a workflow using Sina look like?
------------------------------------------

This depends mainly on whether you run then insert or run *and* insert.

Run first, write JSON, insert when done
#######################################
You will need to modify your code to write Sina schema-compliant JSON. Use the Sina
CLI to ingest this JSON; it will handle setting up the backend (though you'll
need a pre-existing keyspace for Cassandra). That's it! Once ingestion completes,
you can begin querying your data.

Embed Sina in your workflow
###########################
See the API examples for specifics. Generally, you'll use Sina as one of the final
steps, when writing a completed run to file. You'll first need to create a
"factory" object (which will also set up the backend), then a DAO for whatever
object it is you're creating (ex: one RecordDAO and one RelationshipDAO).
Then, simply attach data to an object and use the relevant DAO's insert() method.
Each call to insert() will grow the data pool. A Cassandra database will be
available for querying while ingesting data; a SQL one should be handled with
care, as SQLite does not support concurrent access. You may wish to "checkpoint"
the SQLite database with a simple copy to make something safely queryable.


What's the performance like?
----------------------------

It depends on your data! In general, the more there is, the greater the potential
for "noticeable" slowdown. However, in testing against multi-million-scalar sets on Cassandra,
no Sina native query took longer than around half a second to complete, and the
majority of that time was spent "in transit" (one exception: mid-string matching
on Cassandra isn't supported natively, so partial URI searches are handled more
slowly in Python). For SQL, performance is more variable and largely depends on
the data.
