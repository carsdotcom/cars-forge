"""Parse Forge config files."""
import logging
import os
import sys
import getpass

import yaml
from schema import Schema, And, Or, Use, Optional, SchemaError

from . import DEFAULT_ARG_VALS, ADDITIONAL_KEYS
from .configure import check_env_yaml
from .common import normalize_config, set_config_dir, check_keys, parse_additional_config

logger = logging.getLogger(__name__)



def non_negative_list_list_ints(raw_x):
    """check if input is a single or list of non-negative integers

    Parameters
    ----------
    raw_x : list
        List of values to check if valid

    Returns
    -------
    list
        Validated list of values

    Raises
    ------
    ValueError
        If raw_x is not a list, has a length greater than 2, or if the integers are less than 0
    """
    if not isinstance(raw_x, list):
        raise ValueError('Must be a list of list of ints')
    if len(raw_x) > 2:
        raise ValueError('Only 1 or 2 values allowed.')
    valid_x = []
    for i in raw_x:
        valid_y = []
        for j in i:
            j = int(j)
            if j < 0:
                raise ValueError(f'Each value must be a non-negative integer: {i}')
            valid_y.append(j)
        valid_x.append(sorted(valid_y))
    return valid_x


def check_user_yaml(user_yaml, additional_config: list = None):
    """validates the user yaml file

    Parameters
    ----------
    user_yaml : dict
        User configuration data
    additional_config : dict
        Additional configuration data to allow for dynamic validation

    Returns
    -------
    dict
        The validated user configuration data

    Raises
    ------
    schema.SchemaError
        If user_yaml does not pass validation
    """
    if not additional_config:
        additional_config = []

    positive_int = lambda x: x>0

    key = None
    def _key_check(x):
        """checks if x is a key allowed by additional_config

        Parameters
        ----------
        x : str
            Key to check against the additional_config

        Returns
        -------
        bool
            If x is a valid key in additional_config
        """
        nonlocal key
        key = x
        return x in [cfg['name'] for cfg in additional_config]

    def _is_constrained(x):
        """checks if x is a valid value for the key

        Parameters
        ----------
        x : str
            Value to check against key constraints

        Returns
        -------
        bool
            If x is a valid value in the key constraints
        """
        constraints = list(filter(lambda n: n['name'] == key, additional_config))[0]['constraints']
        if not constraints:
            return True

        return x in constraints

    def _get_type(x):
        """check that x is the type specified by the key

        Parameters
        ----------
        x : str
            Value to check the type of

        Returns
        -------
        bool
            Whether x is the type specified by key
        """
        type_str = list(filter(lambda n: n['name'] == key, additional_config))[0]['type']
        return isinstance(x, eval(type_str))

    logger.debug('additional_config: %s', additional_config)

    schema = Schema({
        Optional('ami'): And(str, len, error="Invalid user AMI"),
        Optional('aws_role'): And(str, len, error='Invalid IAM Role'),
        Optional('cpu'): And(list, error='Invalid CPU cores'),
        Optional('destroy_after_success'): And(bool),
        Optional('destroy_after_failure'): And(bool),
        Optional('disk'): And(Use(int), positive_int),
        Optional('disk_device_name'): And(str, len, error='Invalid Device Name'),
        Optional('forge_env'): And(str, len, error='Invalid Environment'),
        Optional('gpu_flag'): And(bool),
        Optional('market'): And(Or(str, list)),
        Optional('name'): And(str, len, error='Invalid Name'),
        Optional('ratio'): And(list),
        Optional('ram'): And(list, error='Invalid RAM'),
        Optional('rsync_path'): And(str),
        Optional('run_cmd'): And(str, len, error='Invalid run_cmd'),
        Optional('service'): And(str, len, Or('single', 'cluster'), error='Invalid Service'),
        Optional('user_data'): And(list),
        Optional('valid_time'): And(Use(int), positive_int),
        Optional('workers'): And(Use(int), positive_int),
        Optional('log_level'): And(
            Use(str.upper), Or('DEBUG', 'INFO', 'WARNING', 'ERROR'),
            error='Invalid log level'
        ),
        Optional(_key_check): And(
            _get_type, _is_constrained,
            error="An additional_config option did not meet constraints"
        )
    })
    try:
        validated = schema.validate(user_yaml)
        return validated
    except SchemaError as err:
        logger.error(err)
        sys.exit(1)


