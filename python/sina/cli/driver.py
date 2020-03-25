"""
Launcher.py provides command-line functionality for Sina.

Internally, it handles parsing args and setting up logging.


Example::

    $sina -f <some_string> -d <some_db>

Returns a list of filepaths from some_db containing some_string.

"""
from __future__ import print_function
import logging
import inspect
import sys
import os
from argparse import ArgumentParser, RawTextHelpFormatter

from sqlite3 import connect

# Disable pylint check due to its issues with virtual environments
from sqlalchemy.orm.exc import NoResultFound  # pylint: disable=import-error
try:
    from cassandra.cluster import Cluster
    CASSANDRA_PRESENT = True
except ImportError:
    CASSANDRA_PRESENT = False

from sina import utils
from sina.utils import import_json, parse_data_string, create_file
import sina.datastores.sql as sql
if CASSANDRA_PRESENT:
    import sina.datastores.cass as cass

try:
    import sina.cli.diff
    CLI_TOOLS_PRESENT = True
except ImportError:
    CLI_TOOLS_PRESENT = False

ROOTLOGGER = logging.getLogger(inspect.getmodule(__name__))
LOGGER = logging.getLogger(__name__)
LOG_FORMAT = "%(asctime)s - %(name)s:%(funcName)s:%(lineno)s - " \
             "%(levelname)s - %(message)s"
DEFAULT_LOG_PATH = os.path.join(os.path.expanduser('~'), '.sina/sina.log')
DEFAULT_LOG_LEVEL = 'WARNING'
DEFAULT_DATABASE = 'demos/api/demo.sqlite'
DEFAULT_SCALARS = ['problem_size', 'mpi_tasks']
COMMON_OPTION_DATABASE = '--database'
COMMON_SHORT_OPTION_DATABASE = '-d'
COMMON_OPTION_DATABASE_TYPE = '--database-type'
COMMON_OPTION_CASSANDRA_DEST = '--keyspace'

__VERSION__ = __import__('sina').get_version()


def setup_arg_parser():
    """
    Set up the argument parser.

    :returns: A parser object.
    """
    parser = ArgumentParser(prog='sina',
                            description='A software package to process '
                            'data stored in the sina_model format.',
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument('-v', '--version', action='store_true',
                        help="display version information and exit.")
    parser.add_argument('-s', '--stdout', action='store_true',
                        help='display logs to stdout.')
    parser.add_argument('-l', '--loglevel', help='What level to log at.',
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO',
                                 'DEBUG'])
    parser.add_argument('-p', '--logpath', help='Where to put the log file.',)
    subparsers = parser.add_subparsers(title='subcommands', help='Available '
                                       'sub-commands.', dest='subparser_name')
    add_ingest_subparser(subparsers)
    add_export_subparser(subparsers)
    add_query_subparser(subparsers)
    if CLI_TOOLS_PRESENT:
        add_compare_subparser(subparsers)
    return parser


def add_ingest_subparser(subparsers):
    """Add subparser for ingesting Sina-format contents into backends."""
    parser_ingest = subparsers.add_parser(
        'ingest', help='ingest complete Sina-type information and insert into'
                       ' a specified database. See "sina ingest -h" for more '
                       'information.')
    _add_common_args(parser=parser_ingest)
    # pylint: disable=fixme
    # TODO: If use case is Localhost and/or RZSonar, might make sense to have
    # keyspace be the database arg and provide IP/port the special way.
    # This isn't out of line with cql, which will start fine without an
    # ip/port provided (assumes Localhost) and can take a keyspace. SIBO-780

    parser_ingest.add_argument('source', type=str,
                               help='The URI or list of URIs to ingest from. '
                               'Data must be compliant with the Sina schema, '
                               'and can be in any of the supported backends. '
                               'Comma-separated.')
    # pylint: disable=fixme
    # TODO: What if they supply a folder? We'll probably want to support that.
    # I think they should only be able to provide one source-type. They can
    # pipe `find` in if they want to do something fancy--if we try to parse
    # something from a folder and fail because it's the wrong backend, it's
    # time to fail and complain. SIBO-780
    parser_ingest.add_argument('--source-type', type=str,
                               help='The type of the URIs being ingested. Sina '
                               'will try to infer this from --source if '
                               '--source-type is not provided. All URIs being '
                               'ingested in one command must share a type.',
                               choices=['json'])


