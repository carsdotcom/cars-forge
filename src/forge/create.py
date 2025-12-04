"""EC2 instance creation."""
import base64
import logging
import sys
import math
import os
import time
from datetime import datetime, timedelta

import boto3
import botocore.exceptions
from botocore.exceptions import ClientError

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .parser import add_basic_args, add_job_args, add_env_args, add_general_args, add_action_args
from .common import ec2_ip, destroy_hook, exit_callback, user_accessible_vars, FormatEmpty, get_ec2_pricing
from .configuration import Configuration
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
    add_action_args(parser, suppress=True)
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


def create_status(request_list, config: Configuration):
    """create the console status messages for Forge

    Parameters
    ----------
    request_list: list
        List of requests and fleet names
    config : Configuration
        Forge configuration data
    """
    destroy_flag = config.destroy_after_failure

    client = boto3.client('ec2')

    fleet_info = {}

    for (n, request) in request_list:
        logger.info('Creating Fleet %s... - 0s elapsed', n)

        fleet_info[n] = {
            'n': n,
            'time': 10,
            'time_without_spot': 0,
            'time_without_instance': 0,
            'fleet_id': '',
            'current_status': '',
            'create_time': '',
            'fulfilled': False,
            'initialized': False,
            'ec2_id_list': [],
        }

    time.sleep(10)

    for (n, request) in request_list:
        fleet_info[n]['fleet_id'] = fleet_id = request.get('FleetId')
        fleet_description = client.describe_fleets(FleetIds=[fleet_id])
        fleet_info[n]['create_time'] = fleet_description.get('Fleets', [{}])[0].get('CreateTime')

    uninitialized_fleets = list(filter(lambda x: not x['initialized'], fleet_info.values()))
    while uninitialized_fleets:
        for fleet in uninitialized_fleets:
            n = fleet['n']
            fleet_id = fleet['fleet_id']
            fleet_time = fleet['time']
            fleet_time_without_spot = fleet['time_without_spot']
            fleet_time_without_instance = fleet['time_without_instance']
            fleet_ec2_id_list = fleet['ec2_id_list']

            fleet_description = client.describe_fleets(FleetIds=[fleet_id])
            fleet_info[n]['current_status'] = current_status = fleet_description.get('Fleets', [{}])[0].get('ActivityStatus')

            if current_status != 'fulfilled':
                if config.create_timeout and fleet_time > config.create_timeout:
                    logger.error('Timeout of %s seconds hit for instance fulfillment for %s; Aborting.', config.create_timeout, n)
                    if destroy_flag:
                        destroy(config)
                    exit_callback(config, exit=True)

                if current_status == 'pending_fulfillment':
                    logger.info('Creating %s... - %ds elapsed', n, fleet_time)
                else:
                    if fleet_time_without_spot == 70:
                        logger.error('Could not create fleet request %s. Last status: %s.', n, current_status)
                        if destroy_flag:
                            destroy(config)
                        error_details = get_fleet_error(client, fleet_id, fleet['create_time'])
                        logger.error('Last status details: %s', error_details)
                        exit_callback(config, exit=True)

                    logger.info('Searching for %s... - %ds elapsed', n, fleet_time)

                    fleet_info[fleet['n']]['time_without_spot'] += 10
            else:
                if not fleet['fulfilled']:
                    logger.info('Fleet %s fulfilled.', n)
                    fleet_info[n]['fulfilled'] = True

                list_len = len(fleet_ec2_id_list)

                if list_len == 0:
                    if fleet_time_without_instance >= 70:
                        logger.error('The EC2 spot instance failed to start for %s, please try again.', n)
                        if destroy_flag:
                            destroy(config)
                        exit_callback(config, exit=True)

                    logger.info('Finding EC2 for %s... - %ds elapsed', n, fleet_time)

                    fleet_request_configs = client.describe_fleet_instances(FleetId=fleet_id)
                    active_instances_list = fleet_request_configs.get('ActiveInstances')
                    for ec2 in active_instances_list:
                        fleet_info[n]['ec2_id_list'].append(ec2.get('InstanceId'))

                    fleet_info[n]['time_without_instance'] += 10
                else:
                    for s in fleet_ec2_id_list:
                        status = get_status(client, s)
                        logger.debug('Current status for %s: %s', n, status)

                        if status != 'ok':
                            logger.info('EC2 Initializing for %s... - %ds elapsed', n, fleet_time)

                            if status == 'no-status':
                                if fleet_time_without_instance >= 70:
                                    logger.error('The EC2 spot instance failed to start for %s, please try again.', n)
                                    if destroy_flag:
                                        destroy(config)
                                    exit_callback(config, exit=True)

                                fleet_info[n]['time_without_instance'] += 10
                            elif status not in {'initializing', 'ok'}:
                                logger.error('Could not start instance for %s. Last EC2 status: %s', n, status)
                                if destroy_flag:
                                    destroy(config)
                                exit_callback(config, exit=True)
                        else:
                            logger.info('EC2 initialized for %s.', n)
                            fleet_info[n]['initialized'] = True
                            pricing(n, config, fleet_id)

            fleet_info[n]['time'] += 10

        time.sleep(10)
        uninitialized_fleets = list(filter(lambda x: not x['initialized'], fleet_info.values()))


