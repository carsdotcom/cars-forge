"""cleanup expired instances"""
import logging
from datetime import datetime, timezone

import boto3

from . import REQUIRED_ARGS
from .configuration import Configuration
from .parser import add_basic_args, add_general_args, add_env_args, add_job_args, add_action_args

logger = logging.getLogger(__name__)


def cli_cleanup(subparsers):
    """adds cleanup parser to subparser

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser('cleanup', description='Cleanup EC2 launch templates')
    add_basic_args(parser)
    add_general_args(parser)
    add_job_args(parser, suppress=True)
    add_action_args(parser, suppress=True)
    add_env_args(parser)

    REQUIRED_ARGS['cleanup'] = {'forge_env'}


def cleanup(config: Configuration):
    """removes all AWS LaunchTemplates that have an expired valid_time tag

    Parameters
    ----------
    config : Configuration
    Forge configuration data

    Returns
    -------
    int
        returns 0 for success
    """
    client = boto3.client('ec2')

    describe_args = {'Filters': [{'Name': 'tag-key', 'Values': ['valid_until']}]}
    templates = []

    while True:
        response = client.describe_launch_templates(**describe_args)

        templates += [(template['LaunchTemplateName'], template['LaunchTemplateId'], tag['Value'])
                      for template in response['LaunchTemplates'] if 'Tags' in template
                      for tag in template['Tags'] if tag['Key'] == 'valid_until']

        if 'NextToken' not in response:
            break

        describe_args['NextToken'] = response['NextToken']

    logger.debug('Templates are %s', templates)

    now = datetime.now(timezone.utc)
    for name, tid, valid_until in templates:
        valid_until = datetime.strptime(valid_until, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if now > valid_until:
            response = client.delete_launch_template(LaunchTemplateId=tid)
            logger.debug('Response is: %s', response)
            logger.info('Destroyed template %s (%s)', name, tid)

    return 0
