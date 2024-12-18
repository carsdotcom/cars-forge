"""Rsync user content to EC2 instance."""
import logging
import os
import subprocess
import sys

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .destroy import destroy
from .exceptions import ExitHandlerException
from .parser import add_basic_args, add_general_args, add_env_args, add_action_args
from .common import ec2_ip, key_file, get_ip, get_nlist, exit_callback

logger = logging.getLogger(__name__)


def cli_rsync(subparsers):
    """adds rsync parser to subparser

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser('rsync', description='Rsync user content to EC2 instance')
    add_basic_args(parser)

    add_general_args(parser)
    add_action_args(parser)
    add_env_args(parser)

    REQUIRED_ARGS['rsync'] = ['name',
                              'service',
                              'forge_env',
                              'rsync_path']


def rsync(config):
    """rsyncs the file at rsync_path to the instance

    Parameters
    ----------
    config : dict
        Forge configuration data

    Returns
    -------
    int
        The status of the rsync commands
    """

    destroy_flag = config.get('destroy_after_failure')
    rval = 0

    def _rsync(config, ip):
        """performs the rsync to a given ip

        Parameters
        ----------
        config : dict
            Forge configuration data
        ip : str
            IP of the instance to rsync to
        """
        pem_secret = config['forge_pem_secret']
        region = config['region']
        profile = config.get('aws_profile')
        rsync_loc = config.get('rsync_path', config.get('app_dir'))

        with key_file(pem_secret, region, profile) as pem_path:
            if os.path.isdir(rsync_loc):
                logger.info('Copying folder %s to EC2.', rsync_loc)
                rsync_loc += '/*'
            elif os.path.isfile(rsync_loc):
                logger.info('Copying file %s to EC2.', rsync_loc)
            else:
                logger.error("File or folder from 'rsync_path' parameter not found: %s", rsync_loc)
                sys.exit(1)

            cmd = 'rsync -rave "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
            cmd += f' -i {pem_path}" {rsync_loc} root@{ip}:/root/'

            try:
                output = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT, shell=True, universal_newlines=True
                )
                logger.info('Rsync successful:\n%s', output)
                return 0
            except subprocess.CalledProcessError as exc:
                logger.error('Rsync failed:\n%s', exc.output)
                return exc.returncode

    n_list = get_nlist(config)

    for n in n_list:
        try:
            logger.info('Trying to rsync to %s...', n)
            details = ec2_ip(n, config)
            targets = get_ip(details, ('running',))
            logger.debug('Instance target details are %s', targets)
            if not targets or len(targets[0]) != 2:
                logger.error('Could not find any valid instances to rsync to')
                continue

            for ip, _ in targets:
                logger.info('Rsync destination is %s', ip)
                rval = _rsync(config, ip)
                if rval:
                    raise ValueError('Rsync command unsuccessful, ending attempts.')
        except ValueError as e:
            logger.error('Got error %s when trying to rsync.', e)
            try:
                exit_callback(config)
            except ExitHandlerException:
                raise

    return rval
