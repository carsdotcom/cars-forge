"""Configure ENV yaml."""
import ast
import logging
import os

import yaml

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
