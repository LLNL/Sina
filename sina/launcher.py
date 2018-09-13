"""
Launcher.py provides command-line functionality for Sina.

Internally, it handles parsing args and setting up logging.


Example::

    $sina -f <some_string> -d <some_db>

Returns a list of filepaths from some_db containing some_string.

"""
import logging
import inspect
import sys
import os
from argparse import ArgumentParser, RawTextHelpFormatter

from cassandra.cluster import Cluster
from sqlite3 import connect

from sina import utils
from sina.utils import import_many_jsons, import_json, parse_scalars, create_file
import sina.datastores.cass as cass
import sina.datastores.sql as sql

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
    return parser


def add_ingest_subparser(subparsers):
    """Add subparser for ingesting Mnoda-format contents into backends."""
    parser_ingest = subparsers.add_parser(
        'ingest', help='ingest complete Mnoda-type information and insert into'
                       ' a specified database. See "sina ingest -h" for more '
                       'information.')
    required = parser_ingest.add_argument_group("required arguments")
    required.add_argument(COMMON_SHORT_OPTION_DATABASE,
                          COMMON_OPTION_DATABASE, type=str,
                          required=True, dest='database',
                          help='URI of database to ingest into.\n'
                          'For Cassandra: <IP>[:port], use {}'
                          ' to specify keyspace. '
                          'For SQLite: <filepath>'
                          .format(COMMON_OPTION_CASSANDRA_DEST))
    # TODO: If use case is Localhost and/or RZSonar, might make sense to have
    # keyspace be the database arg and provide IP/port the special way.
    # This isn't out of line with cql, which will start fine without an
    # ip/port provided (assumes Localhost) and can take a keyspace.
    parser_ingest.add_argument(COMMON_OPTION_CASSANDRA_DEST, type=str,
                               dest='cass_keyspace',
                               help='If using a Cassandra database, the '
                               'keyspace to use. Ignored by other database '
                               'types.')
    # TODO Expand the 'choices' args below as we add more supported backends.
    parser_ingest.add_argument(COMMON_OPTION_DATABASE_TYPE, type=str,
                               dest='database_type',
                               help='Type of database to ingest into. Sina '
                               'will try to infer this from {} if '
                               'that is provided, but {} is not.'
                               .format(COMMON_OPTION_DATABASE,
                                       COMMON_OPTION_DATABASE_TYPE),
                               choices=['cass', 'sql'])
    parser_ingest.add_argument('source', type=str,
                               help='The URI or list of URIs to ingest from. '
                               'Data must be compliant with the Mnoda schema, '
                               'and can be in any of the supported backends. '
                               'Comma-separated.')
    # TODO: What if they supply a folder? We'll probably want to support that.
    # I think they should only be able to provide one source-type. They can
    # pipe `find` in if they want to do something fancy--if we try to parse
    # something from a folder and fail because it's the wrong backend, it's
    # time to fail and complain.
    parser_ingest.add_argument('--source-type', type=str,
                               help='The type of the URIs being ingested. Sina '
                               'will try to infer this from --source if '
                               '--source-type is not provided. All URIs being '
                               'ingested in one command must share a type.',
                               choices=['json'])


