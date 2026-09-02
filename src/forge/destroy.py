"""EC2 instance destruction."""
import logging
import json
import sys

from datetime import datetime, timezone, timedelta

import boto3

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .parser import add_basic_args, add_general_args, add_env_args, add_job_args, add_action_args
from .common import ec2_ip, get_ec2_pricing, get_ami_spec
from .configuration import Configuration

logger = logging.getLogger(__name__)


def cli_destroy(subparsers):
    """adds destroy parser to subparser

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser('destroy', description='Destroy EC2')
    add_basic_args(parser)
    add_general_args(parser)
    add_job_args(parser, suppress=True)
    add_action_args(parser, suppress=True)
    add_env_args(parser)

    REQUIRED_ARGS['destroy'] = ['name',
                                'service',
                                'forge_env']


def pricing(detail, config: Configuration, market):
    """get pricing info for fleet from AWS

    Parameters
    ----------
    detail : list
        A list of AWS EC2 instance details
    config : Configuration
        Forge configuration data
    market : {'spot', 'on-demand'}
        The market the instance was created in
    """
    logger.debug('config is %s', config)

    total_cost = 0
    now = datetime.now(timezone.utc)
    max_dif = timedelta()
    for e in detail:
        if e['state'] == 'running':
            launch_time = e['launch_time']
            dif = (now - launch_time)
            if dif > max_dif:
                max_dif = dif
            ec2_type = e['instance_type']
            config.aws_az = e['az']
            total_cost = get_ec2_pricing(ec2_type, market, config)

    if total_cost > 0:
        time_d_float = max_dif.total_seconds()
        hours, rem = divmod(int(time_d_float), 3600)
        minutes = rem // 60
        cost = round(total_cost * (time_d_float / 60 / 60), 2)
        time_diff = f"{hours} hours and {minutes} minutes"
        logger.info('Total run time was %s. Total cost was $%s', time_diff, cost)


def template_destroy(n, ami_spec):
    """

    Parameters
    ----------
    n : str
        Fleet name
    ami_spec : dict
        Forge AMI data
    """
    client = boto3.client('ec2')

    for arch in ami_spec.keys():
        arch_n = f'{n}-{arch}'

        try:
            response = client.delete_launch_template(LaunchTemplateName=arch_n)
            debug_info = list(response.values())[0]
            logger.debug('Deleted template %s %s', debug_info["LaunchTemplateId"],
                         debug_info["LaunchTemplateName"])
            logger.debug('Template %s is destroyed', arch_n)
        except:
            logger.debug('Template %s not found', arch_n)


def fleet_destroy(fleet_id):
    """sends the cancel fleet request or terminate instance to AWS

    Parameters
    ----------
    n : str
        Fleet name
    fleet_id : str
        Fleet ID
    config : Configuration
        Forge configuration data
    ami_spec : dict
        Forge AMI data
    """
    client = boto3.client('ec2')

    response = client.delete_fleets(FleetIds=fleet_id, TerminateInstances=True)
    logger.debug('Deleted %d fleets successfully and %d fleets unsuccessfully',
                 len(list(response["SuccessfulFleetDeletions"])), len(list(response["UnsuccessfulFleetDeletions"])))


def find_and_destroy(n, config: Configuration, ami_spec):
    """searches for fleets matching n and destroys them

    Parameters
    ----------
    n : str
        Fleet name
    config : Configuration
        Forge configuration data
    ami_spec : dict
        Forge AMI data
    """
    logger.info('Finding %s instances', n)
    detail = ec2_ip(n, config)
    logger.debug(detail)
    market = config.market_failover or DEFAULT_ARG_VALS['market']
    market = market[-1] if 'cluster-worker' in n else market[0]
    pricing(detail, config, market)

    template_destroy(n, ami_spec)
    for i in detail:
        fleet_destroy(i.get('fleet_id'))

    logger.info('Fleet %s destroyed', n)


def destroy(config: Configuration):
    """finds and destroys forge instances based on market name and service

    Parameters
    ----------
    config : Configuration
        Forge configuration data
    """
    name = config.name
    date = config.date or ''
    service = config.service
    market = config.market or DEFAULT_ARG_VALS['market']

    try:
        ami_spec = get_ami_spec(config)
    except (KeyError, ValueError):
        sys.exit(1)

    if service == 'single':
        n = f'{name}-{market[0]}-{service}-{date}'
        find_and_destroy(n, config, ami_spec)

    if service == 'cluster':
        n = f'{name}-{market[0]}-{service}-master-{date}'
        find_and_destroy(n, config, ami_spec)
        n = f'{name}-{market[-1]}-{service}-worker-{date}'
        find_and_destroy(n, config, ami_spec)
