"""
Feedstock for a vis module.

Hides the complications of serving a variety of visualizations with varying
dimensionality, many of which can be interactive or not. Conceptually, this
module works by splitting information between a few pieces:

1. The _gen_* functions define most of what you'd imagine when you hear "visualization".
   For example, _gen_histogram() takes a matplotlib figure + axis and the name of the
   data you're interested in, then configures the figure and axis to display a histogram
   filled with Sina data.
2. The _*Vis classes handle the display logic surrounding that visualization
   (such as populating dropdown selection widgets)
3. _setup_vis() handles boilerplate that allows us to decouple those first two.
4. The create_* functions merge all the above together into a user-facing method.

Usage looks like this:

vis = Visualizer(sina_datastore)

# Immediately display a plot
vis.create_histogram()

# Do further processing on a plot
my_hist = vis.create_histogram()
my_custom_matplotlib_config_func(my_hist.ax)
my_hist.display()

"""
from __future__ import print_function
from collections import defaultdict
import random
import six
# Disable pylint check due to its issue with virtual environments
# pylint: disable=import-error
import IPython.display
import ipywidgets as widgets
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # Required for 3D plotting.
assert Axes3D  # Satisfies flake8 and pylint

# Disable pylint invalid-name due to intentionally matching matplotlib's x, y, ax, etc.
# Similarly, the functions with a large number of arguments provide them for optional config
# pylint: disable=invalid-name,too-many-arguments

# Legacy solution for a single oddball case. ctrl+f
DEFAULT_GRAPH_SETTINGS = {"dimension_names": ["x", "y", "z", "4th d", "5th d"]}
# A unique, distinct string to indicate that a line plot is not using curveset values
# We use this instead of something like None so it's standard across interactive selections
# and functions, vs. having to swap between two forms.
NO_CURVE_SET = "SINA_VIS_NO_CURVE_SET"


