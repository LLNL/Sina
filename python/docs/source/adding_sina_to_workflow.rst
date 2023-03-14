.. _adding_sina_to_workflow:

Adding Sina to Your Project
===========================

Depending on how your project's organized and what data it deals with, adding Sina
can be a quick and painless process. If not, this page should at least make it
an easier lift. Note that this page assumes some familiarity with Sina basics, so check out
the `tutorials <examples/index.html>`__ and/or `API Concepts <api_basics.html>`__.

Considering the Basics
----------------------

Answering a few questions up front may be helpful in deciding how to begin:

- How many different forms of output are you dealing with? A single .csv of results? A directory with dozens of files?
- For the files containing that data, what's the organization like? Is it unstructured ASCII? Logs? JSON?
- Which of those files contain things used to categorize results? That is, if you have a thousand simulation runs, which data would let you choose the runs you're interested in? That's the sort of data you'll want in Sina (physics output scalars are a common example)
- Of that, what should constitute one Record? Consider what data belongs together as a single grouping of inputs and outputs. A simulation run, a well in a plate, and a set of measurements at one coordinate point are all natural candidates for a single Record.
- Do you want to have multiple types of Record? For example, you might want to track :code:`msub` s and :code:`run` s. Or say you're doing oceanography data, taking measurements at a series of points--you might want :code:`point_measure` s and :code:`trip` s.
- What additional [meta]data, if any, would you like to add in? Timestamps are a common example.
- Which Relationships, if any, would you like to track? It can be helpful to think under which circumstances you'd need to find one Record given another (for example, you might have both :code:`deck` s and :code:`run` s that use a deck, and you may want to find the latter's info from the former, or vice versa)


The simplest case for Sina (which is not uncommon) is that you're already using a code that outputs
Sina JSON. In that case, all you need to do is run the ingest command and start using the visualizer! If not,
you'll have to decide how to line up how you (and/or your users) think about the data with how Sina accesses it.
The aforementioned `API Concepts <api_basics.html>`__ doc covers the ideas, but we can explore some of the
mechanical realities by walking through the process of designing a Record.


Designing Your Record
---------------------

If you're not using a code that outputs a Sina Record, you'll have to design one yourself!
Making a test Record (even/especially psuedocode) is perhaps the fastest way to figure out what should go in one. Make sure
you check out `basic usage <examples/basic_usage.html>`__ (and further examples in the `WEAVE repo <https://lc.llnl.gov/gitlab/weave/weave_demos>`__, if you're an LC user) to see example Records! While there's
more info available in the `schema documentation <sina_schema.html>`__, a few general tips for the sort of info you'll want to think about:

- A Record's :code:`id` can be anything, especially for a test record, but must be unique (within a datastore at least). Timestamp+UUID is common.
- For a :code:`type`, when in doubt, call it something like "<name_of_code>_run", "msub", or "ensemble". You just want to pick something that's easily remembered and helps you tell one thing from another--if you only ever intend to put one thing in there, it's not too important, but :code:`type` becomes critical when mixing types of Records within a database (for example, simulation runs and msubs)
- A Record's :code:`data` should contain anything that you'd want to use to tell one record from another. Inputs, outputs, metadata like when it was run (you may want to get all runs in a date range)--basically, imagine you have a thousand simulations and you want to find the "interesting" ones. You may not know every dimension of "interesting" up front, but you can likely think of at least one or two, phrased as "I want all Records where ____ is ____" (I want all Records where the etot is above 3000, I want all Records where the total_volume is never above 40, I want all Records where the laser package is on...)
- Its :code:`file` s should contain any filepath you want associated with the Record. Run directories, meshes, silo files, output images, etc.
- If you have a lot of timeseries (or cycleseries, etc), :code:`curve_set` s allow you to associate dependents and independents. Useful for anything you expect to be visualizing!
- :code:`library_data` is a fairly advanced field, mostly meant for use within codes. Still, if your Record is incorporating data from multiple sources, check out the model documentation to learn how to use library_data to essentially "namespace" parts of your Record, allowing you to have things like an overall :code:`runtime`, a :code:`runtime` for time spent in a library, etc.
- Finally, :code:`user_defined` is your rummage drawer. Anything you store in here will be saved to the database with the rest of the Record, meaning you can get it back at any time, but doesn't need to conform to any structure beyond being valid JSON (and you can always stringify things to fit them into that mold). Great for any data you want to ensure is available to you, but which you know you'll never query on, or which you want to have available because you're not sure how to express in :code:`data` **yet**--you can always update your Record later, after all!

Repeat these considerations for any :code:`type` of Record you'd want to store (you can always add more later)


Handling the Ingest
-------------------

Once you know what you want in a Record, the next step is getting those Records output by your workflow.

Anything that outputs primarily JSON, CSV, YAML, or another highly structured format is fairly straightforward.
You may want to check out the `WEAVE general "bouncing ball" tutorial <https://lc.llnl.gov/gitlab/weave/weave_demos/-/tree/main/ball_bounce>`_ if you're an LC user, as it features a full DSV
workflow that might be useful as a mockup. For LC and non-LC users, the `post-processing tutorial <examples/post_processing.html>`_ contains examples of writing Sina JSON.

As you add more file formats, and those formats become less regularly structured, the work will naturally become more difficult.
Sina does have tools to alleviate it somewhat, but at the end of the day, there's no way to account for the many ways data might be expressed.

If you're dealing with more exotic structures, it may help to keep the following in mind:
- **You don't need all the answers up front**. For example, you may not immediately have an exhaustive list of questions you'd want to ask of your runs; in that case, start with the ones you do know and note down others over time. You can use a Record's :code:`files` to keep everything together and re-ingest to fit your needs, update() to add further context, etc.
- **You also don't need all the data up front**. If you're dealing with a complicated, heterogenous base of data, it may be tempting to assume that the work's not done until all that data's in the database. In reality, some of it might be rarely referenced, or only needed in the run's own context, and :code:`files` is a fine permanent home.
- Don't be afraid to use :code:`user_defined`!
- When in doubt, collect more than you'll use. Premature optimization is not a friend!
- Relationships are quick and cheap to add at any point, so long as the Records involved in them are already in the database
- You don't need to worry about performance for Sina's most common cases, especially early on! Depending on its backend, Sina has been tested with millions of runs. Focus on collecting relevant data first, and if you're unhappy with the performance, you'll have data to learn from and uncover the issue (vs, again, prematurely optimizing)

That said, there's three main ways to go about getting your data into Sina's format.

1. You can modify your data source to output raw JSON in the format. This is typically the least-recommended option, as
it's also the most fragile, and also requires familiarity with all the ins and outs of Sina. However, it allows
the source to stay fully decoupled from Sina, if you'd prefer to keep your dependencies to an absolute minimum, and also
allows for writing from sources coded in languages Sina's APIs don't interface with.

2. You can modify your data source to output Sina using one of Sina's APIs. It has both C++ and Python APIs for outputting
Records and Relationships; use whichever is more convenient for your project. This is typically a robust, efficient option,
so long as modifying the data generation code is feasible.

3. You can write a script that post-processes your data into the Sina format. This is often the quickest option (especially if
you can use a pre-written converter), and may be the only one in the case of physical instrument data. It does introduce some
frailty, as well as an additional step. It also benefits from the run being completed (may be a consideration in the
case of highly parallel workflows).


I'd then recommend running your code/problem a few times and adding it into a SQLite Sina datastore (see the `CLI docs <cli_basics.html>`__).
Check the `visualization tutorial <examples/vis_usage.ipynb>`__ for a setup example!
