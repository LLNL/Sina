.. _mnoda:

Mnoda Schema
============

Overview
--------

The Mnoda schema is a generalized JSON format for representing experimental data.
It consists of two major components: Records, which are JSON objects representing
the components in an experiment (such as runs, msubs, and jobs) and Relationships,
which are JSON objects representing the relationships between Records. Each Mnoda
document consists of a single JSON object with Records and Relationships as
attributes, each being an array:

.. code-block:: javascript

    {
        "records": [],
        "relationships": []
    }


Records
-------

Every Record has, at minimum, an :code:`id` (or a :code:`local_id`) and a
:code:`type` (run, msub, etc). Records can also have :code:`data`, :code:`files`,
application metadata, arbitrary user-defined information, and more.
A minimal example of a Record:

.. code-block:: javascript

    {
        "type": "some_type",
        "id": "myRecordName"
    }

Note that :code:`id` can be replaced by :code:`local_id`. Use :code:`local_id`
if you're not sure that all your Records will be named uniquely (:code:`local_id` must
still be unique within a JSON document).

A more fleshed-out example, with field descriptions:

.. code-block:: javascript

    {
      // Category of the Record. Some types (ex: run) have additional support within Sina
      "type": "some_type",
      // Local ID of the Record. Must be unique within JSON document. Will be replaced by global id (or simply 'id') in db.
      "local_id": "obj1",
      // A list of files associated with the Record
      "files": [
          // Each file must have a uri, and can optionally specify a mimetype and tags.
          {"uri": "foo.png",
           "mimetype": "image/png",
           "tags": ["summary_image","output"]}
      ],
      // A list of data associated with the Record
      "data": [
          // Entries must have a name and value. Optionally, they can have tags and/or units.
          // We recommend standard SI units with / for division and ^ for exponentiation. This format may have future support in Sina.
          { "name": "max_density", "value": 3, "units": "kg/m^3" },
          { "name": "total_energy", "value": 12.2, "units": "MJ", "tags": ["output"]},
          { "name": "revision", "value": "12-4-11"},
          { "name": "solver", "value": "GMRES", "tags": ["input", "left_quad"]}
      ],
      "user_defined": {
          // Information that does not make sense as a data or file entry should be placed here.
          // None of this will be interpreted by Sina. Instead, it will simply
          // be saved as part of the Record.
      }
    }


Relationships
-------------

Every Relationship is a triple involving exactly three things: a :code:`subject`,
a :code:`predicate`, and an :code:`object`. Together, they form a statement about the relation between
:code:`subject` and :code:`object`. For example, in the phrase "Alice knows Bob", "Alice" is
the :code:`subject`, "knows" is the :code:`predicate`, and "Bob" is the :code:`object`. Other examples:

  * task_1 contains run_22
  * task_1 contains run_23
  * overlay_12 corrects sample_14
  * msub_3 launches job_3

To avoid confusion, try to use the grammatical active voice when assigning predicates.
A "passive voice" :code:`predicate` like "contained by", "corrected by", or
"launched by" may cause confusion, as it would reverse the normal direction of
relations. In the Mnoda schema, a Relationship always consists of exactly a :code:`subject`,
:code:`predicate`, and :code:`object`, where the :code:`subject` and :code:`object`
are each the :code:`id` of a Mnoda Record:

.. code-block:: javascript

    {
      "subject": "myRecordName",
      "predicate": "contains",
      "object": "myRunName"
    }

:code:`Subject` and :code:`object` can be switched to :code:`local_subject`
and :code:`local_object`, respectively, which indicates that the :code:`id` for that field:

  * Must correspond to a Record named using a :code:`local_id` elsewhere in the document
  * Will be replaced by whatever global :code:`id` is chosen to replace the :code:`local_id` naming that Record. For example:

.. code-block:: javascript

    "records": [
      {"type": "some_type", "id": "myRecordName"},
      {"type": "run", "local_id": "run1"}
    ],

    "relationships": [
      {"subject": "myRecordName", "predicate": "summarizes", "local_object": "run1"}
    ]

When ingested by Sina, the :code:`local_id` "run1" and :code:`local_object` "run1" will both be renamed
to the same globally unique ID in order to preserve the relationship.


Special Record Types
--------------------

Certain types of Records are expected to recur in data ingested by Sina.
These types have special field support in datastores created by Sina, and
may also support additional queries. What follows is a list of the
special Record types supported by Sina, and the fields that can be added
to a Mnoda Record to take advantage of that additional support. Note that **all
fields supported by generic Mnoda Records are supported by the special types**,
such as :code:`local_id`, :code:`data`, etc. Additionally, **all fields
supported by special types that aren't included in the generic Record are optional.**

Run
~~~

A Run is a Record that represents a single "run" of code within an application.
As such, Runs **require** an application identification, and optionally take
a user and version:

.. code-block:: javascript

    {
      "type": "run", // Type is case-sensitive
      "id": "myRunName",
      "application": "hydro",  // The application that produced the run
      "user": "John Doe",  // The user who ran the application
      "version": "1.5-dev2",  // The application's version
      "files": [
          {"uri": "run_image_1.png", "mimetype": "png"}
      ],
      "data": [
          { "name": "final_energy", "value": 4005.52, "units": "kJ"}
      ]
    }


Complete, Empty Document
------------------------

For convenience, here is an empty Mnoda document with all Relationship and generic
Record fields represented:

.. code-block:: javascript

    {
      "records": [
        {
          "type": "",
          "id": "",
          "files": [
              {"uri": "", "mimetype": "", "tags": []}
          ],
          "data": [
              { "name": "", "value": "", "units": "", "tags": []}
          ],
          "user_defined": {}
        },
        {
          "type": "",
          "local_id": "",
          "files": [
              {"uri": "", "mimetype": "", "tags": []}
          ],
          "data": [
              { "name": "", "value": "", "units": "", "tags": []}
          ],
          "user_defined": {}
        }
      ],

      "relationships": [
        {
          "subject": "",
          "predicate": "",
          "object": ""
        },
        {
          "local_subject": "",
          "predicate": "",
          "local_object": ""
        }
      ]
    }
