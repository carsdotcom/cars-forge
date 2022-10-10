"""EC2 instance destruction."""
import logging
import json

from datetime import datetime, timezone, timedelta

import boto3

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .parser import add_basic_args, add_general_args, add_env_args
from .common import ec2_ip, set_boto_session, get_ec2_pricing

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
    add_env_args(parser)

    REQUIRED_ARGS['destroy'] = ['name',
                                'service',
                                'forge_env']


def pricing(detail, config, market):
    """get pricing info for fleet from AWS

    Parameters
    ----------
    detail : list
        A list of AWS EC2 instance details
    config : dict
        Forge configuration data
    market : {'spot', 'on-demand'}
        The market the instance was created in
    """
    logger.debug('config is %s', config)
    profile = config.get('aws_profile')
    region = config.get('region')

    set_boto_session(region, profile)

    total_cost = 0
    now = datetime.now(timezone.utc)
    dif = timedelta()
    max_dif = timedelta()
    for e in detail:
        if e['state'] == 'running':
            launch_time = e['launch_time']
            dif = (now - launch_time)
            if dif > max_dif:
                max_dif = dif
            ec2_type = e['instance_type']
            total_cost = get_ec2_pricing(ec2_type, market, config)

    if total_cost > 0:
        time_d_float = max_dif.total_seconds()
        hours, rem = divmod(int(time_d_float), 3600)
        minutes = rem // 60
        cost = round(total_cost * (time_d_float / 60 / 60), 2)
        time_diff = f"{hours} hours and {minutes} minutes"
        logger.info('Total run time was %s. Total cost was $%s', time_diff, cost)


def fleet_destroy(n, fleet_id, config):
    """sends the cancel fleet request or terminate instance to AWS

    Parameters
    ----------
    n : str
        Fleet name
    fleet_id : str
        Fleet ID
    config : dict
        Forge configuration data
    """
    profile = config.get('aws_profile')
    region = config.get('region')

    set_boto_session(region, profile)

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


def find_and_destroy(n, config):
    """searches for fleets matching n and destroys them

    Parameters
    ----------
    n : str
        Fleet name
    config : dict
        Forge configuration data
    """
    logger.info('Finding %s instances', n)
    detail = ec2_ip(n, config)
    logger.debug(detail)
    market = config.get('market', DEFAULT_ARG_VALS['market'])
    market = market[-1] if 'cluster-worker' in n else market[0]
    pricing(detail, config, market)
    for i in detail:
        fleet_destroy(n, i.get('fleet_id'), config)

    logger.info('Fleet %s destroyed', n)


def destroy(config):
    """finds and destroys forge instances based on market name and service

    Parameters
    ----------
    config : dict
        Forge configuration data
    """
    name = config.get('name')
    date = config.get('date', '')
    service = config.get('service')
    market = config.get('market', DEFAULT_ARG_VALS['market'])

    if service == 'single':
        n = f'{name}-{market[0]}-{service}-{date}'
        find_and_destroy(n, config)

    if service == 'cluster':
        n = f'{name}-{market[0]}-{service}-master-{date}'
        find_and_destroy(n, config)
        n = f'{name}-{market[-1]}-{service}-worker-{date}'
        find_and_destroy(n, config)
