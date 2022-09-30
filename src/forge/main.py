import argparse
import logging
import sys

import yaml

from . import __version__, DEFAULT_ARG_VALS, REQUIRED_ARGS
from .common import check_keys, set_config_dir, normalize_config, parse_additional_config
from .engine import cli_engine, engine
from .create import create, cli_create
from .destroy import cli_destroy, destroy
from .rsync import cli_rsync, rsync
from .run import cli_run, run
from .ssh import cli_ssh, ssh
from .configure import cli_configure, configure, check_env_yaml
from .stop import cli_stop, stop
from .start import cli_start, start
from .yaml_loader import load_config
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


def execute(config):
    """execute the proper Forge job

    Parameters
    ----------
    config : dict
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
        rsync(config)
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
        if not status and config.get('destroy_after_success'):
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
    if args['forge_version']:
        print_version()
        return 0

    # Set initial log level
    logger.setLevel(args['log_level'] or DEFAULT_ARG_VALS['log_level'])

    if args['job'] != 'configure':
        if args.get('yaml'):
            config = load_config(args)
        else:
            for i in REQUIRED_ARGS[args['job']]:
                if not args.get(i):
                    logger.error('Missing key "%s" in args', i)
                    sys.exit(1)

            args = normalize_config({k: v for k, v in args.items() if v})
            args['config_dir'] = set_config_dir(args)

            with open(f'{args["config_dir"]}/{args["forge_env"]}.yaml') as handle:
                env_config = check_env_yaml(yaml.safe_load(handle))
                if env_config.get('additional_config'):
                    env_config = parse_additional_config(env_config, env_config.pop('additional_config'))
                env_config = normalize_config(env_config)
                check_keys(args.get('region') or env_config['region'], env_config.get('aws_profile'))
                env_config = {k: v for k, v in env_config.items() if v}
                config = {**DEFAULT_ARG_VALS, **env_config, **args}

        # Reset logging with user-defined level, if set
        logger.setLevel(config['log_level'])
    else:
        config = args
        config['log_level'] = args['log_level'] or DEFAULT_ARG_VALS['log_level']

    logger.debug('config is %s', config)

    return execute(config)


logger = set_logger()

if __name__ == '__main__':
    sys.exit(main())
