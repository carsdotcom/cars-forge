"""Run a command on remote EC2, rsync user content, and execute it."""
import logging
import time

import boto3

from . import DEFAULT_ARG_VALS, REQUIRED_ARGS
from .exceptions import ExitHandlerException
from .parser import add_basic_args, add_job_args, add_env_args, add_general_args, add_action_args, nonnegative_int_arg
from .configuration import Configuration
from .create import create, ec2_ip
from .rsync import rsync
from .run import run


logger = logging.getLogger(__name__)


def cli_engine(subparsers):
    """add engine parser to subparsers

    Parameters
    ----------
    subparsers : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser = subparsers.add_parser('engine', description='create EC2, rsync content, and execute it')
    add_basic_args(parser)
    add_job_args(parser)
    add_env_args(parser)
    add_general_args(parser)
    add_action_args(parser)

    parser.add_argument('--spot_retries', '--spot-retries', type=nonnegative_int_arg)
    parser.add_argument('--on_demand_failover', '--on-demand-failover', action='store_true', dest='market_failover')

    REQUIRED_ARGS['engine'] = list(set(REQUIRED_ARGS['create'] +
                                       REQUIRED_ARGS['rsync'] +
                                       REQUIRED_ARGS['run'] +
                                       REQUIRED_ARGS['destroy']))


def engine(config: Configuration):
    """runs the Forge engine command

    Parameters
    ----------
    config : Configuration
        Forge configuration data

    Returns
    -------
    int
        The exit status for run with 0 for success
    """
    status = 4

    try:
        create(config)
        logger.info('Waiting for 60s to ensure EC2 has finished starting up...')
        time.sleep(60)
        status = rsync(config)
        status = run(config)
    except ExitHandlerException:
        # Check for spot instances and retries
        if 'spot' in config.market:
            name = config.name
            date = config.date or ''
            market = config.market or DEFAULT_ARG_VALS['market']
            service = config.service

            n_list = []
            if service == "cluster":
                n_list.append(f'{name}-{market[0]}-{service}-master-{date}')
                n_list.append(f'{name}-{market[-1]}-{service}-worker-{date}')
            elif service == "single":
                n_list.append(f'{name}-{market[0]}-{service}-{date}')

            for n in n_list:
                flag = False
                details = ec2_ip(n, config)

                for ec2 in details:
                    if ec2['state'] != 'running':
                        flag = True

                if flag:
                    break
            else:
                logger.critical('Bubble received but all instances are ok.')
                status = 3
                return status

            if (config.spot_retries or 0) > 0:
                config.spot_retries -= 1
                status = engine(config)
            elif config.on_demand_failover or config.market_failover:
                config.market[0] = config.market[-1] = 'on-demand'
                status = engine(config)
        else:
            status = 5

    return status