def add_export_subparser(subparsers):
    """Add subparser for exporting from backends into various formats."""
    parser_export = subparsers.add_parser(
        'export', help='export from a Sina-compliant backend into various, '
                       'subset-like formats. Allows for exporting '
                       'information that is not importable with this tool; if '
                       'you want to produce complete Sina schema, try '
                       '`sina import`ing to JSON or csv. See "sina export -h" '
                       'for more information.'
                       'Currently, the only supported export format is csv.')
    required = parser_export.add_argument_group("required arguments")
    _add_common_args(parser=parser_export, required_group=required)
    parser_export.add_argument('--export-type', default='csv',
                               type=str, help='The type of export to run. '
                               'Currently support: csv (default).',
                               choices=['csv'])
    parser_export.add_argument('--target', nargs='?', const='', type=str,
                               help='The filepath to write to. Defaults to: '
                               'output_{timestamp}')
    required.add_argument('-s', '--scalars', required=True, type=str,
                          help='A comma separated list of scalar names '
                               'to output.')
    required.add_argument('-i', '--ids', required=True, type=str,
                          help='A comma separated list of record ids to '
                               'output.')


def add_query_subparser(subparsers):
    """Add subparser for performing queries on backends."""
    parser_query = subparsers.add_parser(
        'query', help='perform a query against a Sina-compliant backend. '
                      'See "sina query -h" for more information.')
    _add_common_args(parser=parser_query)
    # pylint: disable=fixme
    # TODO: This is the prior formatting. But if do comma-separated and hit
    # something that doesn't look like an entire scalar, it's either a range
    # or an error, and it should be easy enough to tell the difference. Given
    # that comma-separated is the standard, might be worth changing. SIBO-780
    parser_query.add_argument('-s', '--scalar', type=str,
                              help='Specify space-separated scalars to search '
                              'on. Sina will return ids for all records '
                              'for which *all* conditions are fulfilled. '
                              'Accepts both operators and inclusive/exclusive '
                              'ranges. Example:'
                              '\n\n'
                              '-s "size=3 tilt=[2,3] height>=2.05 foo=[2,]"'
                              '\n\n'
                              'will return ids of all records where size '
                              'is exactly 3, tilt is between 2 and 3 '
                              '(inclusive), height is greater than or equal to '
                              '2.05, *and* foo is greater than or equal to 2.')
    parser_query.add_argument('-u', '--uri', type=str,
                              help='Specify a uri to search on. %% can be used '
                              'as a wildcard, but incurs a performance hit '
                              '(and, depending on Cassandra instance '
                              'settings, may not be available for that '
                              'backend.) Example:\n\n -f foo%%/bar.%% \n\n'
                              'will return ids of all records associated '
                              'with a document matching '
                              'foo<wildcard>/bar.<wildcard>, such as '
                              'foo/bar.baz, foo/qux/bar.bin, etc.')

    parser_query.add_argument('-r', '--raw', type=str,
                              help='Specify a raw query to perform. Use at '
                              'your own risk! This is not intended for '
                              'general use, as it requires knowledge of both '
                              'Sina internal schema and backend queries. Not '
                              'available for all backends.  Example:'
                              '\n\n'
                              '-r "Select * from Records where type="'
                              '\n\n'
                              'will return the ids of all records associated '
                              'with a document matching '
                              'foo<wildcard>/bar.<wildcard>, such as '
                              'foo/bar.baz, foo/qux/bar.bin, etc.')
    parser_query.add_argument('--id', action='store_true',
                              help='Only return the IDs of matching Records.')


def add_compare_subparser(subparsers):
    """Add subparser for performing record comparisons."""
    parser_compare = subparsers.add_parser(
        'compare', help='perform a comparison against two records. '
                        'See "sina compare -h" for more information.')
    _add_common_args(parser=parser_compare)
    parser_compare.add_argument('id_one', type=str,
                                help='The first id of the record to compare.')
    parser_compare.add_argument('id_two', type=str,
                                help='The second id of the record to compare.')


