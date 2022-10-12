"""EC2 instance creation."""
import base64
import logging
import sys
import os
import time
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .parser import add_basic_args, add_job_args, add_env_args, add_general_args
from .common import (ec2_ip, destroy_hook, set_boto_session,
                     user_accessible_vars, FormatEmpty, get_ec2_pricing)
from .destroy import destroy

logger = logging.getLogger(__name__)


def cli_create(subparsers):
    """adds create parser to subparser

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser('create', description='Create EC2')
    add_basic_args(parser)
    add_job_args(parser)
    add_env_args(parser)
    add_general_args(parser)

    REQUIRED_ARGS['create'] = ['name',
                               'service',
                               'aws_role',
                               'forge_env']


def fleet_request(kwargs):
    """creates the fleet

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
    response = client.create_fleet(**kwargs)
    return response


def get_fleet_error(client, fleet_id, create_time=None):
    """Get the first error message of a fleet.

    This is meant to be used to retrieve details of a fleet that could not be
    fulfilled.

    Parameters
    ----------
    client : Boto3.client
        The client used to get the instance data
    fleet_id : str
        ID of fleet to get error details for.
    create_time : datetime
        Optional fleet creation time. If `None`, will look for fleet starting
        from 1 hour before current time.

    Returns
    -------
    str
        Error description or empty string if fleet is not found or did not error
        out.
    """
    if create_time is None:
        start_time = datetime.utcnow() - timedelta(hours=1)
    else:
        # Add a buffer to start time to account for potential network delays
        start_time = create_time - timedelta(minutes=30)

    try:
        history = client.describe_fleet_history(
            FleetId=fleet_id, StartTime=start_time
        )
    except ClientError:
        return ''

    for event in history.get('HistoryRecords', []):
        if event.get('EventType', '') == 'error':
            # Typically the last error message just says the request is going to
            # ignored for a long while which is not very informative, so we
            # ignore that one.
            event_info = event.get('EventInformation', {})
            if event_info.get('EventSubType', '') != 'allLaunchSpecsTemporarilyBlacklisted':
                return event_info.get('EventDescription', '')

    return ''


def get_status(client, ec2_id):
    """get the string status code of an EC2 instance

    Parameters
    ----------
    client : Boto3.client
        The client used to get the instance data
    ec2_id : str
        The EC2 instance ID to check

    Returns
    -------
    str
        Status of the EC2 instance
    """
    # Gracefully handle non-existent instances
    try:
        response = client.describe_instance_status(InstanceIds=[ec2_id])
    except ClientError:
        return 'invalid-instance'  # Not an official status but it works for us

    # If the statuses list is empty, instance has been created but initialization
    # has not yet started
    try:
        status = response['InstanceStatuses'][0]['InstanceStatus']['Status']
    except (KeyError, IndexError):
        return 'no-status'

    return status


