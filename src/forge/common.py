"""Common functions to most of forge's workings."""
import base64
import contextlib
import json
import logging
import string
import tempfile
import sys
import os
from datetime import datetime
from numbers import Number

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from . import DEFAULT_ARG_VALS, ADDITIONAL_KEYS
from .configuration import Configuration
from .exceptions import ExitHandlerException

logger = logging.getLogger(__name__)


def check_fleet_id(n, config: Configuration):
    """get the AWS fleet id for n

    Parameters
    ----------
    n : str
        Fleet name to get ID of
    config : Configuration
        Forge configuration data

    Returns
    -------
    list
        A list of fleet IDs for n
    """
    client = boto3.client('ec2')
    response = client.describe_tags(
        Filters=[
            {'Name': 'resource-type',
                'Values': ['fleet']},
            {'Name': 'tag:forge-name',
                'Values': [n]}])
    fleet_id = []
    for i in response.get('Tags'):
        fleet_id.append(i.get('ResourceId'))
    f_id = []
    for fleet_request_id in fleet_id:
        try:
            fleet_request_configs = client.describe_fleets(FleetIds=[fleet_request_id])
            fleet_activity_status = fleet_request_configs.get('Fleets')[0].get('FleetState')
            if fleet_activity_status in {'submitted', 'active', 'failed', 'deleted_running', 'modifying'}:
                f_id.append(fleet_request_id)
        except:
            pass
    return f_id


def ec2_ip(n, config: Configuration):
    """get AWS EC2 instance details for n

    Parameters
    ----------
    n : str
        Fleet name to get the instance details of
    config : Configuration
        Forge configuration data

    Returns
    -------
    list
        A list of dictionaries of the instance details in n
    """
    ec2 = boto3.resource('ec2')
    client = boto3.client('ec2')

    running_instances = ec2.instances.filter(Filters=[{
        'Name': 'instance-state-name',
        'Values': ['running', 'stopped', 'stopping', 'pending']},
        {'Name': 'tag:forge-name',
         'Values': [n]}])

    ec2s = []
    for instance in running_instances:
        ec2s.append(instance.id)

    details = []
    if len(ec2s) == 0:
        logger.info('No instances running.')
        x = {
            'ip': None,
            'id': None,
            'fleet_id': check_fleet_id(n, config),
            'state': None
        }
        details.append(x)
        logger.debug('ec2_ip details is %s', details)
        return details
    else:
        reservations = client.describe_instances(InstanceIds=ec2s)
        group = reservations.get('Reservations')
        for instances in group:
            stats = instances.get('Instances')
            for i in stats:
                x = {
                    'ip': i.get('PrivateIpAddress'),
                    'id': i.get('InstanceId'),
                    'instance_type': i.get('InstanceType'),
                    'state': i.get('State').get('Name'),
                    'launch_time': i.get('LaunchTime'),
                    'fleet_id': check_fleet_id(n, config),
                    'az': i.get('Placement')['AvailabilityZone']
                }
                details.append(x)
        logger.debug('ec2_ip details is %s', details)
        return details


def get_ip(details, states):
    """get the fleet ID & IP for details that match state

    Parameters
    ----------
    details : list
        AWS EC2 instance details for a fleet
    states : tuple
        Valid states for details to be

    Returns
    -------
    list
        A list of tuples of (id, ip) for details that match state
    """
    return [(i['ip'], i['id']) for i in list(filter(lambda x: x['state'] in states, details))]


def get_nlist(config: Configuration):
    """get list of instance names based on service

    Parameters
    ----------
    config : Configuration
        Forge configuration data

    Returns
    -------
    list
        List of instance names
    """
    date = config.date or ''
    market = config.market or DEFAULT_ARG_VALS['market']
    name = config.name
    service = config.service

    n_list = []
    if service == "cluster":
        n_list.append(f'{name}-{market[0]}-{service}-master-{date}')
        if config.rr_all:
            n_list.append(f'{name}-{market[-1]}-{service}-worker-{date}')
    elif service == "single":
        n_list.append(f'{name}-{market[0]}-{service}-{date}')

    return n_list