def add_export_subparser(subparsers):
    """Add subparser for exporting from backends into various formats."""
    parser_export = subparsers.add_parser(
        'export', help='export from a Mnoda-compliant backend into various, '
                       'subset-like formats. Allows for exporting '
                       'information that is not importable with this tool; if '
                       'you want to produce complete Mnoda data, try '
                       '`sina import`ing to JSON or csv. See "sina export -h" '
                       'for more information.'
                       'Currently, the only supported export format is csv.')
    required = parser_export.add_argument_group("required arguments")
    required.add_argument(COMMON_SHORT_OPTION_DATABASE,
                          COMMON_OPTION_DATABASE, type=str,
                          required=True, dest='database',
                          help='URI of database to export from.\n'
                          'For Cassandra: <IP>[:port], use {}'
                          ' to specify keyspace. '
                          'For SQLite: <filepath>'
                          .format(COMMON_OPTION_CASSANDRA_DEST))
    parser_export.add_argument(COMMON_OPTION_CASSANDRA_DEST, type=str,
                               dest='cass_keyspace',
                               help='If using a Cassandra database, the '
                               'keyspace to use. Ignored by other database '
                               'types.')
    parser_export.add_argument(COMMON_OPTION_DATABASE_TYPE, type=str,
                               dest='database_type',
                               help='Type of database to export from. Sina '
                               'will try to infer this from {} if '
                               'that is provided, but {} is not.'
                               .format(COMMON_OPTION_DATABASE,
                                       COMMON_OPTION_DATABASE_TYPE),
                               choices=['cass', 'sql'])
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
        'query', help='perform a query against a Mnoda-compliant backend. '
                      'See "sina query -h" for more information.')
    required = parser_query.add_argument_group("required arguments")
    required.add_argument(COMMON_SHORT_OPTION_DATABASE,
                          COMMON_OPTION_DATABASE, type=str,
                          dest='database', required=True,
                          help='URI of database to query.\n'
                          'For Cassandra: <IP>[:port], use {}'
                          ' to specify keyspace. '
                          'For SQLite: <filepath>'
                          .format(COMMON_OPTION_CASSANDRA_DEST))
    parser_query.add_argument(COMMON_OPTION_CASSANDRA_DEST, type=str,
                              dest='cass_keyspace',
                              help='If using a Cassandra database, the '
                              'keyspace to use. Ignored by other database '
                              'types.')
    parser_query.add_argument(COMMON_OPTION_DATABASE_TYPE, type=str,
                              dest='database_type',
                              help='Type of database to query. Sina '
                              'will try to infer this from {} if '
                              'that is provided, but {} is not.'
                              .format(COMMON_OPTION_DATABASE,
                                      COMMON_OPTION_DATABASE_TYPE),
                              choices=['cass', 'sql'])
    # TODO: This is the prior formatting. But if do comma-separated and hit
    # something that doesn't look like an entire scalar, it's either a range
    # or an error, and it should be easy enough to tell the difference. Given
    # that comma-separated is the standard, might be worth changing.
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
    # TODO: Escaping %
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
                              'Mnoda internal schema and backend queries. Not '
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
    fh = logging.FileHandler(logpath)
    fh.setLevel(loglevel)
    fh.setFormatter(formatter)
    ROOTLOGGER.addHandler(fh)

    if args.stdout:
        # Add the StreamHandler
        sh = logging.StreamHandler()
        sh.setLevel(loglevel)
        sh.setFormatter(formatter)
        ROOTLOGGER.addHandler(sh)

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
    LOGGER.info('Ingesting source_list={} into database={}, database_type={}.'
                .format(args.source, args.database, args.database_type))
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
        elif args.source_type not in ('json'):
            error_message.append("Currently, ingesting is only supported when "
                                 "using json files as the source.")
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
            error_message.append("Currently, ingesting is only supported when "
                                 "using sql files or Cassandra as the "
                                 "destination.")
    if args.database_type == 'cass' and (not args.cass_keyspace):
                    error_message.append("{} not provided. In "
                                         "the future, it will be possible to "
                                         "set a default. For now, please "
                                         "specify it to continue!"
                                         .format(COMMON_OPTION_CASSANDRA_DEST))
    if error_message:
        msg = "\n".join(error_message)
        LOGGER.error(msg)
        raise ValueError(msg)
    factory = _make_factory(args=args)
    if len(source_list) > 1:
        import_many_jsons(factory=factory, json_list=source_list)
    else:
        import_json(factory=factory, json_path=source_list[0])


