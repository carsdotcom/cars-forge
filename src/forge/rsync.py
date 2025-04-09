"""Rsync user content to EC2 instance."""
import logging
import os
import re
import subprocess
import sys

import boto3

from . import REQUIRED_ARGS
from .exceptions import ExitHandlerException
from .parser import add_basic_args, add_general_args, add_env_args, add_action_args, add_job_args
from .common import ec2_ip, key_file, get_ip, get_nlist, exit_callback
from .configuration import Configuration

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
    add_job_args(parser, suppress=True)
    add_action_args(parser)
    add_env_args(parser)

    REQUIRED_ARGS['rsync'] = ['name',
                              'service',
                              'forge_env',]


def rsync(config: Configuration):
    """rsyncs the file at rsync_path to the instance

    Parameters
    ----------
    config : Configuration
        Forge configuration data

    Returns
    -------
    int
        The status of the rsync commands
    """

    rval = 0

    def _rsync(config: Configuration, ip):
        """performs the rsync to a given ip

        Parameters
        ----------
        config : Configuration
            Forge configuration data
        ip : str
            IP of the instance to rsync to
        """
        pem_secret = config.forge_pem_secret
        region = config.region
        profile = config.aws_profile
        rsync_loc = config.rsync_path or config.app_dir

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

    def _s3_rsync(config: Configuration, ip):
        """downloads a file from S3 and performs a rsync to a given ip

        Parameters
        ----------
        config : Configuration
            Forge configuration data
        ip : str
            IP of the instance to rsync to
        """

        rval = 0

        s3_loc = config.s3_path

        logger.debug('S3 path: %s', s3_loc)

        s3_uri_pattern = r'(?:s3\:/)?/?(?P<bucket>\S+?)/(?P<key>\S+)'

        match = re.match(s3_uri_pattern, s3_loc)
        if match:
            bucket = match.group('bucket')
            key = match.group('key')
            name = key.split('/')[-1]

            local_path = f'/tmp/{name}'

            logger.debug('Downloading file from S3 to %s', local_path)

            s3 = boto3.resource('s3')
            s3.Object(bucket, key).download_file(local_path)

            logger.debug('Successfully downloaded file %s', local_path)

            s3_config = config.clone()
            s3_config.rsync_path = local_path

            rval += _rsync(s3_config, ip)

            os.remove(local_path)
        else:
            rval += 1

        return rval

    n_list = get_nlist(config)

    if not config.rsync_path and not config.s3_path:
        logger.error('No rsync_path or s3_path specified, exiting')
        sys.exit(1)

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
                if config.rsync_path:
                    logger.info('Rsync destination is %s', ip)
                    rval += _rsync(config, ip)

                if config.s3_path:
                    logger.info('S3 rsync destination is %s', ip)
                    rval += _s3_rsync(config, ip)

                if rval:
                    raise ValueError('Rsync command unsuccessful, ending attempts.')
        except ValueError as e:
            logger.error('Got error %s when trying to rsync.', e)
            try:
                exit_callback(config)
            except ExitHandlerException:
                raise

    return rval
