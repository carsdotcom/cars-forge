"""Run a command on remote EC2, rsync user content, and execute it."""
from . import REQUIRED_ARGS
from .parser import add_basic_args, add_job_args, add_env_args, add_general_args, add_action_args
from .create import create
from .rsync import rsync
from .run import run


def cli_engine(subparsers):
    """add engine parser to subparsers

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser('engine', description='create EC2, rsync content, and execute it')
    add_basic_args(parser)
    add_job_args(parser)
    add_env_args(parser)
    add_general_args(parser)
    add_action_args(parser)

    REQUIRED_ARGS['engine'] = list(set(REQUIRED_ARGS['create'] +
                                       REQUIRED_ARGS['rsync'] +
                                       REQUIRED_ARGS['run'] +
                                       REQUIRED_ARGS['destroy']))


def engine(config):
    """runs the Forge engine command

    Parameters
    ----------
    config : dict
        Forge configuration data

    Returns
    -------
    int
        The exit status for run with 0 for success
    """
    create(config)
    rsync(config)
    status = run(config)
    return status
