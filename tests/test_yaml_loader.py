"""Tests for the config loader module of Forge."""
import logging
import os
from unittest import mock

import pytest

from forge import yaml_loader

from src.forge.yaml_loader import non_negative_list_list_ints

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
FORGE_DIR = os.path.dirname(os.path.realpath(yaml_loader.__file__))


@pytest.mark.parametrize('user_yaml,expected', [
    # Input/ouput pairs of config dicts
    # Single required-only configs with destroy
    ({'name': 'test-run', 'service': 'single', 'ram': [[64]], 'aws_role': 'aws_user', 'forge_env': 'dev',
      'run_cmd': 'dummy.sh dev test', 'destroy_after_success': True, 'ami': 'test_ami'},
     {'name': 'test-run', 'service': 'single', 'ram': [[64]], 'aws_role': 'aws_user', 'forge_env': 'dev',
      'run_cmd': 'dummy.sh dev test', 'destroy_after_success': True, 'ami': 'test_ami'}),
    # Single required-only configs with destroy and ram range
    ({'name': 'test-run', 'service': 'single', 'ram': [[32, 64]], 'aws_role': 'aws_user', 'forge_env': 'dev',
      'run_cmd': 'dummy.sh dev test', 'destroy_after_success': True, 'ami': 'test_ami'},
     {'name': 'test-run', 'service': 'single', 'ram': [[32, 64]], 'aws_role': 'aws_user', 'forge_env': 'dev',
      'run_cmd': 'dummy.sh dev test', 'destroy_after_success': True, 'ami': 'test_ami'}),
    # Single required-only configs
    ({'name': 'test-run', 'service': 'single', 'ram': [[64]], 'aws_role': 'aws_user', 'forge_env': 'dev',
      'run_cmd': 'dummy.sh dev test', 'ami': 'test_ami'},
     {'name': 'test-run', 'service': 'single', 'ram': [[64]], 'aws_role': 'aws_user', 'forge_env': 'dev',
      'run_cmd': 'dummy.sh dev test', 'ami': 'test_ami'}),
    # Single full configs with some parameters passed as strings
    ({'name': 'test-run', 'service': 'single', 'ram': [[64]], 'aws_role': 'aws_user',
      'run_cmd': 'dummy.sh dev test', 'forge_env': 'dev', 'cpu': [[8]], 'disk': 32,
      'valid_time': 12, 'user_data': ['/path/to/startup/script.sh'],
      'rsync_path': '/path/to/dummy.sh', 'gpu_flag': False, 'log_level': 'info', 'ami': 'test_ami'},
     {'name': 'test-run', 'service': 'single', 'ram': [[64]], 'aws_role': 'aws_user',
      'run_cmd': 'dummy.sh dev test', 'forge_env': 'dev', 'cpu': [[8]], 'disk': 32,
      'valid_time': 12, 'user_data': ['/path/to/startup/script.sh'],
      'rsync_path': '/path/to/dummy.sh', 'gpu_flag': False, 'log_level': 'INFO', 'ami': 'test_ami'}),
    # cluster required-only configs
    ({'name': 'test-run', 'service': 'cluster', 'ram': [[8], [512]], 'aws_role': 'aws_user', 'forge_env': 'dev',
      'run_cmd': 'dummy.sh dev test', 'ami': 'test_ami'},
     {'name': 'test-run', 'service': 'cluster', 'ram': [[8], [512]], 'aws_role': 'aws_user', 'forge_env': 'dev',
      'run_cmd': 'dummy.sh dev test', 'ami': 'test_ami'}),
    # cluster full configs with some parameters passed as strings
    ({'name': 'test-run', 'service': 'cluster', 'ram': [[8], [512]], 'aws_role': 'aws_user',
      'run_cmd': 'dummy.sh dev test', 'forge_env': 'dev', 'version': 2.3,
      'pip': ['pandas', 'numpy'], 'disk': 32, 'valid_time': 12,
      'user_data': ['/path/to/startup/script.sh'], 'rsync_path': '/path/to/dummy.sh',
      'log_level': 'info', 'ami': 'test_ami'},
     {'name': 'test-run', 'service': 'cluster', 'ram': [[8], [512]], 'aws_role': 'aws_user',
      'run_cmd': 'dummy.sh dev test', 'forge_env': 'dev', 'version': 2.3,
      'pip': ['pandas', 'numpy'], 'disk': 32, 'valid_time': 12,
      'user_data': ['/path/to/startup/script.sh'], 'rsync_path': '/path/to/dummy.sh',
      'log_level': 'INFO', 'ami': 'test_ami'}),
    # cluster full configs with some parameters passed as strings, master as list
    ({'name': 'test-run', 'service': 'cluster', 'ram': [[8], [512]], 'aws_role': 'aws_user',
      'run_cmd': 'dummy.sh dev test', 'forge_env': 'dev', 'version': 2.3,
      'pip': ['pandas', 'numpy'], 'disk': 32, 'valid_time': 12,
      'user_data': ['/path/to/startup/script.sh'], 'rsync_path': '/path/to/dummy.sh',
      'log_level': 'info', 'ami': 'test_ami'},
     {'name': 'test-run', 'service': 'cluster', 'ram': [[8], [512]], 'aws_role': 'aws_user',
      'run_cmd': 'dummy.sh dev test', 'forge_env': 'dev', 'version': 2.3,
      'pip': ['pandas', 'numpy'], 'disk': 32, 'valid_time': 12,
      'user_data': ['/path/to/startup/script.sh'], 'rsync_path': '/path/to/dummy.sh',
      'log_level': 'INFO', 'ami': 'test_ami'}),
])
def test_check_user_yaml_valid(user_yaml, expected):
    """Test checking of valid user configs."""
    additional_config = [
        {'name': 'pip', 'type': 'list', 'default': [], 'constraints': [], 'error': ''},
        {'name': 'version', 'type': 'float', 'default': 2.3, 'constraints': [2.3, 3.0, 3.1],
         'error': 'Invalid Spark version. Only 2.3, 3.0 and 3.1 are supported.'}
    ]

    actual = yaml_loader.check_user_yaml(user_yaml, additional_config=additional_config)
    assert actual == expected