def export(args):
    """
    Run logic associated with exportation subparser.

    :params args: (ArgumentParser, req) Command line args that tell us what
        pattern and database to use.

    :raises ValueError: if there's an issue with flags (bad filetype, etc)
    """
    LOGGER.info('Exporting ids={} and scalars={} from database_type={} '
                'to target={}.'.format(args.ids,
                                       args.scalars,
                                       args.database_type,
                                       args.target))
    error_message = []
    if not args.database_type:
        args.database_type = _get_guessed_database_type(args.database)
        if not args.database_type:
            error_message.append("{flag} not provided and unable "
                                 "to guess type from source. Please "
                                 "specify {flag}. Currently, "
                                 "only cass and sql are supported for "
                                 "exporting from."
                                 .format(flag=COMMON_OPTION_DATABASE_TYPE))
    args.database_type = args.database_type.lower()
    if args.database_type not in ('cass', 'sql'):
        error_message.append("Currently, exporting is only supported when "
                             "using sql files or Cassandra as the "
                             "database to export from.")
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

    :returns: a list of matching record raws (ids if --id flag used)

    :raises ValueError: if there's an issue with flags (bad filetype, etc)
    """
    LOGGER.info('Querying {}.'.format(args.database_type))
    error_message = []
    if not args.database_type:
        args.database_type = _get_guessed_database_type(args.database)
        if not args.database_type:
            error_message.append("{flag} not provided and unable "
                                 "to guess type from source. Please "
                                 "specify {flag}. Currently, "
                                 "only cass and sql are supported for "
                                 "querying."
                                 .format(flag=COMMON_OPTION_DATABASE_TYPE))
        elif args.database_type not in ('cass', 'sql'):
            error_message.append("Currently, querying is only supported when "
                                 "querying sql files or Cassandra.")
    if args.database_type == 'cass' and (not args.cass_keyspace):
        error_message.append("{} not provided. In "
                             "the future, it will be possible to "
                             "set a default. For now, please "
                             "specify it to continue!"
                             .format(COMMON_OPTION_CASSANDRA_DEST))
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
            LOGGER.debug('Executing raw query on cassandra: {}'.format(args.raw))
            print([str(x) for x in
                  Cluster(args.database)
                  .connect(args.cass_keyspace)
                  .execute(args.raw)])
        elif args.database_type == "sql":
            LOGGER.debug('Executing raw query on sql: {}'.format(args.raw))
            print([str(x) for x in
                   connect(args.database)
                   .cursor()
                   .execute(args.raw)])

    # For all non-raw queries, we go through the DAO.
    record_dao = _make_factory(args=args).createRecordDAO()
    matches = []
    if args.scalar:
        scalar_range_list = parse_scalars(args.scalar)
        matches = record_dao.get_given_scalars(
                             scalar_range_list=scalar_range_list)
    if args.uri:
        accepted_ids_list = [x.id for x in matches] if args.scalar else None
        matches = record_dao.get_given_document_uri(
                             uri=args.uri, accepted_ids_list=accepted_ids_list)
    # TODO: Not ideal, if we only need the ids we're doing an unnecessary query
    # against the records table, as both scalar and uri queries find ids
    # (but then call get_many()). Easily solved with optargs. But is that
    # against "good sense" for the DAO?
    if args.id:
        print([x.id for x in matches])
    else:
        print([x.raw for x in matches])
    # Return value primarily used for testing
    return matches


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
    LOGGER.debug('Attempting to guess the backend type based on name: {}'
                 .format(database_name))
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
        if file_extension in ("json"):
            LOGGER.debug('Found json.')
            return "json"
        if file_extension in ("csv"):
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
    LOGGER.debug('Making {} factory.'.format(args.database_type))
    if args.database_type == "cass":
        return cass.DAOFactory(node_ip_list=args.database,
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
    LOGGER.debug('About to execute with args: {}'.format(args))
    # Execute based on our CLI args
    try:
        if args.subparser_name == 'ingest':
            ingest(args)
        elif args.subparser_name == 'export':
            export(args)
        elif args.subparser_name == 'query':
            query(args)
        else:
            msg = 'No supported args given: {}'.format(args)
            LOGGER.error(msg)
            raise ValueError(msg)
    except (IOError, ValueError, TypeError) as e:
        msg = ('Problem with CLI command: {}, full stacktrace written to log'
               .format(e))
        LOGGER.exception(msg)
        print(msg)
    LOGGER.info('Exiting program.')


if __name__ == '__main__':
    main()