class Visualizer(object):
    """Create visualizations from a connected Sina DataStore."""

    def __init__(self, ds, id_pool=None, matplotlib_options=None):
        """
        Configure the visualizer with top-level settings.

        :param ds: A Sina DataStore
        :param id_pool: A pool of IDs to optionally restrict visualizations to
        :param matplotlib_options: A dictionary of kwargs to pass through to matplotlib
                                   containing configurations (like graph color) to
                                   use for all axes created using this Visualizer.
        """
        self.recs = ds.records
        self.data_names = self.get_contained_data_names()
        # Used for histograms and the like
        self.data_names["scalar_and_string"] = sorted(set(self.data_names["scalar"])
                                                      .union(self.data_names["string"]))
        self.id_pool = id_pool
        self.matplotlib_options = matplotlib_options

    def create_histogram(self, x, fig=None, ax=None, interactive=False,
                         selectable_data=None, id_pool=None, title="Distribution of {x_name}",
                         num_bins=20, y_label="Count", matplotlib_options=None,):
        """
        Create a histogram (also handles string data via bar charts).

        Note that these parameters are used with little variation for the
        other create_* functions.

        :param x: The name of the scalar to plot on the x axis.
        :param fig: The matplotlib figure to add the visualization to.
        :param ax: The matplotlib axis to add the visualization to.
        :param interactive: Whether the visualization should be interactive. Provides
                            selection dropdown for configuring the axis/axes.
        :param selectable_data: If `interactive` is True, the data to fill the dropdown
                                with. If None, then provides names of data with an
                                appropriate  type.
        :param id_pool: A pool of IDs to optionally restrict visualizations to
        :param title: The title to assign to the figure (if any). Use {x_name} to
                      use the name of the x datum in the title (ex: "distribution of {x_name}").
                      Set to None to disable the title.
        :param num_bins: The number of bins to use in the histogram.
        :param y_label: The label to use for the y axis.
        :param matplotlib_options: A dictionary of kwargs to pass through to matplotlib
                                   containing configurations (like graph color) to
                                   use for this graph. Overrides any Visualizer-level ones.
        """
        return self._setup_vis(fig, ax, self._gen_histogram,
                               [x], interactive, selectable_data, id_pool, title,
                               matplotlib_options, fallback_data="scalar_and_string",
                               args=(num_bins, y_label))

    def create_scatter_plot(self, x, y, fig=None, ax=None, interactive=False,
                            selectable_data=None, id_pool=None,
                            title="{y_name} vs. {x_name}",
                            matplotlib_options=None):
        """
        Create a scatter plot.

        Uses the same params as create_histogram() with the following alterations:

        :param y: The name of the scalar to plot on the y axis.
        :param title: Same usage as histogram, but also accepts {y_name}
        """
        return self._setup_vis(fig, ax, self._gen_scatter_plot,
                               [x, y], interactive, selectable_data, id_pool,
                               title, matplotlib_options, fallback_data="scalar")

    def create_surface_plot(self, x, y, z, fig=None, ax=None, interactive=False,
                            selectable_data=None, id_pool=None,
                            title="Relationship between {x_name}, {y_name}, and {z_name}",
                            matplotlib_options=None):
        """
        Create a surface plot.

        Uses the same params as create_histogram() with the following alterations:

        :param y: The name of the scalar to plot on the y axis.
        :param z: The name of the scalar to plot on the z axis.
        :param title: Same usage as histogram, but also accepts {y_name} and {z_name}.
        """
        return self._setup_vis(fig, ax, self._gen_surface_plot,
                               [x, y, z], interactive, selectable_data, id_pool,
                               title, matplotlib_options, fallback_data="scalar")

    def create_line_plot(self, x, y, fig=None, ax=None, curve_set=None,
                         interactive=False, selectable_data=None, id_pool=None,
                         title=None, matplotlib_options=None):
        """
        Create a line plot.

        Uses the same params as create_histogram() with the following alterations:

        :param y: The name of the scalar to plot on the y axis.
        :param curve_set: The name of the curve set that x and y belong to. Curve sets
                          are a special Sina feature used to group associated dependent
                          and independent value series. For example, you might use multiple
                          timesteps for variables that need measured at different times;
                          specify the curve_set to make sure the right timestep is used.
                          If no curve set is chosen, then data will be searched for outside
                          of curve sets (that is, directly in a Record's .data portion)
        """
        # Sina currently has no way of globally getting all curves associated with a given
        # curve set. In addition, our visualization objects are supposed to be insulated
        # from the datastore. As such, for now at least, we pass in a "sample Record"
        # to inform our interactive vis (if any) what the contents of any given curve
        # set is. This assumes that records are homogenous within the id_pool.
        if id_pool is None:
            sample_rec = self.recs.get(self.recs.get_all(ids_only=True))
        else:
            sample_rec = self.recs.get(id_pool[0])
        if curve_set is None:
            curve_set = NO_CURVE_SET
        return self._setup_vis(fig, ax, self._gen_line_plot,
                               [x, y], interactive, selectable_data, id_pool,
                               title, matplotlib_options,
                               fallback_data="scalar_list", args=(curve_set, sample_rec),
                               dedicated_interactive_class=Visualizer._InteractiveCurveSetVis)

    def _combine_matplotlib_options(self, options=None):
        """
        Combine the different levels of matplotlib options in the correct order.

        Plot-specific matplotlib options take precedence over those passed to Visualizer
        on init.
        """
        combined_options = {}
        if self.matplotlib_options is not None:
            combined_options.update(self.matplotlib_options)
        if options is not None:
            combined_options.update(options)
        return combined_options

    def get_curve_values(self, id_pool, curve_names, curve_set=NO_CURVE_SET):
        """
        Given a curve or list of curves, get values for all records in <id_pool>.

        Returns a dictionary in the format
         {rec_id: {curve_name_1: [[val_1_1, ...val_1_N], [val_2_1...]]}, ...}
        """
        data = defaultdict(dict)
        if isinstance(curve_names, (list, tuple)):
            curve_names = curve_names
        else:
            curve_names = (curve_names,)
        recs = (self.recs.get(id_pool)
                if id_pool is not None
                else self.recs.get_all())
        for rec in recs:
            if curve_set != NO_CURVE_SET:
                for curve_name in curve_names:
                    data[rec.id][curve_name] = ((rec.get_curve_set(curve_set)
                                                 .get(curve_name)["value"]))
            else:
                for curve_name in curve_names:
                    try:
                        data[rec.id][curve_name] = rec.data[curve_name]["value"]
                    except KeyError:
                        # Accessing curve set data. We have to find it in the record.
                        for set_name in rec.curve_sets.keys():
                            try:
                                data[rec.id][curve_name] = (rec.get_curve_set(set_name)
                                                            .get(curve_name)["value"])
                                break
                            except AttributeError:
                                continue  # Curve wasn't in that set, try the next
        return data

    def get_contained_data_names(self, do_sort=True, filter_constants=False):
        """
        Return the names of data contained in the connected datastore.

        Used to supply lists of scalar/string/etc. names for interactive
        visualizations.

        :param do_sort: Whether to return the names in alphabetical order. Useful
                        for creating dropdowns.
        :param filter_constants: Whether to remove any data names whose value never
                                 changes (ex: an input that was the same for every run).
                                 Note that this ONLY returns scalars and strings.
                                 It doesn't check if a timeseries was always the same value,
                                 because Sina itself doesn't support that.
        :returns: A dictionary of the form {"scalars": <list of names of scalars, ...}
                  covering all types of data found in the db. Does not include
                  curve set names, which are a separate entity.
        """
        data_names = defaultdict(set)
        known_types = list(self.recs.get_types())
        for known_type in known_types:
            for data_type in ["scalar", "string", "scalar_list", "string_list"]:
                current_data_names = list(self.recs.data_names(known_type,
                                                               data_type,
                                                               filter_constants))
                data_names[data_type].update(current_data_names)
        return {data_type: sorted(list(names)) if do_sort else list(names)
                for data_type, names in data_names.items()}

    def get_curve_set_names(self, rec_type, curve_set_name):
        """
        Pull independent and dependent curve names from an (assumed) representative Record.

        Assumes homogenous Records within a type (with regards to curve set naming).

        :returns: A tuple of (independent, dependent) curve names
        """
        sample_rec = next(self.recs.find_with_type(rec_type, ids_only=True))
        sample_curve_set = self.recs.get(sample_rec).get_curve_set(curve_set_name)
        return (sample_curve_set.independent.keys(), sample_curve_set.dependent.keys())

    def get_values(self, id_pool, datum_name):
        """
        Given a datum name or list of names, get values for all records requested.

        Similar to get_data, but returns a format more suitable for graphing.

        "All records requested" is determined by the caller's id_pool setting
        (all possible records are used if id_pool=None)

        :returns: a dictionary in the format {datum_name: [val_1, val_2...]}
        """
        values = defaultdict(list)
        if isinstance(datum_name, (list, tuple)):
            datum_name = datum_name
        else:
            datum_name = (datum_name,)
        data = self.recs.get_data(data_list=datum_name,
                                  id_list=id_pool)
        for key in data.keys():
            for entry in datum_name:
                if data[key][entry]:
                    values[entry].append(data[key][entry]['value'])
        return values

    def print_summary(self, to_print=10):
        """
        Print summary information about the connected datastore.

        :returns: a dictionary expressing the names of contained data.
        """
        known_types = list(self.recs.get_types())
        print("Database contains {} records of {} type(s): {}"
              .format(len(list(self.recs.get_all(ids_only=True))),
                      len(known_types), known_types))
        known_types = list(self.recs.get_types())
        for known_type in known_types:
            print("\n---SUMMARY OF {} RECORDS---".format(known_type))
            ids_of_type = set(self.recs.find_with_type(known_type, ids_only=True))
            print("Number of records: {}\n".format(len(ids_of_type)))
            for data_type in ["scalar", "string", "scalar_list", "string_list"]:
                current_data_names = list(self.recs.data_names(known_type, data_type))
                if len(current_data_names) > to_print:
                    print("Subset of {} data names: {}\n"
                          .format(data_type, random.sample(current_data_names, to_print)))
                else:
                    print("{} data names: {}\n".format(data_type, list(current_data_names)))
            print("Sample ids: {}"
                  .format(random.sample(ids_of_type, min(to_print, len(ids_of_type)))))

    # The point of this message is to gather together shared configuration work across a
    # large number of visualization types. It might make sense to split in the future, but
    # for now, keeping it all in one function is hopefully clearer.
    # pylint: disable=too-many-locals
    def _setup_vis(self, fig, ax, gen_func, default_values, interactive, selectable_data,
                   id_pool, title, matplotlib_options, fallback_data, args=None,
                   dedicated_interactive_class=None):
        """
        Create an n-dimensional visualization bound to the given figure and axis.

        :param fig: The matplotlib figure to add a vis to. If not provided, one will be created.
        :param ax: The matplotlib ax to add a vis to. If not provided, one will be created.
        :param gen_func: The function to call to generate the visualization, ex: _gen_histogram
        :param default_values: The data names to use when initializing the graph. Doubles as
                               an expression of the graph's dimensionality.
        :param interactive: Whether to create the visualization in interactive mode.
        :param selectable_data: A list of data names that will appear in dropdowns
                                when in interactive mode.
        :param id_pool: A pool of ids to restrict the visualization to.
        :param title: The title (if any) to assign to the figure.
        :param matplotlib_options: A dictionary of settings passed directly to matplotlib.
        :param fallback_data: What to use for selectable_data if it's not specified. Graph
                              dependent.
        :param args: A list of additional arguments to be passed IN ORDER to gen_func.
                     These are used to pass through visualization-specific settings,
                     such as the number of bins to use in a histogram.
        :param dedicated_interactive_class: There's some special cases (like the line plot)
                                            that need special custom dropdowns (like curve set
                                            selection). When in interactive mode, this class
                                            will be created instead of the default interactive
                                            vis class.
        """
        combined_matplotlib_options = self._combine_matplotlib_options(matplotlib_options)
        if fig is None and ax is None:
            if len(default_values) < 3:
                fig, ax = plt.subplots(1, 1, figsize=(6, 4))
            elif len(default_values) == 3:
                # Is there a cleaner way? Feels like there should be involving subplots.
                fig = plt.figure()
                ax = fig.add_subplot(1, 1, 1, projection='3d')
            else:
                raise TypeError("Automatic fig creation for dimensions>3 is not supported")
        if args is None:
            args = []  # Avoiding unsafe default arg val
        elif fig is None or ax is None:
            raise ValueError("Must provide ax AND fig or else provide neither")
        if selectable_data is None:
            selectable_data = self.data_names[fallback_data]
        # The create_*() functions allow any axis to be None, to be filled with a default.
        # This is for easy reuse of "report formats", so that a configured notebook can
        # be loaded with any dataset and instantly "work" (though the visualizations themselves
        # might be meaningless until configured)
        for idx, value in enumerate(default_values):
            if value is None:
                default_values[idx] = selectable_data[idx]
        if isinstance(default_values, six.string_types):
            default_values = [default_values]
        if interactive:
            vis_class = (Visualizer._InteractiveVis if dedicated_interactive_class is None
                         else dedicated_interactive_class)
            vis = vis_class(fig, ax, gen_func, default_values,
                            selectable_data, id_pool, title,
                            combined_matplotlib_options, args)
        else:
            vis = Visualizer._NonInteractiveVis(fig, ax, gen_func, default_values, id_pool,
                                                title, combined_matplotlib_options, args)
        return vis

    # The _gen functions share a signature. Not all make use of fig.
    # pylint: disable=unused-argument
    def _gen_histogram(self, fig, ax, value_names, id_pool, title, matplotlib_options,
                       num_bins, y_label):
        """
        Generate a hist or bar graph depending on value's type.

        :param fig: The matplotlib figure to configure.
        :param ax: The matplotlib axis to configure.
        :param value_names: A list of names of data indicating what datum goes on
                            each axis of the visualization. Should be exactly as long
                            as the number of dimensions in the visualization.
        :param id_pool: A pool of IDs to optionally restrict visualizations to
        :param title: The title to assign to the figure (if any).
        :param matplotlib_options: A dictionary of kwargs to pass through to matplotlib
                                   containing configurations (like graph color) to
                                   use for this graph. Overrides any Visualizer-level ones.
        :param num_bins: The number of bins to use in the histogram.
        :param y_label: The label to use for the y axis.
        """
        x_name = value_names[0]
        values = self.get_values(id_pool, x_name)[x_name]
        ax.cla()
        if value_names[0] in self.data_names["scalar"]:
            ax.hist(values,
                    num_bins,
                    **matplotlib_options)
            # Workaround for numpy issue with large numbers in bins:
            # https://github.com/matplotlib/matplotlib/issues/609/
            ax.set_xrange = (0.5*min(values), max(values)*1.5) if max(values) > 1e15 else None
        else:  # Generate a bar graph pretending to be a histogram
            labels, counts = np.unique(values, return_counts=True)
            ticks = range(len(counts))
            ax.set_xticks(ticks)
            ax.set_xticklabels(labels)
            ax.bar(ticks, counts, align='center', **matplotlib_options)
        if y_label is not None:
            ax.set_ylabel(y_label)
        ax.set_xlabel(x_name)
        if title is not None:
            ax.set_title(title.format(x_name=x_name))

    # The _gen functions share a signature. Not all make use of fig.
    # pylint: disable=unused-argument
    def _gen_scatter_plot(self, fig, ax, value_names, id_pool, title,
                          matplotlib_options):
        """
        Generate a scatterplot.

        Uses the same params (technically a subset of them) as create_histogram().
        """
        x_name, y_name = value_names
        ax.cla()
        data = self.get_values(id_pool, [x_name, y_name])
        ax.scatter(data[x_name],
                   data[y_name],
                   **matplotlib_options)
        ax.set_xlabel(x_name)
        ax.set_ylabel(y_name)
        if title is not None:
            ax.set_title(title.format(x_name=x_name, y_name=y_name))

    def _gen_surface_plot(self, fig, ax, value_names, id_pool, title, matplotlib_options):
        """
        Generate a surface plot.

        Uses the same params as create_histogram().
        """
        x_name, y_name, z_name = value_names
        ax.cla()
        data = self.get_values(id_pool, [x_name, y_name, z_name])
        try:
            surface_plot = ax.plot_trisurf(data[x_name], data[y_name], data[z_name],
                                           **matplotlib_options)
        except RuntimeError as e:
            print("""Encountered an error while creating the plot. Do one or more scalars have an
insufficient number of unique values to create a trisurface plot?: {}""".format(str(e)))
        ax.set_xlabel(x_name)
        ax.set_ylabel(y_name)
        ax.set_zlabel(z_name)
        if title is not None:
            ax.set_title(title.format(x_name=x_name, y_name=y_name, z_name=z_name))
        # Add a color bar which maps values to colors.
        if matplotlib_options.get("cmap"):
            fig.colorbar(surface_plot, shrink=0.5, aspect=5)

    def _gen_line_plot(self, fig, ax, value_names, id_pool, title, matplotlib_options, curve_set):
        """
        Generate a lineplot.

        Uses the same params as create_histogram(), plus curve_set to set the curve set.
        """
        x_of_interest, y_of_interest = value_names
        ax.cla()
        data = self.get_curve_values(id_pool, [x_of_interest, y_of_interest],
                                     curve_set=curve_set)
        # Doesn't currently support customizing curve colors
        target_ids = data.keys()
        for run_id in target_ids:
            x_data, y_data = (data[run_id][x_of_interest], data[run_id][y_of_interest])
            if len(x_data) != len(y_data):
                print("ERROR: Length mismatch! {} has {} entries, while {} has {}"
                      .format(x_of_interest, len(x_data), y_of_interest, len(y_data)))
                return
            ax.plot(x_data, y_data, **matplotlib_options)
        ax.set_xlabel(x_of_interest)
        ax.set_ylabel(y_of_interest)
        ax.legend(target_ids)
        if title is not None:
            ax.set_title(title.format(x_name=x_of_interest, y_name=y_of_interest))

    class _NonInteractiveVis(object):  # pylint: disable=too-many-instance-attributes
        """Helper class for standardizing fig/ax access between visualizations."""

        # Lots of things to potentially hand off; not user-facing, should be fine.
        def __init__(self, fig, ax, gen_func, default_values, id_pool, title,
                     matplotlib_options, args, _delay_display=False):
            """Do not call directly, use Visualizer's create_* instead."""
            self.fig = fig
            self.ax = ax
            self.gen_func = gen_func
            self.default_values = default_values
            self.id_pool = id_pool
            self.title = title
            self.matplotlib_options = matplotlib_options
            self.args = args
            # Child callers want to delay display for widget setup
            if not _delay_display:
                self.display()

        def get_fig(self):
            """Return the matplotlib figure associated with this vis."""
            return self.fig

        def get_ax(self):
            """Return the matplotlib axis associated with this vis."""
            return self.ax

        def display(self):
            """Display the resulting vis, ex: in a Jupyter notebook."""
            self.gen_func(self.fig, self.ax, self.default_values, self.id_pool,
                          self.title, self.matplotlib_options, *self.args)
            self.fig.canvas.draw()

        def get_formatted_fig_ax(self):
            """
            Return the fig and ax.

            Used by _setup_vis to return something the Jupyter notebook will
            automatically visualize without exposing the Vis object to the user.
            """
            return (self.fig, self.ax)

    class _InteractiveVis(_NonInteractiveVis):
        """
        Helper class for managing interactive visualizations.

        Supports select() relying on <self> for context.
        """

        # Pylint ignore: same as for _NonInteractiveVis
        def __init__(self, fig, ax, gen_func, default_values, selectable_data,
                     id_pool, title, matplotlib_options, args,
                     _delay_display=False):   # pylint: disable=too-many-instance-attributes
            """Do not call directly, use Visualizer's create_* instead."""
            # It's "protected" because they're hidden in favor of the create_* method.
            # pylint: disable=protected-access
            super(Visualizer._InteractiveVis, self).__init__(
                fig, ax, gen_func, default_values, id_pool,
                title, matplotlib_options, args, _delay_display=True)
            self.widgets = []
            self.selectable_data = selectable_data
            for dim in range(len(default_values)):
                self.widgets.append(self.init_dropdown(
                    self.default_values[dim],
                    # Hardcoded for now. May revisit if use case arises.
                    DEFAULT_GRAPH_SETTINGS["dimension_names"][dim]))
                select_func = self.gen_select(dim)
                self.widgets[dim].observe(select_func)
            # Children may have further setup and so want to call display themselves.
            if not _delay_display:
                self.gen_func(self.fig, self.ax, self.default_values, self.id_pool,
                              self.title, self.matplotlib_options, *self.args)
                self.display()

        def init_dropdown(self, initial_val, name):
            """Initialize a dropdown selector."""
            widget = widgets.Dropdown(options=self.selectable_data,
                                      value=initial_val,
                                      description="{} data name:".format(name),
                                      disabled=False)
            return widget

        def gen_select(self, dim):
            """Create a function to be called when the graph axes are changed."""
            def generic_select(change):
                """Regenerate the graph when the x dropdown is changed."""
                if not (change['type'] == 'change' and change['name'] == 'value'):
                    return
                self.default_values[dim] = change['new']
                self.gen_func(self.fig, self.ax, self.default_values, self.id_pool,
                              self.title, self.matplotlib_options, *self.args)
                self.fig.canvas.draw()
            return generic_select

        def display(self):
            """Display all the interactive widgets and the visualization itelf."""
            for widget in self.widgets:
                IPython.display.display(widget)
            self.gen_func(self.fig, self.ax, self.default_values, self.id_pool,
                          self.title, self.matplotlib_options, *self.args)
            self.fig.canvas.draw()

    class _InteractiveCurveSetVis(_InteractiveVis):
        """
        Helper class for managing interactive visualizations that specifically use curve sets.

        Responsible for adding an additional dropdown for choosing curve set.
        """

        def __init__(self, fig, ax, gen_func, default_values, selectable_data,
                     id_pool, title, matplotlib_options, args):
            """Do not call directly, use Visualizer's create_* instead."""
            # pylint: disable=protected-access
            super(Visualizer._InteractiveCurveSetVis, self).__init__(
                fig, ax, gen_func, default_values, selectable_data,
                id_pool, title, matplotlib_options, args, _delay_display=True)
            # This dedicated vis class only works with curve sets, so we know our args:
            self.curve_set, self.sample_rec = args
            self.available_curve_sets = list(self.sample_rec.curve_sets.keys())
            self.available_curve_sets.append(NO_CURVE_SET)
            self.available_curves = self.get_curves_in_current_set()
            curve_set_select_widget = self.init_curve_set_dropdown()
            curve_set_select_widget.observe(self.gen_curve_set_select())
            self.widgets.insert(0, curve_set_select_widget)
            # We do this here because the super() call needs to come first.
            # This sets our axes dropdowns to match our curve set, then draws
            self.display()
            self.reset_selectable_curves()

        def get_curves_in_current_set(self):
            """Return all curves (both dependent and independent) for a curve set name."""
            # Might make a nice addition to the CurveSet object over in model.py
            if self.curve_set != NO_CURVE_SET:
                return list(set(self.sample_rec.curve_sets[self.curve_set]["independent"].keys())
                            .union(self.sample_rec.curve_sets[self.curve_set]["dependent"].keys()))
            return self.selectable_data

        def reset_selectable_curves(self):
            """Reset the selection dropdowns to fit the current curve set."""
            for idx in range(1, len(self.widgets)):  # Don't reset the curve set widget
                # Dynamically resetting the options for a widget is pretty nasty, and
                # involves observe/unobserve chicanery that isn't well documented.
                # Instead, since they're simple, we recreate them.
                dim = idx-1  # We have the curve set dropdown first for user ease
                self.widgets[idx].close()
                self.widgets[idx] = self.init_curve_axis_dropdown(
                    self.available_curves[0],
                    DEFAULT_GRAPH_SETTINGS["dimension_names"][dim])
                self.widgets[idx].observe(self.gen_axis_select(dim))
                self.default_values[dim] = self.available_curves[0]
                IPython.display.display(self.widgets[idx])
            self.gen_func(self.fig, self.ax, self.default_values, self.id_pool,
                          self.title, self.matplotlib_options, self.curve_set)
            self.fig.canvas.draw()

        def init_curve_set_dropdown(self):
            """Initialize a dropdown selector."""
            widget = widgets.Dropdown(options=self.available_curve_sets,
                                      value=self.curve_set,
                                      description="Curve set:",
                                      disabled=False)
            return widget

        def init_curve_axis_dropdown(self, initial_val, name):
            """Initialize a dropdown selector."""
            widget = widgets.Dropdown(options=self.available_curves,
                                      value=initial_val,
                                      description="{} data name:".format(name),
                                      disabled=False)
            return widget

        def gen_axis_select(self, dim):
            """Create a function to be called when the graph axes are changed."""
            def generic_select(change):
                """Regenerate the graph when an axis dropdown is changed."""
                if not (change['type'] == 'change' and change['name'] == 'value'):
                    return
                self.default_values[dim] = change['new']
                self.gen_func(self.fig, self.ax, self.default_values, self.id_pool,
                              self.title, self.matplotlib_options, self.curve_set)
                self.fig.canvas.draw()
            return generic_select

        def gen_curve_set_select(self):
            """Create a function to be called when the curve set is changed."""
            def select_curve_set(change):
                """Regenerate the graph when the curve set dropdown is changed."""
                if not (change['type'] == 'change' and change['name'] == 'value'):
                    return
                self.curve_set = change['new']
                self.available_curves = self.get_curves_in_current_set()
                self.reset_selectable_curves()
            return select_curve_set

        def display(self):
            """Display all the interactive widgets and the visualization itelf."""
            for widget in self.widgets:
                IPython.display.display(widget)
            self.gen_func(self.fig, self.ax, self.default_values, self.id_pool,
                          self.title, self.matplotlib_options, self.curve_set)
            self.fig.canvas.draw()
