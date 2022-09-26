"""EC2 instance destruction."""
import logging
import json

from datetime import datetime, timezone, timedelta

import boto3

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .parser import add_basic_args, add_general_args, add_env_args
from .common import ec2_ip, get_regions, set_boto_session

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
    env = config.get('forge_env')
    profile = config.get('aws_profile')
    az = config.get('aws_az')
    region = config.get('region')

    set_boto_session(region, profile)

    ec2_client = boto3.client('ec2')
    pricing_client = boto3.client('pricing', region_name='us-east-1')
    total_spot_cost = 0
    total_on_demand_cost = 0
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
            ec2 = e['instance_type']
            if market == 'spot':
                describe_result = ec2_client.describe_spot_price_history(
                    StartTime=datetime.utcnow(),
                    ProductDescriptions=['Linux/UNIX (Amazon VPC)'],
                    AvailabilityZone=az,
                    InstanceTypes=[ec2]
                )
                spot_price = float(describe_result['SpotPriceHistory'][0]['SpotPrice'])
                total_cost = total_cost + spot_price
                total_cost = round(total_cost, 2)
            elif market == 'on-demand':
                long_region = get_regions()[region]
                op_sys = 'Linux'
                filters = [
                    {'Field': 'tenancy', 'Value': 'shared', 'Type': 'TERM_MATCH'},
                    {'Field': 'operatingSystem', 'Value': op_sys, 'Type': 'TERM_MATCH'},
                    {'Field': 'preInstalledSw', 'Value': 'NA', 'Type': 'TERM_MATCH'},
                    {'Field': 'location', 'Value': long_region, 'Type': 'TERM_MATCH'},
                    {'Field': 'capacitystatus', 'Value': 'Used', 'Type': 'TERM_MATCH'},
                    {'Field': 'instanceType', 'Value': ec2, 'Type': 'TERM_MATCH'}
                ]
                response = pricing_client.get_products(ServiceCode='AmazonEC2', Filters=filters)
                results = response['PriceList']
                product = json.loads(results[0])
                instance = (product['product']['attributes']['instanceType'])
                od = product['terms']['OnDemand']
                price = float(
                    od[list(od)[0]]['priceDimensions'][list(od[list(od)[0]]['priceDimensions'])[0]]['pricePerUnit'][
                        'USD'])
                ip = [instance, price]
                on_demand_price = float(ip[1])
                total_cost = total_cost + on_demand_price
                total_cost = round(total_cost, 2)

    if total_cost > 0:
        time_d_float = max_dif.total_seconds()
        d = {"days": max_dif.days}
        d['hours'], rem = divmod(int(max_dif.total_seconds()), 3600)
        d["minutes"], d["seconds"] = divmod(rem, 60)
        cost = round(total_cost * (time_d_float / 60 / 60), 2)
        time_diff = "{hours} hours and {minutes} minutes".format(**d)
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