@contextlib.contextmanager
def key_file(secret_id, region, profile):
    """Safely retrieve a secret file from AWS for temporary use.

    This function provides a context-manager interface to retrieve a key file
    and ensure it is always removed at the end of the execution.

    Example
    -------
        with key_file(secret_id, region, profile) as pem_path:
            subprocess.run('ssh -i {pem_path} user@{ip} {run_cmd}')
    """
    def read_aws_secret():
        if profile:
            session = boto3.session.Session(profile_name=profile, region_name=region)
        else:
            session = boto3.session.Session(region_name=region)

        client = session.client(service_name='secretsmanager')

        try:
            secret_value = client.get_secret_value(SecretId=secret_id)
        except ClientError as e:
            logger.error('Could not get PEM secret from AWS.')
            raise e

        secret = json.loads(secret_value['SecretString'])
        enc_secret = secret['encoded_pem']
        return base64.b64decode(enc_secret.encode('ascii')).decode('ascii')

    secret = read_aws_secret()

    # Save the file to a temporary location with 600 permissions
    with tempfile.NamedTemporaryFile('w') as fobj:
        fobj.write(secret)
        fobj.seek(0)
        yield fobj.name


def get_regions():
    """gets the AWS region longname

    Returns
    -------
    dict
        A dictionary of a region's shortcode to it's longname
    """
    ssm = boto3.client('ssm')

    def _get_short_codes():
        nonlocal ssm
        out = set()
        for page in ssm.get_paginator('get_parameters_by_path').paginate(
                Path='/aws/service/global-infrastructure/regions'):
            out.update(i['Value'] for i in page['Parameters'])
        return out

    def _get_long_name(code):
        nonlocal ssm
        response = ssm.get_parameters(Names=[f'/aws/service/global-infrastructure/regions/{code}/longName'])
        return response['Parameters'][0]['Value']

    regions = {code: _get_long_name(code) for code in _get_short_codes()}

    return regions


def destroy_hook(exctype, value, tb):
    """a hook to bind to sys.excepthook to destroy Forge instances

    If an error occurs during the creation or running of a Forge instance, it may be more desirable to destroy the
    instance to save resources. This destroy hook enables that by binding to sys.excepthook, so if an uncaught error
    occurs, it will trigger this.

    Examples
    --------
    >>>sys.excepthook = destroy_hook

    Parameters
    ----------
    exctype : exception
        The exception type
    value : exception
        The exception instance
    tb : traceback
        A traceback for the exception
    """
    from .destroy import destroy

    logger.critical('Unhandled exception of type %s caught with value %s.', exctype, value)
    config: Configuration = tb.tb_next.tb_frame.f_locals.get('config')
    if config.destroy_after_failure:
        destroy(config)
        logger.critical('Destroyed target instances due to exception.')

    sys.exit(1)


def set_config_dir(args, forge_env=''):
    """sets the configuration directory for Forge

    Parameters
    ----------
    args : dict
        CLI arguments for Forge
    forge_env : str
        Optional forge environment. Defaults to empty string (no environment).

    Returns
    -------
    str
        Full path to forge configuration directory.
    """
    env = args.get('forge_env') or forge_env
    src_dir = os.path.dirname(os.path.realpath(__file__))

    config_dir = args.get('config_dir')

    if config_dir:
        config_dir = os.path.join(config_dir, env)
    else:
        config_dir = DEFAULT_ARG_VALS['config_dir'].format(src_dir, env)

    return config_dir


