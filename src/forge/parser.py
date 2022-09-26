"""Parser argument groups for Forge."""
import argparse
import os
from ast import literal_eval


def positive_int_arg(string):
    """helper function to validate arguments that must be positive integers

    Parameters
    ----------
    string : str
        String to check if it is a positive int

    Returns
    -------
    int
        The number in string if it is a positive int

    Raises
    ------
    argparse.ArgumentTypeError
        If the number is not a positive integer
    """
    msg = 'Must be a positive integer'
    try:
        number = int(string)
    except ValueError:
        raise argparse.ArgumentTypeError(msg) from None
    if number <= 0:
        raise argparse.ArgumentTypeError(msg)
    return number


def nonnegative_int_arg(string):
    """helper function to validate arguments that must be nonnegative integers

    Parameters
    ----------
    string : str
        String to check if it is a nonegative int

    Returns
    -------
    int
        The number in string if it is a nonnegative int

    Raises
    ------
    argparse.ArgumentTypeError
        If the number is not a nonnegative integer
    """
    msg = 'Must be a non-negative integer'
    try:
        number = int(string)
    except ValueError:
        raise argparse.ArgumentTypeError(msg) from None
    if number < 0:
        raise argparse.ArgumentTypeError(msg)
    return number


def list_string(string):
    """helper function to check that checks a string is alist

    Passes string to ast.literal_eval to parse, and if it cannot then it raises an error.

    Parameters
    ----------
    string : str
        The list to parse by ast.literal_eval

    Returns
    -------
    list
        The list parsed by ast.literal_eval

    Raises
    ------
    argparse.ArgumentTypeError
        If the string is not a list of list of ints
    """
    msg = 'Must be a string that can be formatted by ast.literal_eval into list[list[int]]'
    try:
        ret = literal_eval(string)
    except ValueError:
        raise argparse.ArgumentTypeError(msg) from None

    for i in ret:
        for j in i:
            if not isinstance(j, int):
                raise argparse.ArgumentTypeError(msg)

    return ret


def add_basic_args(parser):
    """adds basic arguments to parser

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    parser.add_argument(
        '--yaml', type=os.path.realpath, help='Path to yaml config file'
    )
    parser.add_argument('--name')
    parser.add_argument('--service', choices={'cluster', 'single'})
    parser.add_argument('--market', nargs='+', choices={'spot', 'on-demand'})


def add_job_args(parser):
    """adds job arguments to parser

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    common_grp = parser.add_argument_group('Common job arguments')
    common_grp.add_argument('--ram', type=list_string)
    common_grp.add_argument('--cpu', type=list_string)
    common_grp.add_argument('--ratio', type=list_string)
    common_grp.add_argument('--aws_role', '--aws-role')
    common_grp.add_argument('--disk', type=positive_int_arg)
    common_grp.add_argument('--valid_time', '--valid-time', type=positive_int_arg)
    common_grp.add_argument('--user_data', '--user-data', nargs='*')
    common_grp.add_argument('--gpu', action='store_true', dest='gpu_flag')


def add_action_args(parser):
    """add action arguments to the parser

    These don't create nor destroy jobs, but are used to do things on existing instances

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    action_grp = parser.add_argument_group('Action Arguments')
    action_grp.add_argument('--rsync_path', '--rsync-path')
    action_grp.add_argument('--run_cmd', '--run-cmd')
    action_grp.add_argument('--all', action='store_true', dest='rr_all')


def add_env_args(parser):
    """adds environment arguments to parser

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    env_cfg_grp = parser.add_argument_group('Environment config')
    env_cfg_grp.add_argument('--aws_profile', '--aws-profile')
    env_cfg_grp.add_argument('--aws_az', '--aws-az')
    env_cfg_grp.add_argument('--aws_act_num', '--aws-account-num')
    env_cfg_grp.add_argument('--aws_subnet', '--aws-subnet')
    env_cfg_grp.add_argument('--ec2_key', '--ec2-key')
    env_cfg_grp.add_argument('--aws_security_group', '--aws_security-group')
    env_cfg_grp.add_argument('--excluded_ec2s', '--excluded-ec2s', nargs='+', metavar='EC2_TYPE', default=list())
    env_cfg_grp.add_argument('--destroy_after_success', '--destroy-after-success', action='store_true', default=None)
    env_cfg_grp.add_argument('--destroy_after_failure', '--destroy-after-failure', action='store_true', default=None)
    env_cfg_grp.add_argument('--no_destroy_after_success', '--no-destroy-after-success', action='store_false',
                             dest='destroy_after_success', default=None)
    env_cfg_grp.add_argument('--no_destroy_after_failure', '--no-destroy-after-failure', action='store_false',
                             dest='destroy_after_failure', default=None)
    env_cfg_grp.add_argument('--forge_pem_secret', '--forge-pem-secret')


def add_general_args(parser, require_env=False):
    """adds general arguments to parser

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Argument parser for Forge.main
    """
    general_grp = parser.add_argument_group('General config')
    general_grp.add_argument('--date')
    general_grp.add_argument('--forge_env', '--forge-env', required=require_env, help='environment')
    general_grp.add_argument('--log_level', '--log-level', choices={'DEBUG', 'INFO', 'WARNING', 'ERROR'},
                             type=str.upper, help='Override logging level.')
    general_grp.add_argument('--config_dir', '--config-dir')
