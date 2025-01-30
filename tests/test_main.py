"""Tests for the main entrypoint module of Forge."""
# pylint: disable=W0621
import os
from unittest import mock

import pytest
import yaml

from forge import main
from forge.configuration import Configuration


TEST_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_CFG_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'data', 'admin_configs'
)
TEST_DIR_REL = os.path.dirname(os.path.relpath(__file__))
FORGE_DIR = os.path.dirname(os.path.realpath(main.__file__))

@pytest.fixture
def load_admin_cfg():
    """Helper function to load the admin configs for the specified environment."""
    def _load_admin_cfg(env):
        path = os.path.join(TEST_CFG_DIR, env, f'{env}.yaml')
        with open(path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        if 'excluded_ec2s' in cfg:
            cfg['excluded_ec2s'] = cfg['excluded_ec2s']
        return cfg
    return _load_admin_cfg


@mock.patch('forge.configuration.Configuration.validate')
@mock.patch('forge.main.execute')
@mock.patch('forge.configuration.getpass', autospec=True)
@pytest.mark.parametrize('cli_call,exp_config', [
    # Destroy job; passing the absolute path to a yaml
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml')],
     {'name': 'test-single-intermediate', 'log_level': 'INFO',
      'yaml': os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'),
      'service': 'single', 'market': ['spot'], 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'destroy', 'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'),
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True,
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized'}),
    # Destroy job; passing the relative path to a yaml
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR_REL, 'data', 'single_intermediate.yaml')],
     {'name': 'test-single-intermediate', 'log_level': 'INFO',
      'yaml': os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'), 'service': 'single', 'market': ['spot'],
      'ram': [[64]], 'aws_role': 'forge-test_role-dev', 'run_cmd': 'dummy.sh dev test', 'job': 'destroy',
      'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR, 'home_dir': os.path.dirname(FORGE_DIR),
      'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user', 'ami': 'single_ami',
      'config_dir': os.path.join(TEST_CFG_DIR, 'dev'), 'region': 'us-east-1', 'additional_config': None,
      'destroy_after_success': True, 'destroy_after_failure': True, 'valid_time': 8,
      'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized'}),
    # Destroy job; overriding log_level
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'), '--log_level', 'debug'],
     {'name': 'test-single-intermediate', 'log_level': 'DEBUG',
      'yaml': os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'),
      'service': 'single', 'market': ['spot'], 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'destroy', 'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'), 'additional_config': None,
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True,
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized'}),
    # Destroy job; overriding market
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'),
      '--market', 'on-demand'],
     {'name': 'test-single-intermediate', 'log_level': 'INFO',
      'yaml': os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'), 'service': 'single', 'market': ['on-demand'],
      'ram': [[64]], 'aws_role': 'forge-test_role-dev', 'run_cmd': 'dummy.sh dev test', 'job': 'destroy',
      'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR, 'home_dir': os.path.dirname(FORGE_DIR),
      'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user', 'ami': 'single_ami', 'additional_config': None,
      'config_dir': os.path.join(TEST_CFG_DIR, 'dev'), 'region': 'us-east-1', 'destroy_after_success': True,
      'destroy_after_failure': True, 'valid_time': 8, 'ec2_max': 768,
      'spot_strategy': 'price-capacity-optimized'}),
    # Destroy job; no market
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR, 'data', 'single_basic.yaml'), '--forge_env', 'dev'],
     {'name': 'test-single-basic', 'log_level': 'INFO', 'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'service': 'single', 'market': ['spot', 'spot'], 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'destroy', 'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'), 'additional_config': None,
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True,
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized'}),
    # Configure job
    (['forge', 'configure'],
     {'job': 'configure', 'log_level': 'INFO'}),
    # Create job with ram range
    (['forge', 'create', '--yaml', os.path.join(TEST_DIR, 'data', 'single_basic.yaml'), '--ram', '[[10, 20]]',
      '--forge_env', 'dev'],
     {'name': 'test-single-basic', 'log_level': 'INFO', 'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'service': 'single', 'market': ['spot', 'spot'], 'ram': [[10, 20]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'create', 'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'), 'additional_config': None,
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True,
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized'}),
    # Create job; setting gpu
    (['forge', 'create', '--yaml', os.path.join(TEST_DIR, 'data', 'single_basic.yaml'), '--forge_env', 'dev', '--gpu'],
     {'name': 'test-single-basic', 'log_level': 'INFO', 'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'service': 'single', 'market': ['spot', 'spot'], 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'create', 'gpu_flag': True, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'), 'additional_config': None,
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True,
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized'}),
])
def test_forge_main(mock_pass, mock_execute, mock_validation, cli_call, exp_config, load_admin_cfg):
    """Test the config after calling forge via the command line."""
    # Loading dev admin configs except for configure job which does not need it
    if cli_call[1] not in {'configure',}:
        cli_call += ['--config-dir', os.path.join(TEST_DIR, 'data', 'admin_configs')]

        exp_config.update(load_admin_cfg('dev'))

        additional_config = exp_config.pop('additional_config')

        exp_config = Configuration(**exp_config)

        # Parses the additional_config as this is parsed during load_config,
        # but Mock.assert_called_with will not be able to parse it, so we must
        # do so beforehand. All this requires is setting the default values if they exist.
        for i in additional_config:
            if i['default'] is not None:
                exp_config[i['name']] = i['default']

    mock_pass.getuser.return_value = 'test_user'

    with mock.patch('sys.argv', cli_call):
        main.main()

    mock_execute.assert_called_once_with(exp_config)
    if cli_call[1] not in {'configure',}:
        mock_validation.assert_called_once()

@pytest.mark.parametrize('cli_call,exp_error', [
    (['forge', 'run'],
     [
         ('forge.configuration', 30, 'No user config provided, continuing with CLI arguments'),
         ('forge.configuration', 40, 'No forge environment specified, exiting...'),
     ]),
    (['forge', 'destroy', '--forge-env', 'dev'],
     [
         ('forge.configuration', 30, 'No user config provided, continuing with CLI arguments'),
         ('forge.configuration', 40, f'Environment \'dev\' config file not found: {os.path.join(FORGE_DIR, "config", "dev", "dev.yaml")}')
     ]),
    (['forge', 'rsync', '--forge-env', 'dev', '--config-dir', os.path.join(TEST_DIR, 'data', 'admin_configs')],
     [
         ('forge.configuration', 30, 'No user config provided, continuing with CLI arguments'),
         ('forge.configuration', 20, f'Opening dev config file at {os.path.join(TEST_DIR, "data", "admin_configs", "dev", "dev.yaml")}.'),
         ('forge.configuration', 30, 'No aws_role specified, continuing...'),
         ('forge.configuration', 40, 'Missing required argument "name" for job "rsync"')
     ]),
    (['forge', 'create', '--forge-env', 'dev', '--config-dir', os.path.join(TEST_DIR, 'data', 'admin_configs'),
      '--name', 'test'],
     [
         ('forge.configuration', 30, 'No user config provided, continuing with CLI arguments'),
         ('forge.configuration', 20, f'Opening dev config file at {os.path.join(TEST_DIR, "data", "admin_configs", "dev", "dev.yaml")}.'),
         ('forge.configuration', 30, 'No aws_role specified, continuing...'),
         ('forge.configuration', 40, 'Missing required argument "service" for job "create"')
     ]),
    (['forge', 'create', '--forge-env', 'dev', '--config-dir', os.path.join(TEST_DIR, 'data', 'admin_configs'),
      '--name', 'test', '--service', 'single'],
     [
         ('forge.configuration', 30, 'No user config provided, continuing with CLI arguments'),
         ('forge.configuration', 20, f'Opening dev config file at {os.path.join(TEST_DIR, "data", "admin_configs", "dev", "dev.yaml")}.'),
         ('forge.configuration', 30, 'No aws_role specified, continuing...'),
         ('forge.configuration', 40, 'Missing required argument "aws_role" for job "create"')
     ]),
    (['forge', 'create', '--forge-env', 'dev', '--config-dir', os.path.join(TEST_DIR, 'data', 'admin_configs'),
      '--name', 'test', '--service', 'single', '--aws-role', 'test', '--no-destroy-after-failure'],
     [
         ('forge.configuration', 30, 'No user config provided, continuing with CLI arguments'),
         ('forge.configuration', 20, f'Opening dev config file at {os.path.join(TEST_DIR, "data", "admin_configs", "dev", "dev.yaml")}.'),
         ('forge.create', 40, 'Invalid configuration, either ram or cpu must be provided.')
     ]),
    (['forge', 'create', '--forge-env', 'dev', '--config-dir', os.path.join(TEST_DIR, 'data', 'admin_configs'),
      '--name', 'test', '--service', 'single', '--aws-role', 'test', '--ram', '[[4],[8]]', '--no-destroy-after-failure'],
     [
         ('forge.configuration', 30, 'No user config provided, continuing with CLI arguments'),
         ('forge.configuration', 20,
          f'Opening dev config file at {os.path.join(TEST_DIR, "data", "admin_configs", "dev", "dev.yaml")}.'),
         ('forge.configuration', 40, 'ram must have 1 values for service single')
     ]),
    (['forge', 'create', '--forge-env', 'dev', '--config-dir', os.path.join(TEST_DIR, 'data', 'admin_configs'),
      '--name', 'test', '--service', 'cluster', '--aws-role', 'test', '--ram', '[[4]]', '--no-destroy-after-failure'],
     [
         ('forge.configuration', 30, 'No user config provided, continuing with CLI arguments'),
         ('forge.configuration', 20,
          f'Opening dev config file at {os.path.join(TEST_DIR, "data", "admin_configs", "dev", "dev.yaml")}.'),
         ('forge.configuration', 40, 'ram must have 2 values for service cluster')
     ]),
])
def test_forge_main_errors(cli_call, exp_error, caplog):
    """Test calling forge via the command line with bad arguments."""
    with pytest.raises(SystemExit):
        with mock.patch('sys.argv', cli_call):
            main.main()

    assert caplog.record_tuples == exp_error
