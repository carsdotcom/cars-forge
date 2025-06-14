"""EC2 instance destruction."""
import logging
import json

from datetime import datetime, timezone, timedelta

import boto3

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .parser import add_basic_args, add_general_args, add_env_args, add_job_args, add_action_args
from .common import ec2_ip, get_ec2_pricing
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


def fleet_destroy(n, fleet_id, config: Configuration):
    """sends the cancel fleet request or terminate instance to AWS

    Parameters
    ----------
    n : str
        Fleet name
    fleet_id : str
        Fleet ID
    config : Configuration
        Forge configuration data
    """
    client = boto3.client('ec2')

    try:
        response = client.delete_launch_template(LaunchTemplateName=n)
        debug_info = list(response.values())[0]
        logger.debug('Deleted instance %s %s from %s', debug_info["LaunchTemplateId"], debug_info["LaunchTemplateName"],
                     fleet_id[0])
        logger.debug('Template %s is destroyed', n)
    except:
        logger.debug('Template %s not found', n)

    response = client.delete_fleets(FleetIds=fleet_id, TerminateInstances=True)
    logger.debug('Deleted %d fleets successfully and %d fleets unsuccessfully',
                 len(list(response["SuccessfulFleetDeletions"])), len(list(response["UnsuccessfulFleetDeletions"])))


def find_and_destroy(n, config: Configuration):
    """searches for fleets matching n and destroys them

    Parameters
    ----------
    n : str
        Fleet name
    config : Configuration
        Forge configuration data
    """
    logger.info('Finding %s instances', n)
    detail = ec2_ip(n, config)
    logger.debug(detail)
    market = config.market_failover or DEFAULT_ARG_VALS['market']
    market = market[-1] if 'cluster-worker' in n else market[0]
    pricing(detail, config, market)
    for i in detail:
        fleet_destroy(n, i.get('fleet_id'), config)

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

    if service == 'single':
        n = f'{name}-{market[0]}-{service}-{date}'
        find_and_destroy(n, config)

    if service == 'cluster':
        n = f'{name}-{market[0]}-{service}-master-{date}'
        find_and_destroy(n, config)
        n = f'{name}-{market[-1]}-{service}-worker-{date}'
        find_and_destroy(n, config)
