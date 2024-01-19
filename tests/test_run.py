"""Tests for the run module of Forge."""
import logging
import subprocess
from unittest import mock

import pytest

from forge import run


@mock.patch('forge.run.subprocess.run')
@mock.patch('forge.run.key_file')
@mock.patch('forge.run.get_ip')
@mock.patch('forge.run.ec2_ip')
@pytest.mark.parametrize('service,out', [('single', 'single'), ('cluster', 'cluster-master')])
def test_run_success(mock_ec2_ip, mock_get_ip, mock_key_file, mock_sub_run, service, out):
    """Test a successful execution of the 'run' sub-command."""
    ip = '123.456.789'
    ec2_details = [{'ip': ip, 'spot_id': ['abc'], 'state': None}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = [(ip, None)]
    key_path = '/dummy/key/path'
    mock_key_file.return_value.__enter__.return_value = key_path
    config = {
        'name': 'test-run',
        'date': '2021-02-01',
        'service': service,
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'forge_env': 'test',
        'run_cmd': 'dummy.sh dev test',
    }
    expected_cmd = [
        'ssh', '-t', '-o', 'UserKnownHostsFile=/dev/null',  '-o',
        'StrictHostKeyChecking=no', '-i', key_path, f'root@{ip}',
        '/root/dummy.sh', 'dev', 'test'
    ]

    assert run.run(config) == 0

    mock_ec2_ip.assert_called_once_with(
        f"{config['name']}-spot-{out}-{config['date']}", config
    )
    mock_get_ip.assert_called_once_with(ec2_details, ('running',))
    mock_key_file.assert_called_once_with(
        config['forge_pem_secret'], config['region'], config['aws_profile']
    )
    mock_sub_run.assert_called_once_with(
        expected_cmd, check=True, universal_newlines=True
    )


@mock.patch('forge.run.subprocess.run')
@mock.patch('forge.run.key_file')
@mock.patch('forge.run.get_ip')
@mock.patch('forge.run.ec2_ip')
def test_run_error(mock_ec2_ip, mock_get_ip, mock_key_file, mock_sub_run, caplog):
    """Test an execution of the 'run' sub-command with errors."""
    ip = '123.456.789'
    ec2_details = [{'ip': ip, 'spot_id': ['abc'], 'state': None}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = [(ip, None)]
    key_path = '/dummy/key/path'
    mock_key_file.return_value.__enter__.return_value = key_path
    config = {
        'name': 'test-run',
        'date': '2021-02-01',
        'service': 'single',
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'forge_env': 'test',
        'run_cmd': 'dummy.sh dev test',
        'job': 'run',
    }
    expected_cmd = [
        'ssh', '-t', '-o', 'UserKnownHostsFile=/dev/null',  '-o',
        'StrictHostKeyChecking=no', '-i', key_path, f'root@{ip}',
        '/root/dummy.sh', 'dev', 'test'
    ]
    mock_sub_run.side_effect = subprocess.CalledProcessError(
        returncode=123, cmd=expected_cmd
    )

    assert run.run(config) == 123

    n = f"{config['name']}-spot-single-{config['date']}"

    mock_ec2_ip.assert_called_once_with(
        n, config
    )
    mock_get_ip.assert_called_once_with(ec2_details, ('running',))
    mock_key_file.assert_called_once_with(
        config['forge_pem_secret'], config['region'], config['aws_profile']
    )
    mock_sub_run.assert_called_once_with(
        expected_cmd, check=True, universal_newlines=True
    )
    assert caplog.record_tuples == [
        ('forge.run', logging.INFO, f'Trying to run command on {n}'),
        ('forge.run', logging.INFO, f'Run destination is {ip}'),
        ('forge.run', logging.ERROR, f'EC2 command failed with error code 123: {expected_cmd}'),
        ('forge.run', logging.ERROR, f'Run command raised error: Run command unsuccessful, ending attempts.')
    ]
