"""Connect to remote EC2 via SSH."""
import logging
import shlex
import subprocess
import sys

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .parser import add_basic_args, add_general_args, add_env_args
from .common import ec2_ip, key_file, get_ip

logger = logging.getLogger(__name__)


def cli_ssh(subparsers):
    """adds ssh parser to subparser

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser('ssh', description='SSH to EC2 instance')
    add_basic_args(parser)
    add_general_args(parser)
    add_env_args(parser)

    REQUIRED_ARGS['ssh'] = ['name',
                            'service',
                            'forge_env']


def ssh(config):
    """ssh into a running EC2 instance

    Parameters
    ----------
    config : dict
        Forge configuration data
    """
    name = config['name']
    date = config.get('date', '')
    service = config['service']
    pem_secret = config['forge_pem_secret']
    region = config['region']
    profile = config.get('aws_profile')
    market = config.get('market', DEFAULT_ARG_VALS['market'])

    if service == "cluster":
        n = f'{name}-{market[0]}-{service}-master-{date}'
        details = ec2_ip(n, config)
    elif service == "single":
        n = f'{name}-{market[0]}-{service}-{date}'
        details = ec2_ip(n, config)

    response = get_ip(details, ('running',))
    if response and len(response[0]) == 2:
        ip, _ = response[0]
    else:
        logger.error('Could not find any valid instances to SSH to')
        sys.exit(1)

    logger.info('Connecting to the instance.')
    with key_file(pem_secret, region, profile) as pem_path:
        cmd = 'ssh -t -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
        cmd += f' -i {pem_path} root@{ip}'

        try:
            subprocess.run(shlex.split(cmd), check=True, universal_newlines=True)
        except subprocess.CalledProcessError as exc:
            if exc.returncode == 142:
                logger.error('Missing proper SSH credentials to connect. Please check your user_data and/or AMI.')
            else:
                logger.error('SSH failed with error code %d: %s', exc.returncode, exc.cmd)
            sys.exit(exc.returncode)