def load_config(args):
    """loads the environment and user configuration data

    Parameters
    ----------
    args : dict
        The args from Forge.main

    Returns
    -------
    dict
        Forge configuration data
    """
    try:
        with open(args['yaml']) as handle:
            logger.info('Opening user config file: %s', args['yaml'])
            user_config = yaml.safe_load(handle)
    except FileNotFoundError:
        logger.error('User config file not found: %s', args['yaml'])
        sys.exit(1)

    logger.info('Checking config file: %s', args['yaml'])
    logger.debug('Required User config is %s', user_config)
    env = args['forge_env'] or user_config.get('forge_env')

    if env is None:
        logger.error("'forge_env' variable required.")
        sys.exit(1)
    user_config['forge_env'] = env
    logger.debug('Environment is %s', env)

    src_dir = os.path.dirname(os.path.realpath(__file__))
    yaml_dir = os.path.dirname(args['yaml'])

    config_dir = set_config_dir(args, env)
    args['config_dir'] = config_dir

    env_config_path = f'{config_dir}/{env}.yaml'
    logger.info('Opening %s config file at %s.', env, env_config_path)
    try:
        with open(env_config_path) as handle:
            env_config = yaml.safe_load(handle)
            env_config = check_env_yaml(env_config)
    except FileNotFoundError:
        logger.error("Environment '%s' config file not found: %s", env, env_config_path)
        sys.exit(1)

    env_config.update(normalize_config(env_config))
    check_keys(env_config['region'], env_config.get('aws_profile'))

    additional_config_data = env_config.pop('additional_config', None)
    additional_config = []
    if additional_config_data:
        for i in additional_config_data:
            ADDITIONAL_KEYS.append(i['name'])
            additional_config.append(i)

    logger.debug('Additional config options: %s', additional_config)

    user_config = check_user_yaml(user_config, additional_config)
    env = args['forge_env'] or user_config.get('forge_env')

    env_config['config_dir'] = config_dir
    env_config = parse_additional_config(env_config, additional_config)

    logger.debug('Full user config options: %s', user_config)

    extra_config = {
        'src_dir': os.path.dirname(os.path.realpath(__file__)),
        'home_dir': os.path.dirname(src_dir),
        'yaml_dir': os.path.dirname(args['yaml']),
        'app_dir': os.path.dirname(yaml_dir),
        'user': getpass.getuser(),
        'date': args['date']
    }

    config = {**env_config, **extra_config, **user_config}

    config = normalize_config(config)

    # Any runtime parameters take precedence over config file parameters
    all_keys = set(args) | set(config) | set(DEFAULT_ARG_VALS)
    final_config = {
        k: i for k in all_keys for i in [DEFAULT_ARG_VALS.get(k), config.get(k), args.get(k)] if isinstance(i, bool) or bool(i)
    }
    # Except for 'excluded_ec2s' which is an additive parameter
    excluded_ec2s = config.get('excluded_ec2s', []) + args.get('excluded_ec2s', [])
    final_config['excluded_ec2s'] = sorted(set(excluded_ec2s))

    # Further customize the job role
    final_config['aws_role'] = final_config['aws_role'] = '-'.join(filter(None, ['forge', final_config['aws_role'], env]))

    logger.debug('Full configuration: %s', final_config)

    # Remove any parameters not present in config file nor passed at runtime
    # to allow setting default parameters later
    return {k: v for k, v in final_config.items() if v is not None}