def _add_common_args(parser, required_group=None):
    """
    Add common arguments to the given parser.

    :param parser: The parser to add the args to.
    :param required_group: The argument group to add required arguments to. If None, will create
        one.
    """
    if not required_group:
        required_group = parser.add_argument_group("required arguments")
    required_group.add_argument(COMMON_SHORT_OPTION_DATABASE,
                                COMMON_OPTION_DATABASE,
                                type=str,
                                required=True,
                                dest='database',
                                help='URI of database to connect to. For Cassandra: <ip>:<port>, '
                                'use {} to specify keyspace. For SQLite: <filepath>. If "sql" is '
                                'specified as the database type and this contains "://", then '
                                'this is interpreted as the URL to pass to the database connector.'
                                .format(COMMON_OPTION_CASSANDRA_DEST))
    parser.add_argument(COMMON_OPTION_CASSANDRA_DEST,
                        type=str,
                        dest='cass_keyspace',
                        help='If using a Cassandra database, the keyspace to use. Ignored by '
                        'other database types.')
    parser.add_argument(COMMON_OPTION_DATABASE_TYPE,
                        type=str,
                        dest='database_type',
                        help='Type of database to connect to. Sina will try to infer this from {} '
                        'if that is provided, but {} is not.'
                        .format(COMMON_OPTION_DATABASE,
                                COMMON_OPTION_DATABASE_TYPE),
                        choices=['cass', 'sql'])


def _validate_cassandra_args(args):
    """
    Check to see if Cassandra is usable and used correctly.

    :param args: The args passed by the user.
    :returns: A list of any issues encountered.
    """
    error_message = []
    if not CASSANDRA_PRESENT:
        error_message.append("The Cassandra driver has not been installed; "
                             "no Cassandra functionality is available.")
    if not args.cass_keyspace:
        error_message.append("{} not provided. In "
                             "the future, it will be possible to "
                             "set a default. For now, please "
                             "specify it to continue!".format(COMMON_OPTION_CASSANDRA_DEST))
    return error_message


def setup_logging(args):
    """
    Set up logging based on provided log params.

    :params args: (ArgumentParser, req) Command line args that tell us
        how to set up logging. If not provided, use some defaults.

    """
    if args.logpath:
        logpath = args.logpath
    else:
        logpath = DEFAULT_LOG_PATH
    if args.loglevel:
        loglevel = args.loglevel
    else:
        loglevel = DEFAULT_LOG_LEVEL

    create_file(logpath)

    formatter = logging.Formatter(LOG_FORMAT)
    ROOTLOGGER.setLevel(loglevel)

    # Setup file handler
    file_handler = logging.FileHandler(logpath)
    file_handler.setLevel(loglevel)
    file_handler.setFormatter(formatter)
    ROOTLOGGER.addHandler(file_handler)

    if args.stdout:
        # Add the StreamHandler
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(loglevel)
        stream_handler.setFormatter(formatter)
        ROOTLOGGER.addHandler(stream_handler)

    LOGGER.info("-------------------------STARTING-------------------------")
    LOGGER.info("INFO Logging Level -- Enabled")
    LOGGER.warning("WARNING Logging Level -- Enabled")
    LOGGER.critical("CRITICAL Logging Level -- Enabled")
    LOGGER.debug("DEBUG Logging Level -- Enabled")


def ingest(args):
    """
    Run logic associated with ingestion subparser.

    :params args: (ArgumentParser, req) Command line args that tell us what
        pattern and database to use.

    :raises ValueError: if there's an issue with flags (bad filetype, etc)
    """
    LOGGER.info('Ingesting source_list=%s into database=%s, database_type=%s.',
                args.source, args.database, args.database_type)
    error_message = []
    source_list = args.source.split(",")
    if not args.source_type:
        source_types = [_get_guessed_database_type(x) for x in source_list]
        if not source_types.count(source_types[0]) == len(source_types):
            error_message.append("When using multiple sources within a "
                                 "command, all must be of the same type.")
        args.source_type = source_types[0]
        if not args.source_type:
            error_message.append("--source-type not provided and unable "
                                 "to guess type from source. Please "
                                 "specify --source-type. Currently, only "
                                 "json is supported for importing from.")
        # While the explicit cli flag has set supported choices, we need to
        # check ourselves if the flag is inferred.

        # Probably a clever way to get argparse's list of choices rather than
        # hardcoding it, might be worth revisiting.
        elif args.source_type not in ['json']:
            error_message.append("Currently, ingesting is only supported when "
                                 "using json files as the source.")
    error_message.extend(_check_common_args(args=args))
    if error_message:
        msg = "\n".join(error_message)
        LOGGER.error(msg)
        raise ValueError(msg)
    factory = _make_factory(args=args)
    import_json(factory=factory, json_paths=source_list)