def pricing(n, config: Configuration, fleet_id):
    """gets pricing info for fleet from AWS

    Parameters
    ----------
    n : str
        Fleet name
    config : Configuration
        Forge configuration data
    fleet_id : str
        AWS Fleet ID
    """
    profile = config.aws_profile
    region = config.region
    market = config.market or DEFAULT_ARG_VALS['market']
    market = market[-1] if 'cluster-worker' in n else market[0]

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
        logger.info('Hourly price for %s is $%.2f. Savings of %.2f%%', n, total_spot_cost, saving)
    elif market == 'on-demand':
        logger.info('Hourly price for %s is $%.2f', n, total_on_demand_cost)


def create_template(n, config: Configuration, task, task_details):
    """creates EC2 Launch Template for n

    Parameters
    ----------
    n : str
        Fleet name
    config : Configuration
        Forge configuration data
    task : str
        Forge service to run
    task_details : dict
        Task instance details
    """
    ud = config.user_data
    key = config.ec2_key
    role = config.aws_role
    sg = config.aws_security_group
    gpu = config.gpu_flag or False
    service = config.service
    market = config.market or DEFAULT_ARG_VALS['market']
    tags = config.tags
    env_ami = config.ec2_amis
    user_ami = config.ami or service
    user_disk = config.disk or 0
    user_disk_device_name = config.disk_device_name
    valid = config.valid_time or DEFAULT_ARG_VALS['valid_time']
    config_dir = config.config_dir
    imds_max_hops = config.aws_imds_max_hops

    market = market[-1] if task == 'cluster-worker' else market[0]
    if service:
        if user_ami[:4] == "ami-":
            if not user_disk or not user_disk_device_name:
                logger.error('disk and disk_device_name must be specified when manually setting an AMI ID')
                sys.exit(1)

            ami, disk, disk_device_name = (user_ami, user_disk, user_disk_device_name)
        else:
            if gpu:
                user_ami += '_gpu'

            ami_info = env_ami.get(user_ami)
            disk, disk_device_name = (ami_info['disk'], ami_info['disk_device_name'])
            ami = list(task_details['ami_spec'].values())[0]

            if not imds_max_hops and ami_info.get('aws_imds_max_hops'):
                imds_max_hops = ami_info['aws_imds_max_hops']

        disk = user_disk if user_disk > disk else disk
        disk_device_name = user_disk_device_name if user_disk_device_name else disk_device_name

    fmt = FormatEmpty()
    client = boto3.client('ec2')
    if isinstance(ud, dict):
        # ToDo: Deprecate service being checked in event of AMI ID
        ami_or_service = user_ami if user_ami in config.user_data else service

        if ami_or_service:
            if isinstance(ud[ami_or_service], str):
                with open(os.path.join(config_dir, ud[ami_or_service]), 'r') as f:
                    ud = fmt.format(f.read(), **user_accessible_vars(config, market=market, task=task))
            else:
                for k, v in ud[ami_or_service].items():
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

    launch_template_kwargs = {}
    if tags:
        launch_template_kwargs['TagSpecifications'] = [{'ResourceType': 'instance', 'Tags': tags}]

    if sg:
        launch_template_kwargs['SecurityGroupIds'] = sg

    valid_tag = [{'Key': 'valid_until', 'Value': datetime.strftime(valid_until, "%Y-%m-%dT%H:%M:%SZ")}]

    imds_v2 = 'required' if config.aws_imds_v2 else 'optional'
    metadata_options = {'HttpTokens': imds_v2}

    if imds_max_hops:
        metadata_options['HttpPutResponseHopLimit'] = imds_max_hops

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
            'MetadataOptions': metadata_options,
            **launch_template_kwargs
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