@mock.patch('forge.yaml_loader.sys.exit')
@pytest.mark.parametrize('bad_config,error_msg', [
    # Invalid config option and expected error message pairs
    ({'name': ''}, 'Invalid Name'),
    ({'cpu': -5}, 'Invalid CPU cores'),
    ({'version': 'aaa'}, 'An additional_config option did not meet constraints'),
])
def test_check_user_yaml_invalid(mock_exit, bad_config, error_msg, caplog):
    """Test that invalid user configs raise errors."""
    user_config = {
        'name': 'test-run', 'service': 'single', 'ram': [64], 'aws_role': 'aws_user',
        'run_cmd': 'dummy.sh dev test'
    }

    additional_config = [
        {'name': 'pip', 'type': 'list', 'default': [], 'constraints': [], 'error': ''},
        {'name': 'version', 'type': 'float', 'default': 2.3, 'constraints': [2.3, 3.0, 3.1],
         'error': 'Invalid Spark version. Only 2.3, 3.0 and 3.1 are supported.'}
    ]

    user_config.update(bad_config)

    actual = yaml_loader.check_user_yaml(user_config, additional_config=additional_config)

    assert actual is None
    assert caplog.record_tuples == [('forge.yaml_loader', logging.ERROR, error_msg)]
    mock_exit.assert_called_once_with(1)