def create_status(n, request, config):
    """create the console status messages for Forge

    Parameters
    ----------
    n : str
        Fleet name
    request : dict
        Response data from Boto3 create_fleet
    config : dict
        Forge configuration data
    """
    profile = config.get('aws_profile')
    region = config.get('region')
    destroy_flag = config.get('destroy_after_failure')

    set_boto_session(region, profile)

    client = boto3.client('ec2')

    logger.info('Creating Fleet... - 0s elapsed')
    time.sleep(10)
    t = 10
    logger.info('Creating... - %ds elapsed', t)

    fleet_id = request.get('FleetId')
    fleet_description = client.describe_fleets(FleetIds=[fleet_id])
    fleet_details = fleet_description.get('Fleets', [{}])[0]
    current_status = fleet_details.get('ActivityStatus')
    create_time = fleet_details.get('CreateTime')
    time_without_spot = 0
    while current_status != 'fulfilled':
        if current_status == 'pending_fulfillment':
            time.sleep(10)
            t += 10
            logger.info('Creating... - %ds elapsed', t)
        else:
            if time_without_spot == 70:
                logger.error('Could not create fleet request. Last status: %s.', current_status)
                if destroy_flag:
                    destroy(config)
                error_details = get_fleet_error(client, fleet_id, create_time)
                logger.error('Last status details: %s', error_details)
                sys.exit(1)
            time.sleep(10)
            t += 10
            time_without_spot += 10
            logger.info('Searching... - %ds elapsed', t)
        fleet_description = client.describe_fleets(FleetIds=[fleet_id])
        current_status = fleet_description.get('Fleets', [{}])[0].get('ActivityStatus')

    logger.info('Fleet fulfilled.')

    ec2_id_list = []
    time_without_instance = 0
    list_len = 0
    while list_len == 0:
        time.sleep(10)
        t += 10
        time_without_instance += 10
        if time_without_instance == 70:
            logger.error('The EC2 spot instance failed to start, please try again.')
            if destroy_flag:
                destroy(config)
            sys.exit(1)
        logger.info('Finding EC2... - %ds elapsed', t)
        fleet_request_configs = client.describe_fleet_instances(FleetId=fleet_id)
        active_instances_list = fleet_request_configs.get('ActiveInstances')
        for ec2 in active_instances_list:
            ec2_id_list.append(ec2.get('InstanceId'))
        list_len = len(ec2_id_list)

    logger.debug('EC2 list is: %s', ec2_id_list)
    time_without_instance = 0
    for s in ec2_id_list:
        status = 'initializing'
        while status != 'ok':
            time.sleep(10)
            t += 10
            logger.info('EC2 Initializing... - %ds elapsed', t)
            status = get_status(client, s)
            logger.debug('Current status: %s', status)
            if status == 'no-status':
                time_without_instance += 10
                if time_without_instance == 70:
                    logger.error('The EC2 spot instance failed to start, please try again.')
                    if destroy_flag:
                        destroy(config)
                    sys.exit(1)
            elif status not in {'initializing', 'ok'}:
                logger.error('Could not start instance. Last EC2 status: %s', status)
                if destroy_flag:
                    destroy(config)
                sys.exit(1)
    logger.info('EC2 initialized.')
    pricing(n, config, fleet_id)


def pricing(n, config, fleet_id):
    """gets pricing info for fleet from AWS

    Parameters
    ----------
    n : str
        Fleet name
    config : dict
        Forge configuration data
    fleet_id : str
        AWS Fleet ID
    """
    profile = config.get('aws_profile')
    region = config.get('region')
    market = config.get('market', DEFAULT_ARG_VALS['market'])
    market = market[-1] if 'cluster-worker' in n else market[0]

    set_boto_session(region, profile)

    region = config.get('region')
    ec2_client = boto3.client('ec2')

    # Get list of active fleet EC2s
    fleet_types = []
    fleet_request_configs = ec2_client.describe_fleet_instances(FleetId=fleet_id)
    for i in fleet_request_configs.get('ActiveInstances', []):
        fleet_types.append(i['InstanceType'])

    if not fleet_types:
        return

    # Get on-demand prices regardless of market
    total_on_demand_cost = 0
    for ec2_type in fleet_types:
        total_on_demand_cost += get_ec2_pricing(ec2_type, 'on-demand', config)

    # If using spot instances get spot pricing to show savings over on-demand
    if market == 'spot':
        total_spot_cost = 0
        for ec2_type in fleet_types:
            total_spot_cost += get_ec2_pricing(ec2_type, market, config)
        saving = 100 * (1 - (total_spot_cost / total_on_demand_cost))
        logger.info('Hourly price is $%.2f. Savings of %.2f%%', total_spot_cost, saving)
    elif market == 'on-demand':
        logger.info('Hourly price is $%.2f', total_on_demand_cost)


