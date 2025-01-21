.. Sina documentation master file, created by
   sphinx-quickstart on Thu Dec 14 11:13:32 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Sina's documentation!
++++++++++++++++++++++++++++++++

Sina exists to put more data into user's hands, more quickly, at larger scales, and with minimal time investment from code teams or users,
all without interrupting existing user workflows.

In brief, it comes in two parts: a C++ library that's called from within codes to output data to a common format, and a Python API + toolset
providing a wide range of functionality for working with these files.

Naturally, you can use a lot of Sina or just a little. Here's our major features and where to go to learn more,
ordered as "increasing amounts of Sina" from the end-user perspective.


Sina integrates with codes to output data
-----------------------------------------
Sina collects data directly within codes, outputting them to a common file output format designed alongside code teams and users. Typically called <something>_sina.json, Sina's file is optionally output at the end of (or during) a run, and contains metadata, physics quantities, deck info, etc.

If you want to see if your code of choice has Sina integration (potentially including customization on the type(s) of data output), see `here <https://lc.llnl.gov/confluence/display/WEAV/Sina+Integration>`__. If you'd like to learn about adding Sina to a code, check out our `C++ documentation <cpp.html>`__, and reach out to us at weave-support@llnl.gov.

Data are organized for easy access and automation
-------------------------------------------------
If you'd like to work with Sina files directly (or output them without C++ integration), check out the `schema details <sina_schema.html>`__. While using Sina's API is generally recommended over direct access, operating on Sina JSON provides quick, structured access to data of interest.

Sina's Python API provides QoL for post-processing...
-----------------------------------------------------
Working with the Sina API adds durability and QoL to your post-processing to keep your scripts portable, durable, and generally more pleasant to work with. See the `post-processing tutorial <examples/post_processing.html>`__ for more.

...and powerful queries for working with large numbers of runs
--------------------------------------------------------------
To support workflows that cover problem spaces where not all results are "equally interesting", Sina can leverage its format to compare tens of thousands of runs (or less, or more) to help you find relevant results. Sina does this by taking advantage of backends supported by LC (mostly sqlite and MySQL/MariaDB), but this is "hidden" from the user by our simple Python API. Essentially, you say something like "I want to look at every run where <package> was enabled, etot was >1.112", etc, getting the advantages of both Python accessibility and database performance. A large chunk of our documentation is dedicated to this; users should check out the `basic usage tutorial <examples/basic_usage.html>`__ to start.

Simple aggregate visualizations allow for visual exploration of run sets
------------------------------------------------------------------------
Sina provides its own visualization module, essentially queries mixed into a plotting library and wrapped with interactive elements via Jupyter. These allow you to display summary data from all your runs at once (ex: a histogram of etots), optionally without writing any code, enabling the creation of interactive, live "reports". Learn more in the `visualization tutorial <examples/vis_usage.html>`__

And more!
---------
Sina can't solve every problem, but we do hope to help with common data management troubles, slot easily into workflows, and generally support fast, easy, and sane access of the data users care about. We also act as the basis for other tools that expand on Sina's functionality, namely `Kosh <https://kosh.readthedocs.io/en/latest/>`__ (which adds loaders for non-common-file-format data). If you're intending to incorporate Sina into a workflow yourself (or otherwise want a more "holistic" understanding of what's going on), I'd recommend going down the left bar in order (though check out `API Concepts <api_basics.html>`__ first if you prefer to have the "what" and "why" before the "how"). And please don't hesitate to reach out to us!


Installation/Accessing Sina
+++++++++++++++++++++++++++

.. toctree::
   :maxdepth: 1

   readme


Quickstart and Tutorials
++++++++++++++++++++++++

.. toctree::
   :maxdepth: 2

   examples/index


Documentation
+++++++++++++

.. toctree::
   :maxdepth: 2

   api_basics
   cli_basics
   adding_sina_to_workflow
   sina_schema
   faq
   cpp
   changelog
   modules

* :ref:`genindex`
* :ref:`modindex`