def get_placement_az(config: Configuration, instance_details, mode=None):
    if not mode:
        mode = 'balanced'

    region = config.region
    subnet = config.aws_multi_az

    client = boto3.client('ec2')
    az_info = client.describe_availability_zones()
    az_mapping = {x['ZoneId']: x['ZoneName'] for x in az_info['AvailabilityZones']}

    kwargs = {}
    if instance_details['instance_type']:
        kwargs['InstanceTypes'] = [instance_details['instance_type']]
    else:
        kwargs = {
            'InstanceRequirementsWithMetadata': {
                'ArchitectureTypes': list(instance_details['ami_spec'].keys()),
                'InstanceRequirements': instance_details['override_instance_stats']
            }
        }

    try:
        response = client.get_spot_placement_scores(
            TargetCapacity=instance_details['total_capacity'],
            TargetCapacityUnitType=instance_details['capacity_unit'],
            SingleAvailabilityZone=True,
            RegionNames=[region],
            MaxResults=10,
            **kwargs
        )

        placement = {az_mapping[x['AvailabilityZoneId']]: x['Score'] for x in response['SpotPlacementScores']}
        logger.debug(placement)
    except botocore.exceptions.ClientError as e:
        logger.error('Permissions to pull spot placement scores are necessary')
        logger.error(e)
        placement = {}

    subnet_details = {}

    try:
        for placement_az, placement_subnet in subnet.items():
            response = client.describe_subnets(
                SubnetIds=[placement_subnet]
            )

            logger.debug(response)

            subnet_details[placement_az] = response['Subnets'][0]['AvailableIpAddressCount']

    except botocore.exceptions.ClientError as e:
        logger.error(e)

    if mode in ['balanced', 'placement']:
        subnet_details = {k: int(math.sqrt(v)) for k, v in subnet_details.items()}

    if mode == 'placement':
        placement = {k: v**2 for k, v in placement.items()}

    for k, v in subnet_details.items():
        if placement.get(k):
            placement[k] += v
        else:
            placement[k] = v

    az = max(placement, key=placement.get)

    return az