@mock.patch('forge.yaml_loader.set_config_dir')
@mock.patch('forge.yaml_loader.check_keys')
@pytest.mark.parametrize('args,expected', [
    # Job with no runtime overrides
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_full.yaml'),
      'date': '2021-01-01', 'forge_env': None},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'cpu': [[8]], 'disk': 32, 'valid_time': 3,
      'user_data': ['/path/to/startup/script.sh'], 'market': ['spot'],
      'rsync_path': '/path/to/dummy.sh', 'gpu_flag': False, 'log_level': 'INFO'}),
    # Job with runtime override of 'log_level' parameter from single_full.yaml
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_full.yaml'),
      'date': '2021-01-01', 'forge_env': None, 'log_level': 'ERROR'},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'cpu': [[8]], 'disk': 32, 'valid_time': 3,
      'user_data': ['/path/to/startup/script.sh'], 'market': ['spot'],
      'rsync_path': '/path/to/dummy.sh', 'gpu_flag': False, 'log_level': 'ERROR'}),
    # Job with runtime override of 'cpu' parameter from single_full.yaml
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_full.yaml'),
      'date': '2021-01-01', 'forge_env': None, 'cpu': [[16]]},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'cpu': [[16]], 'disk': 32, 'valid_time': 3,
      'user_data': ['/path/to/startup/script.sh'], 'market': ['spot'],
      'rsync_path': '/path/to/dummy.sh', 'gpu_flag': False, 'log_level': 'INFO'}),
    # Job with runtime setting of 'env' parameter
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'date': '2021-01-01', 'forge_env': 'dev'},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test'}),
    # Job with runtime setting of 'destroy' parameter
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'date': '2021-01-01', 'forge_env': 'dev', 'destroy_after_success': True},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'destroy_after_success': True}),
    # Job with no runtime override and destroy parameter
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_basic_destroy.yaml'),
      'date': '2021-01-01', 'forge_env': 'dev'},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'destroy_after_success': True}),
    # Job with runtime override of 'excluded_ec2s' parameter from dev.yaml
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'date': '2021-01-01', 'forge_env': 'dev',
      'excluded_ec2s': ['a.b.c', 't2.medium', 'd.e.f']},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test',
      'excluded_ec2s': ['*g.*', '*metal*', 'a.b.c', 'd.e.f', 'g4ad*', 'gd.*', 'm4.large', 't2.large', 't2.medium']}),
    # Job with runtime override of 'gpu_flag' parameter from single_full.yaml
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_full.yaml'),
      'date': '2021-01-01', 'forge_env': 'dev', 'gpu_flag': True},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'cpu': [[8]], 'disk': 32, 'valid_time': 3,
      'user_data': ['/path/to/startup/script.sh'], 'market': ['spot'],
      'rsync_path': '/path/to/dummy.sh', 'gpu_flag': True, 'log_level': 'INFO'}),
    # Job with no runtime overrides and gpu instance
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_basic_gpu.yaml'),
      'date': '2021-01-01', 'forge_env': 'dev'},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'gpu_flag': True}),
    # Job with no runtime overrides and on-demand instance
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_basic_ondemand.yaml'),
      'date': '2021-01-01', 'forge_env': 'dev'},
     {'forge_env': 'dev', 'service': 'single', 'ram': [[64]], 'aws_role': 'forge-test_role-dev',
      'run_cmd': 'dummy.sh dev test', 'market': ['on-demand']}),
])
def test_load_config(mock_keys, mock_config_dir, args, expected):
    """Test loading of forge configuration with some runtime overrides."""
    mock_config_dir.return_value = os.path.join(
        TEST_DIR, 'data', 'admin_configs', 'dev'
    )
    actual = yaml_loader.load_config(args)

    for k, v in expected.items():
        assert actual[k] == v

    mock_keys.assert_called_once()
    mock_config_dir.assert_called_once_with(args, 'dev')


@mock.patch('forge.yaml_loader.getpass', autospec=True)
@pytest.mark.parametrize('args,exp_error', [
    # Passing an invalid yaml path
    ({'yaml': '/path/to/non-existent.yaml',
      'date': '2021-01-01', 'forge_env': 'dev', 'log_level': 'INFO',
      'aws_role': 'foo-bar'},
      'User config file not found: /path/to/non-existent.yaml'),
    # No 'forge_env' variable
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'date': '2021-01-01', 'forge_env': None, 'log_level': 'INFO'},
      "'forge_env' variable required."),
    # Passing an invalid environment name
    ({'yaml': os.path.join(TEST_DIR, 'data', 'single_basic.yaml'),
      'date': '2021-01-01', 'forge_env': 'foo', 'log_level': 'INFO',
      'aws_role': 'foo-bar'},
      f"Environment 'foo' config file not found: {os.path.join(FORGE_DIR, 'config', 'foo', 'foo.yaml')}"),
])
def test_load_config_errors(mock_pass, args, exp_error, caplog):
    """Test loading of forge configuration with errors."""
    mock_pass.getuser.return_value = 'dummy'

    with pytest.raises(SystemExit):
        yaml_loader.load_config(args)

    assert caplog.record_tuples[-1] == ('forge.yaml_loader', logging.ERROR, exp_error)


@pytest.mark.parametrize(
    "raw_x", [
        1,
        1.1,
        "1",
        None,
        [1, "two", 3.3],
        [1, 2, 3],
        [[-1, "two", 3.3]]
    ]
)
def test_non_negative_list_failures(raw_x):
    with pytest.raises(ValueError):
        non_negative_list_list_ints(raw_x)


@pytest.mark.parametrize(
    "raw_x", [
        [[1, 2, 3]],
        [[1, 2, 3], [4, 5, 6]],
    ]
)
def test_non_negative_list_pass(raw_x):
    result = non_negative_list_list_ints(raw_x)
    assert result == raw_x