def create_template(n, config, task):
    """creates EC2 Launch Template for n

    Parameters
    ----------
    n : str
        Fleet name
    config : dict
        Forge configuration data
    task : str
        Forge service to run
    """
    profile = config.get('aws_profile')
    ud = config.get('user_data', None)
    now_utc = datetime.utcnow()
    now_utc = now_utc.replace(microsecond=0)
    key = config.get('ec2_key')
    role = config.get('aws_role')
    name = config.get('name')
    date = config.get('date')
    region = config.get('region')
    sg = config.get('aws_security_group')
    gpu = config.get('gpu_flag', False)
    service = config.get('service')
    user = config.get('user')
    market = config.get('market', DEFAULT_ARG_VALS['market'])
    tags = config.get('tags')
    env_ami = config.get('ec2_amis')
    user_ami = config.get('ami', service)
    user_disk = config.get('disk', 0)
    user_disk_device_name = config.get('disk_device_name', None)
    valid = config.get('valid_time', DEFAULT_ARG_VALS['valid_time'])
    config_dir = config['config_dir']

    market = market[-1] if task == 'cluster-worker' else market[0]
    if service:
        if len(user_ami) == 21 and user_ami[:4] == "ami-":
            ami, disk, disk_device_name = (user_ami, config['disk'], config['disk_device_name'])
        else:
            ami_info = env_ami.get(user_ami)
            ami, disk, disk_device_name = (ami_info['ami'], ami_info['disk'], ami_info['disk_device_name'])

        disk = user_disk if user_disk > disk else disk
        disk_device_name = user_disk_device_name if user_disk_device_name else disk_device_name

    set_boto_session(region, profile)

    fmt = FormatEmpty()
    client = boto3.client('ec2')
    if isinstance(ud, dict):
        if service in config['user_data']:
            if isinstance(ud[service], str):
                with open(os.path.join(config_dir, ud[service]), 'r') as f:
                    ud = fmt.format(f.read(), **user_accessible_vars(config, market=market, task=task))
            else:
                for k, v in ud[service].items():
                    if k in n:
                        with open(os.path.join(config_dir, v), 'r') as f:
                            ud = fmt.format(f.read(), **user_accessible_vars(config, market=market, task=task))
        u = base64.b64encode(ud.encode("ascii")).decode("ascii")
    elif isinstance(ud, list):
        with open(os.path.realpath(ud[0 if task != 'cluster-worker' else 1])) as f:
            ud = fmt.format(f.read(), **user_accessible_vars(config, market=market, task=task))
        u = base64.b64encode(ud.encode("ascii")).decode("ascii")
    else:
        u = base64.b64encode("".encode("ascii")).decode("ascii")

    try:
        response = client.describe_launch_templates(LaunchTemplateNames=[n])
        logger.debug('Template %s exists, deleting', n)
        response = client.delete_launch_template(LaunchTemplateName=n)
    except ClientError:
        logger.debug('Template %s does not exists, creating.', n)

    if valid is None:
        logger.warning('No valid time limit given, defaulting to %d hours', DEFAULT_ARG_VALS['valid_time'])
        valid = DEFAULT_ARG_VALS['valid_time']

    now_utc = datetime.utcnow()
    now_utc = now_utc.replace(microsecond=0)
    valid_until = now_utc + timedelta(hours=int(valid))  # Used in tags for cleanup. DO NOT DELETE

    access_vars = user_accessible_vars(config, market=market, task=task)
    tags = [{k: fmt.format(v, **access_vars) for k, v in inner.items()} for inner in tags] if tags else None
    tags = [inner for inner in tags if None not in inner.values()]
    tags.append({'Key': 'forge-name', 'Value': n})
    specs = {'TagSpecifications': [{'ResourceType': 'instance', 'Tags': tags}]} if tags else {}

    valid_tag = [{'Key': 'valid_until', 'Value': datetime.strftime(valid_until, "%Y-%m-%dT%H:%M:%SZ")}]

    response = client.create_launch_template(
        LaunchTemplateName=n,
        LaunchTemplateData={
            'IamInstanceProfile': {'Name': role, },
            'BlockDeviceMappings': [{'DeviceName': disk_device_name,
                                     'Ebs': {'DeleteOnTermination': True,
                                             'VolumeSize': disk,
                                             'VolumeType': 'gp3'}},
                                    ],
            'ImageId': ami,
            'KeyName': key,
            'InstanceInitiatedShutdownBehavior': 'terminate',
            'UserData': u,
            'SecurityGroupIds': [sg],
            **specs
        },
        TagSpecifications=[{
            'ResourceType': 'launch-template',
            'Tags': valid_tag
        }])
    logger.info('Template %s created.', n)


