"""
Convert the pickle files produced by the icf workflow to Mnoda JSON format.

For more information about Mnoda, please see this link:

https://lc.llnl.gov/confluence/display/SIBO/Mnoda+Discussion+page+to+develop+a+JSON+schema+and+tools+for+Simulation+Information

TODO: Replace with link to Mnoda repo when it goes live

This is modified from Dan Laney's icf2json converter.
"""

import json
import uuid
import os
import datetime
import sys
import pickle


# The number of runs to wait before writing to a checkpoint file.
CHECKPOINT_INTERVAL = 50


class BurnAvgData:
    """Class which allows access to data in a summary_burn_avg.pkl file."""

    def __init__(self, fname):
        """Load in pickle file, retrieve run_ids."""
        with open(fname) as f:
            self.burn = pickle.load(f)
            self.run_ids = [r for r in self.burn.keys() if r != 'name_index']

    def get_var(self, runId, varName):
        """
        Get the value of a variable given a runID.

        :param runId: integer run ID
        :param varName: name of the variable to return

        :returns: the value of varName in run #runId

        """
        i = self.burn["name_index"].index(
            varName)   # the index of the field we want
        return self.burn[runId]['data'][i]

    def get_run_outputs(self, runId):
        """
        Extract output scalars for a given run from the master pickle.

        :param runId: integer run ID

        :returns: list of Mnoda "value"-format dicts representing run's
                  (scalar) outputs
        """
        out = []
        for name in self.burn['name_index']:
            out.append({'name': name, 'value': self.get_var(
                runId, name), 'tags': ['output']})
        return out

    def get_run_inputs_and_meta(self, runId, metadata_names):
        """
        Extract input scalars and metadata for run from the master pickle.

        Decides what is an "input" and what is "metadata" based on a provided
        list, metadata_names.

        :param runId: integer run ID
        :param metadata_names: list of names of metadata to filter on

        :returns: a tuple of ([run_scalars],[run_metadata]), with lists
                 composed of Mnoda "value" and "user-defined"-format dicts,
                 respectively.
        """
        data = self.burn[runId]['info']
        # We make a copy of data as we'll need to delete some entries locally
        masterlist = dict(data)
        metadata = []
        for name in metadata_names:
            metadata.append({'name': name, 'value': masterlist[name]})
            del masterlist[name]
        inputs = [{'name': x, 'value': y, 'tags': ['input']}
                  for x, y in masterlist.items()]
        return (inputs, metadata)

    def get_run(self, runId):
        """
        Given a run ID, return a JSON-compatible Python dict describing run.

        :param runId: The ID for the run, essentially a local id.

        :returns: The run as a Mnoda "object"-format dict.
        """
        r = {
            'type': 'run',
            'id': str(uuid.uuid4()),
            'application': 'hydra',
            'version': 'Unknown',

            # Input files currently always empty
            # 'input_files': [],

            # Populated in a later function call
            'output_files': [],

            'values': [],
            'user-defined': {},
        }

        uqp_meta_keys = ['ASV_1', 'ASV_2', 'ASV_3', 'ASV_4', 'ASV_5', 'ASV_6',
                         'DAKOTA_AN_COMPS', 'DAKOTA_DER_VARS', 'DAKOTA_FNS',
                         'DAKOTA_VARS', 'DVV_1', 'RunID']

        r['values'], metadata = self.get_run_inputs_and_meta(
            runId, uqp_meta_keys)
        r['values'].extend(self.get_run_outputs(runId))
        r['user-defined'] = metadata
        return r


def _get_filepaths(dirpath):
    """
    Return list of absolute paths to files in tree rooted at dirpath.

    :param dirpath: the path of the directory to crawl

    :returns: a list of absolute filepaths to files found.

    """
    result = []
    for (dirpath, dirs, files) in os.walk(dirpath):
        pth = os.path.abspath(dirpath)
        for f in files:
            result.append(os.path.join(pth, f))
    return result


def get_filepaths_of_run(path_to_runs, runId):
    """
    Walk run's subdirectory tree to find absolute filepaths.

    :param path_to_runs: location of the runs we're iterating over
    :param runId: id of the specific run we're getting filepaths for

    :returns: a list of Mnoda "file"-format dicts.
    """
    run_path = os.path.join(path_to_runs, 'run%04d' % runId)
    files = _get_filepaths(run_path)
    return [{'uri': f, 'mime_type': f.split('.')[-1]} for f in files]


