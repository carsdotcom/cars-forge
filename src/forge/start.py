"""Start a previously stopped EC2 on-demand instance."""
import logging
import sys

import boto3

from . import REQUIRED_ARGS
from .parser import add_basic_args, add_general_args, add_env_args, add_job_args, add_action_args
from .common import ec2_ip, get_ip, get_nlist
from .configuration import Configuration

logger = logging.getLogger(__name__)


def cli_start(subparsers):
    """adds start parser to subparser

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main

    Returns
    -------
    None
    """
    parser = subparsers.add_parser('start', description='start an on-demand EC2')
    add_basic_args(parser)
    add_general_args(parser)
    add_job_args(parser, suppress=True)
    add_action_args(parser, suppress=True)
    add_env_args(parser)

    REQUIRED_ARGS['start'] = ['name',
                              'service',
                              'forge_env']


def start_fleet(n_list, config: Configuration):
    """starts each fleet in n_list

    Parameters
    ----------
    n_list : list
        List of fleet names
    config : Configuration
        Forge configuration data
    """
    client = boto3.client('ec2')

    details = {n: ec2_ip(n, config) for n in n_list}
    targets = {k: get_ip(v, ('stopped', 'stopping')) for k, v in details.items()}
    if not targets:
        logger.error('Could not find any valid instances to start.')
        sys.exit(1)

    for k, v in targets.items():
        if not v:
            logger.error('Could not find any valid instances to start for %s', k)
            continue

        logger.debug('Instance target details are %s', targets)
        logger.info(f'{k} fleet is now starting.')

        for ec2 in v:
            _, uid = ec2
            client.start_instances(InstanceIds=[uid])


def start(config: Configuration):
    """start a stopped on-demand EC2 instance

    Parameters
    ----------
    config : Configuration
        Forge configuration data
    """
    market = config.market

    if 'spot' in market:
        logger.error('Master or worker is a spot instance; you cannot start a spot instance')
        # sys.exit(1)  # ToDo: Should we change the tests to reflect an exit or allow it to continue?

    config.rr_all = True

    n_list = get_nlist(config)
    start_fleet(n_list, config)
