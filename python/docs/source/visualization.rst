.. _visualization:

Visualization with Sina
=======================

.. note::
    This page provides a brief overview; for a deeper and more hands-on look, see the Jupyter
    notebook :code:`vis_usage.ipynb` as detailed in the :ref:`readme`.

.. warning::
    This is temporary documentation and may be replaced by a full tutorial in the
    future. Direct links may break.

Jupyter + Matplotlib
~~~~~~~~~~~~~~~~~~~~

Most Sina visualization is tied to Jupyter notebooks. Sina's :code:`visualization.py`
module provides a selection of visualizations (histograms, scatter plots, line plots, etc)
that can be configured to display data directly from a Sina database. Usage is
of the form::

  import sina
  from sina.visualization import Visualizer

  ds = sina.connect("somefile.sqlite")
  vis = Visualizer(ds)
  vis.create_histogram(x="machine")

This would create a matplotlib visualization below the cell containing a histogram
of the :code:`machine` data values of Records found in :code:`somefile.sqlite`.
The other visualizations follow the same format (ex: :code:`vis.create_scatter_plot(...)`).
All visualizations support an "interactive mode" for on-the-fly selection of data,
allow passing matplotlib options (color, alpha, etc), and expose various additional
configurations, such as title or the number of bins in a histogram. Please see the
example Jupyter notebook for more info.

Other Visualization
~~~~~~~~~~~~~~~~~~~

Sina is also supported by `PyDV <https://github.com/LLNL/PyDV/>`_. If you're on
an LC machine, usage is::

  import sys
  sys.path.append("/usr/gapps/pydv/current")
  import pydvpy as pydvif

  curves = pydvif.readsina('some_sina_file.json')

This will read in all the curve sets from a Sina file. You can treat the resulting
:code:`curves` object as you would one from pydvif.read().

You can of course visualize Sina data with matplotlib directly. See the example
Jupyter notebooks, especially the Fukushima data.
