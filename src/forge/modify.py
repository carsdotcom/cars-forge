"""EC2 Fleet modification"""
import datetime
import logging
import sys

import boto3
import botocore.exceptions

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .common import get_nlist, ec2_ip
from .configuration import Configuration
from .create import get_instance_details
from .parser import add_basic_args, add_modify_args, add_env_args, add_general_args, add_action_args

logger = logging.getLogger(__name__)


def cli_modify(subparsers):
    """adds modify parser to subparser

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser('modify', description='Modify EC2 Fleets')
    add_basic_args(parser)
    add_general_args(parser)
    add_modify_args(parser)
    add_action_args(parser, suppress=True)
    add_env_args(parser)

    REQUIRED_ARGS['modify'] = ['name',
                               'service',
                               'forge_env']


def generate_fleet_template(n, config: Configuration, instance_details):
    """generate the EC2 fleet override launch template

    Parameters
    ----------
    n : str
        Fleet name
    config : Configuration
        Forge configuration data
    instance_details: dict
        EC2 instance details for create_fleet

    Returns
    -------
    dict
        EC2 fleet template
    """
    ami = config['ami']
    disk = config.disk
    disk_device_name = config.disk_device_name
    excluded_ec2s = config.excluded_ec2s
    gpu = config.gpu_flag or False


    kwargs = {}

    if instance_details.get('instance_type') or instance_details.get('override_instance_stats'):
        kwargs['TargetCapacitySpecification'] = {
            'TotalTargetCapacity': instance_details['total_capacity'],
        }

    launch_template_config = {
        'LaunchTemplateSpecification': {'LaunchTemplateName': n, 'Version': '1'},
        'Overrides': [{}]
    }

    if instance_details.get('instance_type'):
        launch_template_config['Overrides'][0]['InstanceType'] = instance_details['instance_type']
    elif instance_details.get('override_instance_stats'):
        if gpu:
            instance_details['override_instance_stats']['AcceleratorTypes'] = ['gpu']
        if excluded_ec2s:
            instance_details['override_instance_stats']['ExcludedInstanceTypes'] = excluded_ec2s

        launch_template_config['Overrides'][0]['InstanceRequirements'] = instance_details['override_instance_stats']
        #kwargs['TargetCapacitySpecification']['TargetCapacityUnitType'] = instance_details['capacity_unit']

    if ami:
        launch_template_config['Overrides'][0]['ImageId'] = ami
    if disk:
        launch_template_config['Overrides'][0]['BlockDeviceMappings'] = [{
            'DeviceName': disk_device_name,
            'Ebs': {
                'DeleteOnTermination': True,
                'VolumeSize': disk,
                'VolumeType': 'gp3'
            }
        }]

    if kwargs:
        kwargs['LaunchTemplateConfigs'] = [launch_template_config]

    return kwargs


def get_fleet_details(fleet_id):
    """get fleet details

    Parameters
    ==========
    fleet_id : str
        ID of the fleet to get information for

    Returns
    -------
    dict
        Response from Boto3 describe_fleets
    """
    client = boto3.client('ec2')
    response = client.describe_fleets(FleetIds=[fleet_id])
    return response['Fleets'][0]


def fleet_request(kwargs):
    """modifies the fleet

    Parameters
    ----------
    kwargs : dict
        Arguments to pass to Boto3 create_fleet

    Returns
    -------
    dict
        Response from Boto3 create_fleet
    """
    client = boto3.client('ec2', region_name=kwargs.pop('region'))
    response = client.modify_fleet(**kwargs)
    return response


def search_and_modify(config, task_list):
    """check for running instances and modify if found

    Parameters
    ----------
    config : Configuration
        Forge configuration data
    task_list: list[str]
        List of tasks to run
    """
    region = config.region
    name = config.name
    date = config.date or ''
    markets = config.market or DEFAULT_ARG_VALS['market']
    if isinstance(markets, str):
        markets = [markets]

    for task in task_list:
        market = markets[-1] if task == 'cluster-worker' else markets[0]
        n = f'{name}-{market}-{task}-{date}'

        detail = ec2_ip(n, config)

        if len(detail) == 1:
            e = detail[0]
            if e['state'] in ['running', 'stopped', 'stopping', 'pending']:
                fleet_id = e['fleet_id']
                fleet_details = get_fleet_details(fleet_id[0])

                worker_units = True
                if fleet_details['TargetCapacitySpecification']['TargetCapacityUnitType'] == 'memory-mib':
                    worker_units = False

                instance_details = get_instance_details(config, [task], worker_units=worker_units)
                kwargs = generate_fleet_template(n, config, instance_details[task])

                if kwargs:
                    kwargs['ExcessCapacityTerminationPolicy'] = 'termination'
                    kwargs['FleetId'] = fleet_id[0]
                    kwargs['region'] = region

                    try:
                        response = fleet_request(kwargs)
                        logger.debug(response)
                    except botocore.exceptions.ClientError as error:
                        if error.response['Error']['Code'] == 'InvalidParameter':
                            logger.error('Cannot switch between using an instance type and using instance requirements')
                        else:
                            logger.error(error)

                        continue

                    if response['Return']:
                        logger.info('Fleet request for %s modified', n)
                    else:
                        logger.error('Fleet request for %s was not modified', n)


def modify(config: Configuration):
    """modify and existing EC2 fleet

    Parameters
    ----------
    config : Configuration
        Forge configuration data
    """
    service = config.service
    task_list = ['single']

    if service == 'cluster':
        task_list = ['cluster-master', 'cluster-worker']

    logger.warning('The modify command is experimental; fleet modifications may be unpredictable.')

    search_and_modify(config, task_list)