def create_task(path_to_container):
    """
    Create a 'Task' from the DOE directory.

    Return the design of experiement directory (the directory containing the
    container) as a 'Task', an 'unsupported' toplevel object that contains all
    runs.

    :param path_to_container: The path to the directory containing the runs

    :returns: A Mnoda "object"-format dict representing the task
    """
    path = os.path.split(os.path.abspath(path_to_container))
    task = {
        'type': 'task',
        # example of a provided (hopefully) global ID
        'id': (path[-2] + '/' + path[-1] + '_' + datetime.datetime
               .fromtimestamp(os.path.getmtime(path_to_container))
               .strftime("%Y_%m_%d_%H_%M")
               ), 'application': 'hydra', 'version': 'Unknown'
           }
    return task


def main():
    """
    Launch CLI for streaming JSON docs to STDOUT from ICF simulations folder.

    Feeds .pkl file data into a series of dictionaries patterned off of the
    JSON objects described by the Mnoda schema, then organizes those
    dictionaries and exports them as a single JSON file.
    """
    from argparse import ArgumentParser

    parser = ArgumentParser(
        prog="icfdata",
        description="A tool to output ICF ensemble data as JSON documents to "
                    "stdout. Note that a Mnoda JSON can't be written until "
                    "complete, so if you expect interruptions, provide a "
                    "checkpoint file with -c.")
    parser.add_argument(
        "container_dir",
        help="Path to container directory. A container contains a data "
        "associated with a set of runs, typically the result of "
        "running the UQ Pipeline and analyzing the results.")
    parser.add_argument('-p', '--pretty', action='store_true',
                        help="Format the JSON output for human consumption.")
    parser.add_argument(
        '-n',
        '--no-paths',
        action='store_false',
        dest="with_paths",
        help="Don't walk directories to get filepaths associated with runs.")
    parser.add_argument(
        '-r',
        '--run',
        type=int,
        help="Returns only the single JSON document of the given run ID.")
    parser.add_argument(
        '-c',
        '--checkpoint',
        help="Path to checkpoint file. If provided, each time this script "
             "completes CHECKPOINT_INTERVAL runs (default 50), it will dump "
             "the contents of the Mnoda object to the provided checkpoint "
             "file (overwrites previous contents).")
    args = parser.parse_args()

    if args.pretty:
        indent = 4
        sort_keys = True
        separators = (',', ': ')
    else:
        indent = None
        sort_keys = None
        separators = (',', ':')   # remove spaces around , and : as well

    # The path to the files and run directories in the container
    data_dir = os.path.join(args.container_dir, "deck", "base")
    summary_burn_fname = os.path.join(data_dir, "summary_burn_avg_data.pkl")

    # There are other data files, but we only process this one for now.
    data = BurnAvgData(summary_burn_fname)

    if args.run is None:
        runIds = data.run_ids
    else:
        if args.run in data.run_ids:
            runIds = [args.run]
        else:
            print("\nERROR: run {} does not exist.\n".format(args.run))
            sys.exit(0)

    mnoda = {
        'objects': [],
        'relationships': []
    }
    task = create_task(args.container_dir)
    task_id = task['id']
    mnoda['objects'].append(task)

    for run_id in runIds:
        run = data.get_run(run_id)
        if args.with_paths:
            run['output_files'] = get_filepaths_of_run(data_dir, run_id)
        mnoda['objects'].append(run)
        mnoda['relationships'].append(
            {'subject': task_id, 'predicate': 'contains', 'object': run['id']})
        if args.checkpoint and (run_id % CHECKPOINT_INTERVAL == 0 or run_id == runIds[-1]):
            with open(args.checkpoint, "w") as out:
                json.dump(
                    mnoda,
                    out,
                    indent=indent,
                    sort_keys=sort_keys,
                    separators=separators)

    print(json.dumps(
        mnoda,
        indent=indent,
        sort_keys=sort_keys,
        separators=separators))


if __name__ == "__main__":

    main()
