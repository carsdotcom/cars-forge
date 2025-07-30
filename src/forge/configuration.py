from dataclasses import dataclass, field
import getpass
import logging
import os
import sys
from typing import ForwardRef, Literal, Optional, Type, Union

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import yaml

from . import ADDITIONAL_KEYS, DEFAULT_ARG_VALS, REQUIRED_ARGS

logger = logging.getLogger(__name__)


MachineSpec = Union[list[Union[int, list[int]]]]
JobUnion = Literal['cleanup', 'create', 'destroy', 'engine', 'rsync', 'run', 'ssh', 'start', 'stop']


@dataclass
class Configuration:
    region: str
    ec2_amis: dict
    ec2_key: str
    forge_env: str
    forge_pem_secret: str
    job: JobUnion

    additional_config: Optional[list[dict]] = None
    ami: Optional[str] = None
    app_dir: Optional[str] = None
    aws_az: Optional[str] = None
    aws_imds_v2: Optional[bool] = None
    aws_imds_max_hops: Optional[int] = None
    aws_multi_az: Optional[dict] = None
    aws_profile: Optional[str] = None
    aws_region: Optional[str] = None
    aws_role: Optional[str] = None
    aws_security_group: Optional[list[str]] = None
    aws_subnet: Optional[str] = None
    config_dir: Optional[str] = None
    cpu: Optional[MachineSpec] = None
    create_timeout: Optional[int] = None
    date: Optional[str] = None
    destroy_after_success: Optional[bool] = DEFAULT_ARG_VALS['destroy_after_success']
    destroy_after_failure: Optional[bool] = DEFAULT_ARG_VALS['destroy_after_failure']
    destroy_on_create: Optional[bool] = None
    disk: Optional[int] = None
    disk_device_name: Optional[str] = None
    ec2_max: Optional[int] = DEFAULT_ARG_VALS['ec2_max']
    excluded_ec2s: Optional[list] = None
    gpu_flag: Optional[bool] = DEFAULT_ARG_VALS['gpu_flag']
    home_dir: Optional[str] = None
    log_level: Optional[Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']] = DEFAULT_ARG_VALS['log_level']
    market: Optional[Union[str, list[str]]] = field(default_factory=lambda: DEFAULT_ARG_VALS['market'])
    market_failover: Optional[bool] = None  # ToDo: Remove
    name: Optional[str] = None
    on_demand_failover: Optional[bool] = None
    ratio: Optional[MachineSpec] = None #field(default_factory=lambda: DEFAULT_ARG_VALS['default_ratio'])
    ram: Optional[MachineSpec] = None
    rr_all: Optional[bool] = None
    rsync_path: Optional[str] = None
    run_cmd: Optional[str] = None
    s3_path: Optional[str] = None
    service: Optional[Literal['single', 'cluster']] = None
    spot_retries: Optional[int] = None
    spot_strategy: Optional[Literal['lowest-price', 'diversified', 'capacity-optimized', 'capacity-optimized-prioritized', 'price-capacity-optimized']] = DEFAULT_ARG_VALS['spot_strategy']
    src_dir: Optional[str] = None
    tags: Optional[list[dict]] = None
    user: Optional[str] = None
    user_data: Optional[Union[dict, list]] = None
    valid_time: Optional[int] = DEFAULT_ARG_VALS['valid_time']
    workers: Optional[int] = None
    yaml: Optional[str] = None
    yaml_dir: Optional[str] = None

    def __post_init__(self):
        if self.spot_retries and self.spot_retries <= 0:
            raise ValueError('The number of spot retries must be greater than zero')

        if self.create_timeout and self.create_timeout <= 0:
            raise ValueError('The create timeout must be greater than zero')

        if self.disk and self.disk <= 0:
            raise ValueError('The disk size must be greater than zero')

        if self.valid_time and self.valid_time <= 0:
            raise ValueError('The valid must be greater than zero')

        if self.workers and self.workers <= 0:
            raise ValueError('The number of workers must be greater than zero')

    def __getitem__(self, item):
        return self.__dict__[item]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __repr__(self):
        return repr(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __delitem__(self, key):
        del self.__dict__[key]

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    def clone(self):
        tmp = Configuration(
            region=self.region,
            ec2_amis=self.ec2_amis,
            ec2_key=self.ec2_key,
            forge_env=self.forge_env,
            forge_pem_secret=self.forge_pem_secret,
            job=self.job,
        )

        tmp.update(self.__dict__)
        return tmp

    def copy(self):
        return self.__dict__.copy()

    def update(self, *args, **kwargs):
        return self.__dict__.update(*args, **kwargs)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    @staticmethod
    def load_config(
            cli_config: dict,
            user_config: Optional[dict] = None,
            env_config: Optional[dict] = None,
            additional_config: Optional[dict] = None) -> 'Configuration':
        src_dir = os.path.dirname(os.path.realpath(__file__))
        home_dir = os.path.dirname(src_dir)
        yaml_dir = None
        app_dir = None
        user = getpass.getuser()

        cli_config = {k: v for k, v in cli_config.items() if v is not None}

        # Load user config
        if not user_config:
            if user_yaml := cli_config.get('yaml'):
                try:
                    with open(user_yaml, 'r') as f:
                        logger.info('Opening user config file: %s', user_yaml)
                        user_config = yaml.safe_load(f)

                    yaml_dir = os.path.dirname(user_yaml)
                    app_dir = os.path.dirname(yaml_dir)
                except FileNotFoundError:
                    logger.error('User config file not found: %s', user_yaml)
                    sys.exit(1)
            else:
                logger.warning('No user config provided, continuing with CLI arguments')
                user_config = {}

        config_dict = {**user_config, **cli_config}

        # Load environmental config
        if not env_config:
            if forge_env := config_dict.get('forge_env'):
                logger.debug('Environment is %s', forge_env)

                # ToDo: Set config_dir based on XDG directories
                if config_dir := config_dict.get('config_dir'):
                    config_dir = os.path.join(config_dir, forge_env)
                else:
                    config_dir = f'{src_dir}/config/{forge_env}'

                config_dict['config_dir'] = config_dir

                env_yaml = f'{config_dir}/{forge_env}.yaml'

                try:
                    with open(env_yaml, 'r') as f:
                        logger.info('Opening %s config file at %s.', forge_env, env_yaml)
                        env_config = yaml.safe_load(f)
                except FileNotFoundError:
                    logger.error("Environment '%s' config file not found: %s", forge_env, env_yaml)
                    sys.exit(1)
            else:
                logger.error('No forge environment specified, exiting...')
                sys.exit(1)

        config_dict = {**env_config, **config_dict}

        # Get additional config options
        if not additional_config:
            additional_config = {}

            if additional_config_schema := config_dict.pop('additional_config', []):
                for i in additional_config_schema:
                    adc_name: str = i['name']
                    # ToDo: Figure out better way to check type
                    adc_type: Type = ForwardRef(i['type'])._evaluate(globals(), locals(), frozenset())
                    adc_default: Optional[adc_type] = i.get('default')
                    adc_constraints: list = i.get('constraints', [])

                    ADDITIONAL_KEYS.append(adc_name)

                    val: Optional[adc_type] = config_dict.pop(adc_name, adc_default)

                    if adc_constraints and val not in adc_constraints:
                        raise ValueError('Additional config option %s does not match constraints: %s', adc_name, val)

                    additional_config[adc_name] = val

        # Set configuration extras
        config_dict = {**config_dict, **{
            'src_dir': src_dir,
            'home_dir': home_dir,
            'yaml_dir': yaml_dir,
            'app_dir': app_dir,
            'user': user
        }}

        # Config normalization
        aws_az = config_dict.get('aws_az')
        aws_region = config_dict.get('aws_region')
        aws_multi_az = config_dict.get('aws_multi_az')
        aws_subnet = config_dict.get('aws_subnet')
        aws_security_group = config_dict.get('aws_security_group')

        cpu = config_dict.get('cpu')
        ram = config_dict.get('ram')
        ratio = config_dict.get('ratio')
        ec2_max = config_dict.get('ec2_max')

        if aws_az and aws_multi_az:
            logger.warning('The config options aws_az and aws_multi_az are mutually exclusive, defaulting to aws_az')
        elif not aws_az and not aws_multi_az:
            logger.error('Either aws_az or aws_multi_az must be set, aborting...')
            sys.exit(1)

        if aws_az:
            config_dict['region'] = aws_az[:-1]

            if aws_subnet:
                config_dict['aws_multi_az'] = {aws_az: aws_subnet}
            elif not aws_multi_az:
                logger.error('aws_az set without aws_subnet or aws_multi_az options, aborting...')
                sys.exit(1)
        elif aws_subnet:
            logger.warning('Both aws_multi_az and aws_subnet exist, defaulting to aws_multi_az')

        if aws_region:
            config_dict['region'] = aws_region

        if aws_security_group:
            if isinstance(aws_security_group, str):
                config_dict['aws_security_group'] = [aws_security_group]

        def _parse_list(option):
            """Parse a list option.

            Parameters
            ----------
            option : str or list
                Option value to be parsed. Can be an actual list of lists or a list of
                comma-joined list values.

            Returns
            -------
            list of list
                Parsed option as a list of lists.
            """
            if option is None:
                return option
            option = [
                list(map(int, opt.split(','))) if isinstance(opt, str) else opt for opt in option
            ]
            option = [opt if isinstance(opt, list) else [opt] for opt in option]
            return option

        if not ram and not cpu:
            if ratio:
                DEFAULT_ARG_VALS['default_ratio'] = ratio

            if ec2_max:
                DEFAULT_ARG_VALS['ec2_max'] = ec2_max
        else:
            if ram := _parse_list(ram):
                config_dict['ram'] = ram

            if cpu := _parse_list(cpu):
                config_dict['cpu'] = cpu

            if ratio := _parse_list(ratio):
                config_dict['ratio'] = ratio

            market = config_dict.get('market')
            if market and isinstance(market, str):
                config_dict['market'] = list(map(str.strip, market.split(',')))

            if service := config_dict.get('service'):
                min_values = 1 if service == 'single' else 2

                if ram and len(ram) != min_values:
                    logger.error('ram must have %s values for service %s', min_values, service)
                    sys.exit(1)
                if cpu and len(cpu) != min_values:
                    logger.error('cpu must have %s values for service %s', min_values, service)
                    sys.exit(1)
                if ratio and len(ratio) != min_values:
                    logger.error('ratio must have %s values for service %s', min_values, service)
                    sys.exit(1)

        # Random checks and transformations to conform to Forge's quirks
        if excluded_ec2s := cli_config.get('excluded_ec2s'):
            config_dict['excluded_ec2s'] = list(sorted(set(config_dict['excluded_ec2s'] + cli_config['excluded_ec2s'])))

        if not config_dict.get('aws_role'):
            logger.warning('No aws_role specified, continuing...')
        else:
            config_dict['aws_role'] = '-'.join(filter(None, ['forge', config_dict['aws_role'], forge_env]))

        # Create configuration
        config = Configuration(**config_dict)

        # Add additional config options
        for k, v in additional_config.items():
            config[k] = v

        return config

    def validate(self) -> bool:
        return self.validate_aws_permissions() and self.validate_job_args()

    def validate_job_args(self) -> bool:
        if self.job in ['create', 'destroy', 'engine', 'rsync', 'run', 'ssh', 'start', 'stop']:
            for requisite in REQUIRED_ARGS[self.job]:
                if not self[requisite]:
                    logger.error('Missing required argument "%s" for job "%s"', requisite, self.job)
                    return False

        return True

    def validate_aws_permissions(self) -> bool:
        try:
            region = self.aws_region
            profile = self.aws_profile

            if profile:
                session = boto3.session.Session(profile_name=profile, region_name=region)
            else:
                session = boto3.session.Session(region_name=region)

            session.client('sts').get_caller_identity()

            return True
        except NoCredentialsError:
            logger.error("Missing AWS credentials to run Forge")
        except ClientError:
            logger.error("Invalid AWS credentials to run Forge")

        return False
