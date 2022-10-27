"""Start a previously stopped EC2 on-demand instance."""
import logging
import sys

import boto3

from . import REQUIRED_ARGS
from .parser import add_basic_args, add_general_args, add_env_args
from .common import ec2_ip, get_ip, set_boto_session

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
    add_env_args(parser)

    REQUIRED_ARGS['start'] = ['name',
                              'service',
                              'forge_env']


def start_fleet(n_list, config):
    """starts each fleet in n_list

    Parameters
    ----------
    n_list : list
        List of fleet names
    config : dict
        Forge configuration data
    """
    profile = config.get('aws_profile')
    region = config.get('region')
    set_boto_session(region, profile)
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


def start(config):
    """start a stopped on-demand EC2 instance

    Parameters
    ----------
    config : dict
        Forge configuration data
    """
    name = config['name']
    date = config.get('date', '')
    service = config['service']
    market = config.get('market')

    n_list = []
    if service == "cluster":
        if market[0] == 'spot':
            logger.error('Master is a spot instance; you cannot start a spot instance')
        elif market[0] == 'on-demand':
            n_list.append(f'{name}-{market[0]}-{service}-master-{date}')

        if market[-1] == 'spot':
            logger.error('Worker is a spot fleet; you cannot start a spot fleet')
        elif market[-1] == 'on-demand':
            n_list.append(f'{name}-{market[0]}-{service}-worker-{date}')
    elif service == "single":
        if market[0] == 'spot':
            logger.error('The instance is a spot instance; you cannot start a spot instance')
        elif market[0] == 'on-demand':
            n_list.append(f'{name}-{market[0]}-{service}-{date}')
    start_fleet(n_list, config)