def export(args):
    """
    Run logic associated with exportation subparser.

    :params args: (ArgumentParser, req) Command line args that tell us what
        pattern and database to use.

    :raises ValueError: if there's an issue with flags (bad filetype, etc)
    """
    LOGGER.info('Exporting ids=%s and scalars=%s from database_type=%s '
                'to target=%s.', args.ids, args.scalars, args.database_type, args.target)
    error_message = []
    error_message.extend(_check_common_args(args=args))
    if not args.ids:
        error_message.append('Require one or more record ids to export.')
    if not args.scalars:
        error_message.append('Require one or more scalar names to export.')
    if error_message:
        msg = "\n".join(error_message)
        LOGGER.error(msg)
        raise ValueError(msg)

    utils.export(factory=_make_factory(args=args),
                 id_list=args.ids.split(','),
                 scalar_names=args.scalars.split(','),
                 output_file=args.target,
                 output_type=args.export_type)


def query(args):
    """
    Run logic associated with query subparser.

    :params args: (ArgumentParser, req) Command line args that tell us what
        pattern and database to use.

    :raises ValueError: if there's an issue with flags (bad filetype, etc)
    """
    LOGGER.info('Querying %s.', args.database_type)
    error_message = []
    error_message.extend(_check_common_args(args=args))
    if not args.raw and not args.scalar and not args.uri:
        error_message.append("You must specify a query type!")
    elif args.raw and (args.scalar or args.uri or args.id):
        error_message.append("Raw queries don't support additional query "
                             "flags (--scalar, --uri, or --id)")
    if error_message:
        msg = "\n".join(error_message)
        LOGGER.error(msg)
        raise ValueError(msg)

    # Raw queries are a special case that completely bypasses the DAO.
    if args.raw:
        if args.database_type == "cass":
            LOGGER.debug('Executing raw query on cassandra: %s', args.raw)
            print([str(x) for x in
                   Cluster(args.database)
                   .connect(args.cass_keyspace)
                   .execute(args.raw)])
        elif args.database_type == "sql":
            LOGGER.debug('Executing raw query on sql: %s', args.raw)
            print([str(x) for x in
                   connect(args.database)
                   .cursor()
                   .execute(args.raw)])

    # For all non-raw queries, we go through the DAO.
    record_dao = _make_factory(args=args).create_record_dao()
    matches = []
    if args.scalar:
        data_args = parse_data_string(args.scalar)
        matches = list(record_dao.get_given_data(**data_args))
    if args.uri:
        accepted_ids_list = matches if args.scalar else None
        matches = record_dao.get_given_document_uri(
            uri=args.uri, accepted_ids_list=accepted_ids_list, ids_only=True)
    if args.id:
        print([x for x in matches])
    else:
        print([x.raw for x in record_dao.get(matches)])


def compare_records(args):
    """
    Run logic for comparing records.

    :params args: (ArgumentParser, req) Command line args that tell us
        what pattern and database to use.

    :raises ValueError: if there's an issue with flags (bad record id)
    """
    LOGGER.info('Comparing %s to %s.', args.id_one, args.id_two)
    error_message = []
    error_message.extend(_check_common_args(args=args))
    if error_message:
        msg = "\n".join(error_message)
        LOGGER.error(msg)
        raise ValueError(msg)
    record_dao = _make_factory(args=args).create_record_dao()
    try:
        record_one = record_dao.get(args.id_one)
        try:
            record_two = record_dao.get(args.id_two)
            sina.cli.diff.print_diff_records(record_one=record_one,
                                             record_two=record_two)
        except NoResultFound:
            print('Could not find record with id <{}>. Check id and '
                  'database.'.format(args.id_two))
    except NoResultFound:
        print('Could not find record with id <{}>. Check id and '
              'database.'.format(args.id_one))


