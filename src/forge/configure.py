"""Configure ENV yaml."""
import ast
import logging
import os
import sys

import yaml
from schema import Schema, And, Optional, SchemaError

from .common import set_config_dir

logger = logging.getLogger(__name__)


def cli_configure(subparsers):
    """adds configure parser to subparser

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser(
        'configure', description=f'Configure env yaml and place it in {set_config_dir({})}'
    )

    parser.add_argument(
        '--log_level', choices={'DEBUG', 'INFO', 'WARNING', 'ERROR'},
        default='INFO', type=str.upper, help='Override logging level.'
    )


def check_env_yaml(env_yaml):
    """validates the environment yaml file

    Parameters
    ----------
    env_yaml : dict
        The environment configuration data

    Returns
    -------
    dict
        The validated environment yaml data

    Raises
    ------
    schema.SchemaError
        If env_yaml does not pass validation
    """
    schema = Schema({
        'forge_env': And(str, len, error='Invalid Environment Name'),
        'aws_az': And(str, len, error='Invalid AWS availability zone'),
        'ec2_amis': And(dict, len, error='Invalid AMI Dictionary'),
        'aws_subnet': And(str, len, error='Invalid AWS Subnet'),
        'ec2_key': And(str, len, error='Invalid AWS key'),
        'aws_security_group': And(str, len, error='Invalid AWS Security Group'),
        'forge_pem_secret': And(str, len, error='Invalid Name of Secret'),
        Optional('aws_profile'): And(str, len, error='Invalid AWS profile'),
        Optional('ratio'): And(list, len, error='Invalid default ratio'),
        Optional('user_data'): And(dict, len, error='Invalid Create Scripts'),
        Optional('tags'): And(list, len, error="Invalid AWS tags"),
        Optional('excluded_ec2s'): And(list),
        Optional('additional_config'): And(list),
        Optional('ec2_max'): And(int)
    })
    try:
        validated = schema.validate(env_yaml)
        return validated
    except SchemaError as err:
        logger.error(err)
        sys.exit(1)


def configure():
    """create a Forge configuration file in the CLI"""
    forge_env = input("Environment Name?: ")
    aws_profile = input("AWS profile?: ")
    aws_az = input("AWS availability zone?: ")
    ec2_amis = input("EC2 AMIs?: ")
    aws_subnet = input("AWS Subnet?: ")
    ec2_key = input("AWS key used with EC2?: ")
    aws_security_group = input("AWS Security Group?: ")
    forge_pem_secret = input("Name of Secret for pem key?: ")
    excluded_ec2s = input("EC2s to exclude from spot fleet (Optional): ")
    tags = input("Tags applied to EC2 and fleet (Optional): ")
    user_data = input("The default user_data files. Files are loaded to the config folder (Optional): ")
    additional_config = input("Additional configs needed for your application (Optional): ")

    d = {'forge_env': forge_env, 'aws_profile': aws_profile, 'aws_az': aws_az,
         'ec2_amis': ast.literal_eval(ec2_amis), 'aws_subnet': aws_subnet,
         'ec2_key': ec2_key, 'aws_security_group': aws_security_group, 'forge_pem_secret': forge_pem_secret}

    if tags:
        d.update({'tags': ast.literal_eval(tags)})
    if excluded_ec2s:
        excluded_ec2s = excluded_ec2s.replace(',', ' ')
        excluded_ec2s = excluded_ec2s.replace('  ', ' ')
        ec2_list = list(excluded_ec2s.split(" "))
        d.update({'excluded_ec2s': (ec2_list)})
    if user_data:
        d.update({'user_data': ast.literal_eval(user_data)})
    if additional_config:
        d.update({'additional_config': ast.literal_eval(additional_config)})

    config = check_env_yaml(d)
    logger.debug('env_yaml is %s', config)
    src_dir = os.path.dirname(os.path.realpath(__file__))
    config_dir = f'{src_dir}/config/{forge_env}'

    if os.path.exists(config_dir):
        logger.info('Config directory for %s already exists. Overwriting.', config_dir)
    else:
        logger.info('Config directory for %s does no exist. Making directory.', config_dir)
        os.mkdir(config_dir)

    file = f'{config_dir}/{forge_env}.yaml'
    with open(file, 'w') as file:
        yaml.dump(config, file)
    logger.info('Created %s config file.', forge_env)