def create_fleet(n, config: Configuration, task, task_details):
    """creates the AWS EC2 fleet

    Parameters
    ----------
    n : str
        Fleet name
    config : Configuration
        Forge configuration data
    task : str
        Forge service to run
    task_details: dict
        EC2 instance details for create_fleet

    Returns
    -------
    dict
        Response from Boto3 create_fleet
    """
    valid = config.valid_time or DEFAULT_ARG_VALS['valid_time']
    excluded_ec2s = config.excluded_ec2s
    tags = config.tags
    region = config.region
    now_utc = datetime.utcnow()
    now_utc = now_utc.replace(microsecond=0)
    valid_until = now_utc + timedelta(hours=int(valid))
    subnet = config.aws_multi_az
    instance_type = config.instance_type

    gpu = config.gpu_flag or False
    market = config.market or DEFAULT_ARG_VALS['market']
    strategy = config.spot_strategy

    if not isinstance(market, list):
        market = [market]
    market = market[-1] if 'cluster-worker' in n else market[0]

    az = config.aws_az

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
            'AllocationStrategy': strategy,
            'InstanceInterruptionBehavior': 'terminate',
            'MaintenanceStrategies': {
                'CapacityRebalance': {
                    'ReplacementStrategy': 'launch-before-terminate',
                    'TerminationDelay': 120
                }
            }
        },
        'TargetCapacitySpecification': {
            'TotalTargetCapacity': task_details['total_capacity'],
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

    overrides = {
        'SubnetId': subnet[az],
        'AvailabilityZone': az,
    }

    if task_details['instance_type']:
        overrides['InstanceType'] = task_details['instance_type']
    else:
        if gpu:
            task_details['override_instance_stats']['AcceleratorTypes'] = ['gpu']
        if excluded_ec2s:
            task_details['override_instance_stats']['ExcludedInstanceTypes'] = excluded_ec2s

        overrides['InstanceRequirements'] = task_details['override_instance_stats']
        kwargs['TargetCapacitySpecification']['TargetCapacityUnitType'] = task_details['capacity_unit']

    kwargs['LaunchTemplateConfigs'] = [{
        'LaunchTemplateSpecification': {'LaunchTemplateName': n, 'Version': '1'},
        'Overrides': []
    }]
    for ami_arch, ami_id in task_details['ami_spec'].items():
        kwargs['LaunchTemplateConfigs'][0]['Overrides'].append({
            **overrides,
            'ImageId': ami_id,
        })

    kwargs['region'] = region
    logger.debug(kwargs)
    request = fleet_request(kwargs)
    logger.debug(request)

    return request
    #create_status(n, request, config)


def search_and_create(config: Configuration, instance_details):
    """check for running instances and create new ones if necessary

    Parameters
    ----------
    config : Configuration
        Forge configuration data
    instance_details: dict
        EC2 instance details for create_fleet
    """
    if not config.ram and not config.cpu and not config.instance_type:
        logger.error('Please supply either a ram, cpu, or instance_type value to continue.')
        sys.exit(1)

    name = config.name
    date = config.date or ''
    markets = config.market or DEFAULT_ARG_VALS['market']

    if not isinstance(markets, list):
        markets = [markets]

    create_tasks = []

    for task, task_details in instance_details.items():
        market = markets[-1] if task == 'cluster-worker' else markets[0]
        n = f'{name}-{market}-{task}-{date}'

        detail = ec2_ip(n, config)

        if len(detail) == 1:
            e = detail[0]
            if e['state'] in ['running', 'stopped', 'stopping', 'pending']:
                logger.info('%s is %s, the IP is %s', task, e['state'], e['ip'])

                if config.destroy_on_create:
                    logger.info('destroy_on_create true, destroying fleet.')
                    destroy(config)
                    create_template(n, config, task, task_details)
                    create_tasks.append((task, n))
                    #create_fleet(n, config, task, instance_details)
            else:
                if len(e['fleet_id']) != 0:
                    logger.info('Fleet is running without EC2, will recreate it.')
                    destroy(config)
                create_template(n, config, task, task_details)
                create_tasks.append((task, n))
                #create_fleet(n, config, task, instance_details)
        elif len(detail) > 1 and task != 'cluster-worker':
            logger.info('Multiple %s instances running, destroying and recreating', task)
            destroy(config)
            create_template(n, config, task, task_details)
            create_tasks.append((task, n))
            #create_fleet(n, config, task, instance_details)
            #detail = ec2_ip(n, config)
            #for e in detail:
                #if e['state'] == 'running':
                    #logger.info('%s is running, the IP is %s', task, e['ip'])

    fleet_requests = []
    for task, n in create_tasks:
        request = create_fleet(n, config, task, instance_details[task])
        fleet_requests.append((n, request))

    create_status(fleet_requests, config)


def get_ami_spec(config: Configuration):
    """

    Parameters
    ----------
    config : Configuration
        Forge configuration data

    Returns
    -------
    dict
        a resolved Forge AMI specification that maps AMI architecture to an AMI ID
    """
    arch = config.architecture or 'x86_64'
    env_amis = config.ec2_amis
    user_ami = config.ami
    service = config.service
    destroy_flag = config.destroy_after_failure

    if user_ami and user_ami[:4] == 'ami-':
        return {arch: user_ami}

    ami_info = env_amis.get(user_ami) or env_amis.get(service)

    if ami_spec := ami_info.get('ami_spec'):
        ret = {}

        if arch := config.architecture:
            try:
                ami_spec = {arch: ami_spec[arch]}
            except KeyError:
                logger.error('No matching AMI spec for the requested architecture')
                if destroy_flag:
                    destroy(config)
                sys.exit(1)

        for ami_arch, ami_spec_details in ami_spec.items():
            if ami_id := ami_spec_details.get('id'):
                ret[ami_arch] = ami_id
            elif ami_filter := ami_spec_details.get('filter'): # ToDo: Implement AMI filters
                logger.error('AMI filters have not been implemented yet.')
                if destroy_flag:
                    destroy(config)
                sys.exit(1)

        return ret

    return {arch: ami_info['ami']}


def get_instance_details(config: Configuration, task_list, *, worker_units: bool = True):
    """calculate instance details & resources for fleet creation
    Parameters
    ----------
    config : Configuration
        Forge configuration data
    task_list : list
        Forge services to get details of
    worker_units : bool
        Whether the number of workers should be discretely set (True, default) or inferred (False)
    """
    job = config.job
    service = config.service
    ram = config.ram
    cpu = config.cpu
    ratio = config.ratio
    worker_count = config.workers
    destroy_flag = config.destroy_after_failure
    instance_type = config.instance_type

    rc_length = 1 if service == 'single' else 2 if service == 'cluster' else None

    if not ram and not cpu and not instance_type:
        if job != 'modify':
            logger.error('Invalid configuration, either ram, cpu, or instance_type must be provided.')
            if destroy_flag:
                destroy(config)
            sys.exit(1)
    elif (ram and len(ram) != rc_length) or (cpu and len(cpu) != rc_length) or (instance_type and len(instance_type) != rc_length):
        logger.error('Invalid configuration, ram, cpu, or instance_type must have one value for single jobs, and two for cluster jobs.')
        if destroy_flag:
            destroy(config)
        sys.exit(1)

    instance_details = {}
    ami_spec = get_ami_spec(config)

    def _check(x, i):
        logger.debug('Get index %d of %s', i, x)
        return x[i] if x and x[i:i + 1] else None

    for task in task_list:
        task_worker_count = worker_count

        calc_kwargs = {}

        if 'cluster-master' in task or 'single' in task:
            task_ram = _check(ram, 0)
            task_cpu = _check(cpu, 0)
            task_ratio = _check(ratio, 0)
            task_instance_type = _check(instance_type, 0)

            if task_worker_count or task_instance_type:
                task_worker_count = 1
        elif 'cluster-worker' in task:
            task_ram = _check(ram, 1)
            task_cpu = _check(cpu, 1)
            task_ratio = _check(ratio, 1)
            task_instance_type = _check(instance_type, 1)

            calc_kwargs['workers'] = task_worker_count

            if task_instance_type: # ToDo: calculate RAM maximum
                task_worker_count = config.workers or 1
        else:
            logger.error("'%s' does not seem to be a valid cluster or single job.", task)
            if destroy_flag:
                destroy(config)
            sys.exit(1)

        instance_details[task] = {
            'ami_spec': ami_spec,
            'instance_type': task_instance_type,
            'total_capacity': task_worker_count,
            'capacity_unit': 'units' if task_worker_count else 'memory-mib',
        }

        if (task_ram and task_ram[0]) or (task_cpu and task_cpu[0]):
            task_ram, task_cpu, total_ram, ram2cpu_ratio = calc_machine_ranges(ram=task_ram, cpu=task_cpu, ratio=task_ratio, **calc_kwargs)
            logger.debug('%s OVERRIDE DETAILS | RAM: %s out of %s | CPU: %s with ratio of %s', task, task_ram, total_ram, task_cpu, ram2cpu_ratio)

            instance_details[task]['total_capacity'] = total_ram
            instance_details[task]['capacity_unit'] = 'memory-mib'

            if task_worker_count:
                if worker_units:
                    instance_details[task]['total_capacity'] = task_worker_count
                    instance_details[task]['capacity_unit'] = 'units'
                else:
                    logger.warning('Number of workers specified, but fleet is not configured to use number of workers; using inferred workers instead')

            instance_details[task]['override_instance_stats'] = {
                'MemoryMiB': {'Min': task_ram[0], 'Max': task_ram[1]},
                'VCpuCount': {'Min': task_cpu[0], 'Max': task_cpu[1]},
                'SpotMaxPricePercentageOverLowestPrice': 100,
                'MemoryGiBPerVCpu': {'Min': ram2cpu_ratio[0], 'Max': ram2cpu_ratio[1]} if ram2cpu_ratio else None
            }

        if task_instance_type:
            logger.warning('For task %s, the configured instance type will override the configured ram/cpu values', task)

    return instance_details


def create(config: Configuration):
    """creates EC2 instances based on config

    Parameters
    ----------
    config : Configuration
        Forge configuration data
    """
    sys.excepthook = destroy_hook

    service = config.service
    task_list = ['single']

    if service == 'cluster':
        task_list = ['cluster-master', 'cluster-worker']

    instance_details = get_instance_details(config, task_list)

    if not config.aws_az:
        config.aws_az = get_placement_az(config, instance_details[task_list[-1]])

    search_and_create(config, instance_details)