def _check_common_args(args):
    """
    Check common arguments for issues.

    :params args: (ArgumentParser, req) Command line args that tell us database to use.
    :returns: A list of error messages.
    """
    error_message = []
    if not args.database_type:
        args.database_type = _get_guessed_database_type(args.database)
        if not args.database_type:
            error_message.append("{flag} not provided and unable "
                                 "to guess type from source. Please "
                                 "specify {flag}. Currently, "
                                 "only cass and sql are supported for "
                                 "ingesting."
                                 .format(flag=COMMON_OPTION_DATABASE_TYPE))
        elif args.database_type not in ('cass', 'sql'):
            error_message.append("Can only {} when connecting to sql files or Cassandra."
                                 .format(args.subparser_name))
    if args.database_type == 'cass':
        error_message.extend(_validate_cassandra_args(args))
    return error_message


def version():
    """
    Return the version of the package.

    :returns: The version of Sina.
    """
    LOGGER.debug('Getting version.')
    return __VERSION__


def _get_guessed_database_type(database_name):
    """
    Try to guess the type of backend in use.

    :param database_name: The name of the database we're guessing the type of

    :returns: A string representing database type, None if it can't be guessed
    """
    LOGGER.debug('Attempting to guess the backend type based on name: %s', database_name)
    filetype_check = database_name.split('.')
    # First we check if it contains a period. Both IPs and files with
    # extensions should have periods--if we don't have either, we can't guess.
    if len(filetype_check) > 1:
        # Whatever follows the final period is what we're interested in.
        identifier = filetype_check[-1]
        file_extension = identifier.lower()
        if file_extension in ("sqlite", "sql", "sqlite3"):
            LOGGER.debug('Found sql.')
            return "sql"
        if file_extension in ["json"]:
            LOGGER.debug('Found json.')
            return "json"
        if file_extension in ["csv"]:
            LOGGER.debug('Found csv.')
            return "csv"
    LOGGER.debug('Unable to guess database type.')
    return None


def _make_factory(args):
    """
    Create a factory fitting the requirements expressed by args.

    :param args: The arguments passed into the parser.

    :returns: a factory satisfying the provided arguments
    """
    LOGGER.debug('Making %s factory.', args.database_type)
    if args.database_type == "cass":
        return cass.DAOFactory(node_ip_list=[args.database],
                               keyspace=args.cass_keyspace)
    elif args.database_type == "sql":
        return sql.DAOFactory(args.database)
    else:
        # Note: database_type should be constrained to a list of choices
        # by the ArgumentParser. If you're seeing this error, then it's likely
        # you've either modified the args or the choices are broken. Should not
        # be caused by user error.
        msg = "Unrecognized database type: {}".format(args.database_type)
        LOGGER.error(msg)
        raise ValueError(msg)


def main():
    """
    Begin main CLI process.

    Make calls to set up the command line argument parser, parse command line
    arguments, and then execute based on those args.
    """
    parser = setup_arg_parser()
    # Python2 workaround for Argparse's lack of truly optional subcommands
    if len(sys.argv) > 1 and sys.argv[1] in ('-v', '--version'):
        print(version())
        return
    args = parser.parse_args()
    setup_logging(args)
    LOGGER.debug('Logging successfully set up.')
    LOGGER.debug('About to execute with args: %s', args)
    # Execute based on our CLI args
    try:
        if args.subparser_name == 'ingest':
            ingest(args)
        elif args.subparser_name == 'export':
            export(args)
        elif args.subparser_name == 'query':
            query(args)
        elif args.subparser_name == 'compare':
            compare_records(args)
        else:
            msg = 'No supported args given: {}'.format(args)
            LOGGER.error(msg)
            raise ValueError(msg)
    except (IOError, ValueError, TypeError) as context:
        LOGGER.exception('Problem with CLI command: %s, full stacktrace written to log', context)
    LOGGER.info('Exiting program.')


if __name__ == '__main__':
    main()