class FormatEmpty(string.Formatter):
    """formatter class to put blank strings instead of an error when kwargs don't exist

    Methods
    -------
    get_value(key, args, kwargs)
        Gets the appropriate data to fill in when formatting a string
    """

    def get_value(self, key, args, kwargs):
        """fills in data when formatting

        Parameters
        ----------
        key : int | str
            index of args or kwargs
        args : list
            int indexed arguments to fill in
        kwargs : dict
            key indexed arguments to fill in

        Returns
        -------
        str
            The requested data from the formatter, or blank if it does not exist
        """
        if isinstance(key, int) and args[key]:
            return args[key]
        elif isinstance(key, str) and kwargs.get(key):
            return kwargs.get(key)
        else:
            return ""


def user_accessible_vars(config: Configuration, **kwargs):
    """Create a dictionary to hold user-accessible data.

    This data can be used in:

    * user_data scripts
    * run_cmd string
    * Admin tags

    Parameters
    ----------
    config : Configuration
        Forge configuration data.
    kwargs : str
        Extra variables to be exposed.

    Returns
    -------
    dict
        User data script data
    """
    user_vars = {}

    # Expose the proper market(s)
    job_markets = config.market or DEFAULT_ARG_VALS['market']
    if config.service == 'cluster':
        user_vars['market_master'] = job_markets[0]
        user_vars['market_worker'] = job_markets[-1]
    else:
        user_vars['market'] = job_markets[0]

    # Expose any explicit extra variables
    user_vars.update(kwargs)
    # Expose any numeric of string configs
    user_vars.update(
        {k: v for k, v in config.items() if isinstance(v, (Number, str))}
    )
    # Expose any admin-defined variables
    user_vars.update({k: v for k, v in config.items() if k in ADDITIONAL_KEYS})

    return user_vars


def get_ec2_pricing(ec2_type, market, config: Configuration):
    """Get the hourly spot or on-demand price of given EC2 instance type.

    Parameters
    ----------
    ec2_type : str
        EC2 type to get pricing for.
    market : str
        Whether EC2 is a `'spot'` or `'on-demand'` instance.
    config : Configuration
        Forge configuration data.

    Returns
    -------
    float
        Hourly price of given EC2 type in given market.
    """
    region = config.region
    az = config.aws_az

    if market == 'spot':
        client = boto3.client('ec2')
        response = client.describe_spot_price_history(
            StartTime=datetime.utcnow(),
            ProductDescriptions=['Linux/UNIX (Amazon VPC)'],
            AvailabilityZone=az,
            InstanceTypes=[ec2_type]
        )
        price = float(response['SpotPriceHistory'][0]['SpotPrice'])

    elif market == 'on-demand':
        client = boto3.client('pricing', region_name='us-east-1')

        long_region = get_regions()[region]
        op_sys = 'Linux'

        filters = [
            {'Field': 'tenancy', 'Value': 'shared', 'Type': 'TERM_MATCH'},
            {'Field': 'operatingSystem', 'Value': op_sys, 'Type': 'TERM_MATCH'},
            {'Field': 'preInstalledSw', 'Value': 'NA', 'Type': 'TERM_MATCH'},
            {'Field': 'location', 'Value': long_region, 'Type': 'TERM_MATCH'},
            {'Field': 'capacitystatus', 'Value': 'Used', 'Type': 'TERM_MATCH'},
            {'Field': 'instanceType', 'Value': ec2_type, 'Type': 'TERM_MATCH'}
        ]
        response = client.get_products(ServiceCode='AmazonEC2', Filters=filters)

        results = response['PriceList']
        product = json.loads(results[0])
        od = product['terms']['OnDemand']
        price_details = list(od.values())[0]['priceDimensions']
        price = list(price_details.values())[0]['pricePerUnit']['USD']
        price = float(price)

    return price


def exit_callback(config: Configuration, exit: bool = False):
    if config.job == 'engine' and (config.spot_retries or (config.on_demand_failover or config.market_failover)):
        logger.error('Error occurred, bubbling up error to handler.')
        raise ExitHandlerException

    if exit:
        sys.exit(1)

    pass
