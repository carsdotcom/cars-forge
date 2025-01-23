"""Tests for the main entrypoint module of Forge."""
# pylint: disable=W0621
import os
from unittest import mock
from xmlrpc.client import Fault

import pytest
import yaml

from forge import main


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
            cfg['excluded_ec2s'] = sorted(cfg['excluded_ec2s'])
        return cfg
    return _load_admin_cfg


@mock.patch('forge.yaml_loader.set_config_dir')
@mock.patch('forge.yaml_loader.check_keys')
@mock.patch('forge.main.execute')
@mock.patch('forge.yaml_loader.getpass', autospec=True)
@pytest.mark.parametrize('cli_call,exp_config', [
    # Destroy job; passing the absolute path to a yaml
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml')],
     {'name': 'test-single-intermediate', 'log_level': 'INFO',
      'yaml': os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'),
      'service': 'single', 'market': ['spot'], 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'destroy', 'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'forge_version': False, 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'),
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True, 'default_ratio': [8, 8],
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized', 'rr_all': False}),
    # Destroy job; passing the relative path to a yaml
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR_REL, 'data', 'single_intermediate.yaml')],
     {'name': 'test-single-intermediate', 'log_level': 'INFO',
      'yaml': os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'), 'service': 'single', 'market': ['spot'],
      'ram': [[64]], 'aws_role': 'forge-test_role-dev', 'run_cmd': 'dummy.sh dev test', 'job': 'destroy',
      'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR, 'home_dir': os.path.dirname(FORGE_DIR),
      'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user', 'ami': 'single_ami',
      'forge_version': False, 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'), 'region': 'us-east-1',
      'destroy_after_success': True, 'destroy_after_failure': True, 'default_ratio': [8, 8], 'valid_time': 8,
      'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized', 'rr_all': False}),
    # Destroy job; overriding log_level
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'), '--log_level', 'debug'],
     {'name': 'test-single-intermediate', 'log_level': 'DEBUG',
      'yaml': os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'),
      'service': 'single', 'market': ['spot'], 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'destroy', 'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'forge_version': False, 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'),
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True, 'default_ratio': [8, 8],
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized', 'rr_all': False}),
    # Destroy job; overriding market
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'),
      '--market', 'on-demand'],
     {'name': 'test-single-intermediate', 'log_level': 'INFO',
      'yaml': os.path.join(TEST_DIR, 'data', 'single_intermediate.yaml'), 'service': 'single', 'market': ['on-demand'],
      'ram': [[64]], 'aws_role': 'forge-test_role-dev', 'run_cmd': 'dummy.sh dev test', 'job': 'destroy',
      'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR, 'home_dir': os.path.dirname(FORGE_DIR),
      'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user', 'ami': 'single_ami', 'forge_version': False,
      'config_dir': os.path.join(TEST_CFG_DIR, 'dev'), 'region': 'us-east-1', 'destroy_after_success': True,
      'destroy_after_failure': True, 'default_ratio': [8, 8], 'valid_time': 8, 'ec2_max': 768,
      'spot_strategy': 'price-capacity-optimized', 'rr_all': False}),
    # Destroy job; no market
    (['forge', 'destroy', '--yaml', os.path.join(TEST_DIR, 'data', 'single_basic.yaml'), '--forge_env', 'dev'],
     {'name': 'test-single-basic', 'log_level': 'INFO', 'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'service': 'single', 'market': ['spot', 'spot'], 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'destroy', 'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'forge_version': False, 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'),
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True, 'default_ratio': [8, 8],
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized', 'rr_all': False}),
    # Configure job
    (['forge', 'configure'],
     {'forge_version': False, 'job': 'configure', 'log_level': 'INFO'}),
    # Create job with ram range
    (['forge', 'create', '--yaml', os.path.join(TEST_DIR, 'data', 'single_basic.yaml'), '--ram', '[[10, 20]]',
      '--forge_env', 'dev'],
     {'name': 'test-single-basic', 'log_level': 'INFO', 'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'service': 'single', 'market': ['spot', 'spot'], 'ram': [[10, 20]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'create', 'gpu_flag': False, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'forge_version': False, 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'),
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True, 'default_ratio': [8, 8],
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized', 'rr_all': False}),
    # Create job; setting gpu
    (['forge', 'create', '--yaml', os.path.join(TEST_DIR, 'data', 'single_basic.yaml'), '--forge_env', 'dev', '--gpu'],
     {'name': 'test-single-basic', 'log_level': 'INFO', 'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'service': 'single', 'market': ['spot', 'spot'], 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'job': 'create', 'gpu_flag': True, 'app_dir': TEST_DIR, 'src_dir': FORGE_DIR,
      'home_dir': os.path.dirname(FORGE_DIR), 'yaml_dir': os.path.join(TEST_DIR, 'data'), 'user': 'test_user',
      'ami': 'single_ami', 'forge_version': False, 'config_dir': os.path.join(TEST_CFG_DIR, 'dev'),
      'region': 'us-east-1', 'destroy_after_success': True, 'destroy_after_failure': True, 'default_ratio': [8, 8],
      'valid_time': 8, 'ec2_max': 768, 'spot_strategy': 'price-capacity-optimized', 'rr_all': False}),
])
def test_forge_main(mock_pass, mock_execute, mock_keys, mock_config_dir, cli_call, exp_config, load_admin_cfg):
    """Test the config after calling forge via the command line."""
    mock_config_dir.return_value = os.path.join(
        TEST_DIR, 'data', 'admin_configs', 'dev'
    )
    # Loading dev admin configs except for configure job which does not need it
    if cli_call[1] not in {'configure',}:
        exp_config.update(load_admin_cfg('dev'))

        # Parses the additional_config as this is parsed during load_config,
        # but Mock.assert_called_with will not be able to parse it, so we must
        # do so beforehand. All this requires is setting the default values if they exist.
        for i in exp_config.pop('additional_config'):
            if i['default']:
                exp_config[i['name']] = i['default']

    mock_pass.getuser.return_value = 'test_user'

    with mock.patch('sys.argv', cli_call):
        main.main()

    mock_execute.assert_called_once_with(exp_config)
    if cli_call[1] not in {'configure',}:
        mock_keys.assert_called_once()


@pytest.mark.parametrize('cli_call,exp_error', [
    (['forge', 'create'],
     [('root', 40, 'Missing key "name" in args')]),
    (['forge', 'destroy', '--name', 'test'],
     [('root', 40, 'Missing key "service" in args')]),
    (['forge', 'rsync', '--name', 'test', '--service', 'single'],
     [('root', 40, 'Missing key "forge_env" in args')]),
    (['forge', 'run', '--name', 'test', '--service', 'single', '--forge_env', 'test'],
     [('root', 40, 'Missing key "run_cmd" in args')])
])
def test_forge_main_errors(cli_call, exp_error, caplog):
    """Test calling forge via the command line with bad arguments."""
    with pytest.raises(SystemExit):
        with mock.patch('sys.argv', cli_call):
            main.main()

    for record in caplog.records:
        assert 'ERROR' == record.levelname

    assert caplog.record_tuples == exp_error
