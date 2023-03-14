.. _sina_schema:

Sina JSON Schema
================

.. note:: Most users won't interact with Sina's JSON schema directly. This is provided as a
    reference for anyone designing a workflow where direct interaction with the
    JSON is required. Most post-processing can be done through Sina's Python API, which
    is more user-friendly; visit `the post-processing tutorial <examples/post_processing.html>`__
    for more info.


Overview
--------

The Sina schema is a generalized JSON format for representing experimental data.
It consists of two types of JSON objects: Records, which represent the components in
an experiment (such as runs, msubs, and jobs) and Relationships, which represent
the relationships between Records. This page outlines the basics of the schema.

These concepts are, of course, deeply linked to Sina's `API Concepts <api_basics.html>`__.
Familiarity with those should help here!

Each Sina document consists of a single JSON object with arrays for Records and
Relationships:

.. code-block:: javascript

    {
        "records": [],
        "relationships": []
    }


Records
-------

Every Record has, at minimum, an :code:`id` and a :code:`type` (run, msub,
etc). Records can also have :code:`data`, :code:`curve_sets`, :code:`files`,
application metadata, arbitrary user-defined information, and more.
A minimal example of a Record:

.. code-block:: javascript

    {
        "type": "some_type",
        "id": "myRecordName"
    }

Note that :code:`id` can be replaced by :code:`local_id`. Use :code:`local_id`
if you're not sure that all your Records will be named uniquely (:code:`local_id` must
still be unique within a JSON document). This is especially useful when outputting
a Sina Record from a code, since it avoids needing to come up with a UUID/etc. within
the integration.

A more fleshed-out example, with field descriptions:

.. warning:: Comments are not part of the JSON standard, meaning this example is not
    valid JSON. See the end of this page for a JSON "skeleton" or one of the
    example datasets (described in the :ref:`readme`) for valid Sina JSON.

.. code-block:: javascript

    {
      // Category of the Record.
      "type": "some_type",
      // Local ID of the Record. Must be unique within JSON document. Will be
      // replaced by global id (or simply 'id') in db.
      "local_id": "obj1",
      // A dictionary of files associated with the Record
      "files": {
          // Each file can optionally specify a mimetype and tags.
          "foo.png": {"mimetype": "image/png", "tags": ["summary_image","output"]}
      },
      // A dictionary of data associated with the Record
      "data": {
          // Entries must have a value. Optionally, they can have tags and/or units.
          "initial_angle": {"value": 30},
          "max_density": { "value": 3, "units": "kg/m^3" },
          "total_energy": { "value": 12.2, "units": "MJ", "tags": ["output"]},
          // Data can be strings, scalars, lists of strings, or lists of scalars
          "revision": { "value": "12-4-11", "tags": ["pedigree"]},
          "presets": { "value": ["quickstart", "glass"]}
      },
      // Sets of curves associated with the Record (essentially a special case of data)
      "curve_sets": {
          // Each set of curves needs a name
          "timeplot_1": {
              // Each set has independent(s) and dependent(s)
              "independent": {
                  // Individual curves take the same format as lists of scalars in "data"
                  "time": {"value": [0, 1, 2]}},
              "dependent": {
                  "mass": {"value": [12, 11, 8], "tags": ["physics"]},
                  "volume": {"value": [10, 14, 22.2], "units": "m^3"}}
          }
      },
      // Data that comes from any libraries associated with a Record. This allows data
      // from nested libraries to be grouped, as well as avoiding name collisions.
      "library_data": {
          "outer_lib": {
              // libraries can have curve_sets and data sections just like the greater Record.
              // They cannot have files or user_defined; those still belong to the greater Record.
              "data": {"total_energy": {"value": 2.2}},
              // libraries can be nested to whatever depth is required
              "library_data": {
                  "inner_lib": {
                      "data": {"total_energy": {"value": 0.2}}
                  }
              }
          }
      },
      // A dictionary of information that does not make sense as a data or file entry
      "user_defined": {
          // None of this will be interpreted by Sina. Instead, it will simply
          // be saved as part of the Record.
          "display_string": "0x477265617420636174636821"
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

In the Sina schema, a Relationship always consists of exactly a :code:`subject`,
:code:`predicate`, and :code:`object`, where the :code:`subject` and :code:`object`
are each the :code:`id` of a Record:

.. code-block:: javascript

    {
      "subject": "myTaskId",
      "predicate": "contains",
      "object": "myRunId"
    }

:code:`subject` and :code:`object` can be switched to :code:`local_subject`
and :code:`local_object`, respectively, which indicates that the :code:`id` for that field:

  * Must correspond to a Record named using a :code:`local_id` elsewhere in the document
  * Will be replaced by whatever global :code:`id` is chosen to replace the :code:`local_id` naming that Record. For example:

.. code-block:: javascript

    "records": [
      {"type": "some_type", "id": "myRecordId"},
      {"type": "run", "local_id": "run1"}
    ],

    "relationships": [
      {"subject": "myRecordId", "predicate": "summarizes", "local_object": "run1"}
    ]

When ingested by Sina, the :code:`local_id` "run1" and :code:`local_object` "run1" will both be renamed
to the same globally unique ID in order to preserve the relationship.


Complete, Empty Document
------------------------

For convenience, below is a Sina document template with Relationship and generic
Record fields represented. Note that :code:`datum_name` should be replaced by the
actual name of the datum (such as "density" or "max_volume").

.. code-block:: javascript

    {
      "records": [
        {
          "type": "",
          "id": "",
          "files": {
              "uri": {"mimetype": "", "tags": []}
          },
          "data": {
              "datum_name": {"value": "", "units": "", "tags": []}
          },
          "user_defined": {}
        },
        {
          "type": "",
          "local_id": "",
          "files": {
              "uri": {"mimetype": "", "tags": []}
          },
          "data": {
              "datum_name": {"value": [], "units": "", "tags": []}
          },
          "curve_sets": {
              "curve_set_name": {
                  "independent": {
                      "independent_name": {"value": [], "units": "", "tags": []}
                  },
                  "dependent": {
                      "dependent_name": {"value": [], "units": "", "tags": []}
                  }
              }
          }
          "library_data": {
              "outer_lib": {
                  "data": {"datum_name": {"value": [], "units": "", "tags": []}}
              }
          },
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