def calc_machine_ranges(*, ram=None, cpu=None, ratio=None, workers=None):
    """calculate machine data for an EC2 instance

    Two of the three optional list values (ram, cpu, ratio) must be provided to calculate the third. If all three are
    provided then use all three. Ratio will default to the DEFAULT_ARG_VALS['ratio'] value which is set in __init__.py
    and overridden by normalize_config.

    Parameters
    ----------
    ram : list, default=[]
        The ram data in a double nested list
    cpu : list, default=[]
        The cpu data in a double nested list
    ratio : list, default=DEFAULT_ARG_VALS['ratio']
        The ratio data in a double nested list
    workers : int, default=1
        The number of workers

    Returns
    -------
    job_ram : list
        The calculated ram range
    job_cpu : list
        The calculated cpu range
    total_ram : int
        Total target ram for the fleet
    ram2cpu_ratio : list
        The calculated ram:cpu ratio range
    """
    default_ratio = False
    default_worker = False
    ram_and_cpu = True

    if not workers:
        workers = 1
        default_worker = True
    if not ratio:
        ratio = DEFAULT_ARG_VALS['default_ratio']
        default_ratio = True

    ratio = sorted(ratio)

    if ram == [0]:
        ram = None

    if not ram:
        ram = sorted([cpu[0] * ratio[0], cpu[-1] * ratio[-1]])
        ram_and_cpu = False
    else:
        ram = sorted(ram)

    total_ram = ram[0] * 1024

    # 768 is the max size, so make sure nothing is set to be larger than 768
    if ram[0] / workers > DEFAULT_ARG_VALS['ec2_max']:
        if not default_worker:
            logger.error('Minimum amount of RAM per worker exceeds AWS max instance')
            raise ValueError('Minimum amount of ram per worker exceeds AWS instance limit')

        job_ram = [128, 768]
    else:
        job_ram = [ram[0] // workers, ram[-1] // workers]

    # Default ram:cpu ratios are set to 8:1, but can be changed with ratio
    if not cpu:
        job_cpu = [max(job_ram[0] // ratio[0], 1), max(job_ram[1] // ratio[-1], 2)]
        ram_and_cpu = False
    else:
        job_cpu = sorted(cpu)
        job_cpu = [job_cpu[0], job_cpu[-1]]

    if ram_and_cpu and not default_ratio:
        ram2cpu_ratio = sorted(ratio)
        ram2cpu_ratio = [ram2cpu_ratio[0], ram2cpu_ratio[-1]]
    else:
        ram2cpu_ratio = [job_ram[0] / job_cpu[0], job_ram[1] / job_cpu[1]]

    job_ram = [1024 * r for r in job_ram]

    return job_ram, job_cpu, total_ram, sorted(ram2cpu_ratio)


def create_fleet(n, config, task):
    """creates the AWS EC2 fleet

    Parameters
    ----------
    n : str
        Fleet name
    config : dict
        Forge configuration data
    task : str
        Forge service to run
    """
    profile = config.get('aws_profile')
    valid = config.get('valid_time', DEFAULT_ARG_VALS['valid_time'])
    excluded_ec2s = config.get('excluded_ec2s', None)
    tags = config.get('tags')
    region = config.get('region')
    now_utc = datetime.utcnow()
    now_utc = now_utc.replace(microsecond=0)
    valid_until = now_utc + timedelta(hours=int(valid))
    subnet = config.get('aws_subnet')

    ram = config.get('ram', None)
    cpu = config.get('cpu', None)
    ratio = config.get('ratio', None)
    worker_count = config.get('workers', None)
    destroy_flag = config.get('destroy_after_failure')

    if 'single' in n and max(len(ram or []), len(cpu or []), len(ratio or [])) > 1:
        raise ValueError("Too many values provided for single job.")
    elif 'cluster' in n and min(len(ram or [0, 0]), len(cpu or [0, 0]), len(ratio or [0, 0])) < 2:
        raise ValueError("Too few values provided for cluster job.")

    def _check(x, i):
        logger.debug('Get index %d of %s', i, x)
        return x[i] if x and x[i:i + 1] else None

    if 'cluster-master' in n or 'single' in n:
        ram, cpu, total_ram, ram2cpu_ratio = calc_machine_ranges(ram=_check(ram, 0), cpu=_check(cpu, 0),
                                                                 ratio=_check(ratio, 0))
        worker_count = 1
    elif 'cluster-worker' in n:
        ram, cpu, total_ram, ram2cpu_ratio = calc_machine_ranges(ram=_check(ram, 1), cpu=_check(cpu, 1),
                                                                 ratio=_check(ratio, 1), workers=worker_count)
    else:
        logger.error("'%s' does not seem to be a valid cluster or single job.", n)
        if destroy_flag:
            destroy(config)
        sys.exit(1)

    logger.debug('OVERRIDE DETAILS | RAM: %s out of %s | CPU: %s with ratio of %s', ram, total_ram, cpu, ram2cpu_ratio)

    gpu = config.get('gpu_flag', False)
    market = config.get('market', DEFAULT_ARG_VALS['market'])
    subnet = config.get('aws_subnet')

    market = market[-1] if 'cluster-worker' in n else market[0]

    set_boto_session(region, profile)

    fmt = FormatEmpty()
    access_vars = user_accessible_vars(config, market=market, task=task)
    tags = [{k: fmt.format(v, **access_vars) for k, v in inner.items()} for inner in tags] if tags else None
    tags = [inner for inner in tags if None not in inner.values()]
    tags.append({'Key': 'forge-name', 'Value': n})

    kwargs = {
        'OnDemandOptions': {
            'AllocationStrategy': 'lowest-price'
        },
        'SpotOptions': {
            'AllocationStrategy': 'capacity-optimized',
            'InstanceInterruptionBehavior': 'terminate',
            'MaintenanceStrategies': {
                'CapacityRebalance': {
                    'ReplacementStrategy': 'launch-before-terminate',
                    'TerminationDelay': 120
                }
            }
        },
        'TargetCapacitySpecification': {
            'TotalTargetCapacity': worker_count or total_ram,
            'TargetCapacityUnitType': 'units' if worker_count else 'memory-mib',
            'DefaultTargetCapacityType': market
        },
        'Type': 'maintain',
        'ValidUntil': valid_until,
        'ExcessCapacityTerminationPolicy': 'termination',
        'TerminateInstancesWithExpiration': True,
        'ReplaceUnhealthyInstances': True,
        'TagSpecifications': [
            {
                'ResourceType': 'fleet',
                'Tags': tags
            }
        ]
    }

    if not tags:
        kwargs.pop('TagSpecifications')

    override_instance_stats = {
        'MemoryMiB': {'Min': ram[0], 'Max': ram[1]},
        'VCpuCount': {'Min': cpu[0], 'Max': cpu[1]},
        'SpotMaxPricePercentageOverLowestPrice': 100,
        'MemoryGiBPerVCpu': {'Min': ram2cpu_ratio[0], 'Max': ram2cpu_ratio[1]}
    }
    if gpu:
        override_instance_stats['AcceleratorTypes'] = ['gpu']
    if excluded_ec2s:
        override_instance_stats['ExcludedInstanceTypes'] = excluded_ec2s

    launch_template_config = {
        'LaunchTemplateSpecification': {'LaunchTemplateName': n, 'Version': '1'},
        'Overrides': [{
            'SubnetId': subnet,
            'InstanceRequirements': override_instance_stats
        }]
    }
    kwargs['LaunchTemplateConfigs'] = [launch_template_config]
    kwargs['region'] = region
    logger.debug(kwargs)
    request = fleet_request(kwargs)
    logger.debug(request)
    create_status(n, request, config)


def search_and_create(config, task):
    """check for running instances and create new ones if necessary

    Parameters
    ----------
    config : dict
        Forge configuration data
    task : str
        Forge service to run
    """
    if not config.get('ram') and not config.get('cpu'):
        logger.error('Please supply either a ram or cpu value to continue.')
        sys.exit(1)

    name = config.get('name')
    date = config.get('date', '')
    market = config.get('market', DEFAULT_ARG_VALS['market'])

    market = market[-1] if task == 'cluster-worker' else market[0]

    n = f'{name}-{market}-{task}-{date}'

    detail = ec2_ip(n, config)

    if len(detail) == 1:
        e = detail[0]
        if e['state'] in ['running', 'stopped', 'stopping', 'pending']:
            logger.info('%s is %s, the IP is %s', task, e['state'], e['ip'])
        else:
            if len(e['fleet_id']) != 0:
                logger.info('Fleet is running without EC2, will recreate it.')
                destroy(config)
            create_template(n, config, task)
            create_fleet(n, config, task)
    elif len(detail) > 1 and task != 'cluster-worker':
        logger.info('Multiple %s instances running, destroying and recreating', task)
        destroy(config)
        create_template(n, config, task)
        create_fleet(n, config, task)
        detail = ec2_ip(n, config)
        for e in detail:
            if e['state'] == 'running':
                logger.info('%s is running, the IP is %s', task, e['ip'])


def create(config):
    """creates EC2 instances based on config

    Parameters
    ----------
    config : dict
        Forge configuration data
    """
    sys.excepthook = destroy_hook

    service = config.get('service')

    if service == 'single':
        search_and_create(config, 'single')
    if service == 'cluster':
        search_and_create(config, 'cluster-master')
        search_and_create(config, 'cluster-worker')
