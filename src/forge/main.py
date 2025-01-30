import argparse
import logging
import sys

import boto3
from . import __version__, DEFAULT_ARG_VALS
from .engine import cli_engine, engine
from .create import create, cli_create
from .destroy import cli_destroy, destroy
from .rsync import cli_rsync, rsync
from .run import cli_run, run
from .ssh import cli_ssh, ssh
from .configuration import Configuration
from .configure import cli_configure, configure
from .stop import cli_stop, stop
from .start import cli_start, start
from .cleanup import cli_cleanup, cleanup

available_subcommands = [
    cli_create,
    cli_destroy,
    cli_rsync,
    cli_run,
    cli_engine,
    cli_configure,
    cli_ssh,
    cli_stop,
    cli_start,
    cli_cleanup
]


def print_version():
    """Print forge currently installed version to the screen."""
    print(f'Forge v{__version__}')


def set_logger(name=None, level=DEFAULT_ARG_VALS['log_level']):
    """Configure the desired logger with nice defaults."""
    # Get the logger
    _logger = logging.getLogger(name)

    # Set the level
    _logger.setLevel(level)

    # create formatter
    formatter = logging.Formatter(
        fmt = '%(asctime)s -- %(levelname)s -- %(message)s',
        datefmt = '%a %b %d %H:%M:%S %Y'
    )

    # create console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    _logger.addHandler(ch)

    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

    return _logger


def execute(config: Configuration):
    """execute the proper Forge job

    Parameters
    ----------
    config : Configuration
        Forge configuration data

    Returns
    -------
    int
        The exit status of the job
    """
    status = 0
    job = config['job']
    if job == 'create':
        create(config)
    elif job == 'destroy':
        destroy(config)
    elif job == 'rsync':
        status = rsync(config)
    elif job == 'run':
        status = run(config)
    elif job == 'engine':
        status = engine(config)
    elif job == 'configure':
        configure()
    elif job == 'ssh':
        ssh(config)
    elif job == 'stop':
        stop(config)
    elif job == 'start':
        start(config)
    elif job == 'cleanup':
        cleanup(config)

    if job in {'run', 'engine'}:
        if not status and config.destroy_after_success:
            logger.info('destroy_after_success parameter True, running forge destroy...')
            destroy(config)
    return status


def main():
    """Forge entrypoint."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False
    )
    # TODO: maybe convert this to lowercase (version) and rename the other version to spark_version?
    parser.add_argument(
        '-V', '--version',
        dest='forge_version', action='store_true',
        help='Print the version number of Forge.'
    )
    subparsers = parser.add_subparsers(help='job for forge to do', dest='job')
    for sub in available_subcommands:
        sub(subparsers)
    args = vars(parser.parse_args())
    if args.pop('forge_version'):
        print_version()
        return 0

    # Set initial log level
    logger.setLevel(args['log_level'] or DEFAULT_ARG_VALS['log_level'])

    if args['job'] != 'configure':
        config: Configuration = Configuration.load_config(args)

        if not config.validate():
            sys.exit(1)

        config.log_level = config.log_level or DEFAULT_ARG_VALS['log_level']
        logger.setLevel(config.log_level)

        # Set default boto3 session
        if config.aws_profile:
            boto3.setup_default_session(profile_name=config.aws_profile, region_name=config.region)
        else:
            boto3.setup_default_session(region_name=config.region)
    else:
        config = args

    logger.debug('config is %s', config)

    return execute(config)


logger = set_logger()

if __name__ == '__main__':
    sys.exit(main())
