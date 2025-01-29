"""Run a command on remote EC2."""
import logging
import shlex
import subprocess
import sys

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .exceptions import ExitHandlerException
from .parser import add_basic_args, add_general_args, add_env_args, add_action_args, add_job_args
from .common import ec2_ip, key_file, get_ip, destroy_hook, user_accessible_vars, FormatEmpty, exit_callback, get_nlist
from .configuration import Configuration
from .destroy import destroy

logger = logging.getLogger(__name__)


def cli_run(subparsers):
    """adds run parser to subparser

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser('run', description='Run command on remote EC2')
    add_basic_args(parser)
    add_general_args(parser)
    add_job_args(parser, suppress=True)
    add_action_args(parser)
    add_env_args(parser)

    REQUIRED_ARGS['run'] = ['name',
                            'service',
                            'forge_env',
                            'run_cmd']


def run(config: Configuration):
    """runs the file specified by run_cmd on the instance

    Parameters
    ----------
    config : Configuration
        Forge configuration data

    Returns
    -------
    int
        The status of the run commands
    """
    sys.excepthook = destroy_hook

    # run the run script on the single or master
    service = config.service
    market = config.market or DEFAULT_ARG_VALS['market']
    destroy_flag = config.destroy_after_failure
    rval = 0
    task = service

    def _run(config: Configuration, ip):
        """performs the run operation on a given ip

        Parameters
        ----------
        config : Configuration
            Forge configuration data
        ip : str
            IP of the instance to run the command on

        Returns
        -------
        int
            The status of the program
        """
        run_cmd = config.run_cmd
        pem_secret = config.forge_pem_secret
        region = config.region
        profile = config.aws_profile

        with key_file(pem_secret, region, profile) as pem_path:
            fmt = FormatEmpty()
            run_cmd = fmt.format(run_cmd, **user_accessible_vars(config, market=market, task=task, ip=ip))
            cmd = 'ssh -t -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
            cmd += f' -i {pem_path} root@{ip} /root/{run_cmd}'

            try:
                subprocess.run(shlex.split(cmd), check=True, universal_newlines=True)
                return 0
            except subprocess.CalledProcessError as exc:
                logger.error(
                    'EC2 command failed with error code %d: %s', exc.returncode, exc.cmd
                )
                return exc.returncode

    n_list = get_nlist(config)

    for n in n_list:
        try:
            logger.info('Trying to run command on %s', n)
            details = ec2_ip(n, config)
            targets = get_ip(details, ('running',))

            if not targets or len(targets[0]) != 2:
                logger.error('Could not find any valid instances to run the command on')
                rval += 1
                continue

            logger.debug('Instance target details are %s', targets)
            market = n.split('-')[1]

            if 'cluster-master' in n:
                task += '-master'
            elif 'cluster-worker' in n:
                task += '-worker'

            for ip, _ in targets:
                logger.info('Run destination is %s', ip)
                rval = _run(config, ip)
                if rval:
                    raise ValueError('Run command unsuccessful, ending attempts.')
        except ValueError as e:
            logger.error('Run command raised error: %s', e)
            try:
                exit_callback(config)
            except ExitHandlerException:
                raise
            finally:
                if destroy_flag:
                    logger.info('destroy_after_failure parameter True, running forge destroy...')
                    destroy(config)

    return rval
