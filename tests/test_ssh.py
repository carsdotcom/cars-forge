"""Tests for the ssh module of Forge."""
import logging
import subprocess
from unittest import mock

import pytest

from forge import ssh


@mock.patch('forge.ssh.subprocess.run')
@mock.patch('forge.ssh.key_file')
@mock.patch('forge.ssh.get_ip')
@mock.patch('forge.ssh.ec2_ip')
@pytest.mark.parametrize('service,out', [('single', 'single'), ('cluster', 'cluster-master')])
def test_ssh_success(mock_ec2_ip, mock_get_ip, mock_key_file, mock_sub_run, service, out):
    """Test a successful execution of the 'ssh' sub-command."""
    ip = '123.456.789'
    ec2_details = [{'ip': ip, 'id': 'i-abc', 'fleet_id': ['fleet-def'], 'state': 'running'}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = [(ip, 'i-abc')]
    key_path = '/dummy/key/path'
    mock_key_file.return_value.__enter__.return_value = key_path
    config = {
        'name': 'test-run',
        'date': '2021-02-01',
        'service': service,
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'market': ['spot', 'spot'],
    }
    expected_cmd = [
        'ssh', '-t', '-o', 'UserKnownHostsFile=/dev/null',  '-o',
        'StrictHostKeyChecking=no', '-i', key_path, f'root@{ip}',
    ]

    ssh.ssh(config)

    mock_ec2_ip.assert_called_once_with(
        f"{config['name']}-{config['market'][0]}-{out}-{config['date']}", config
    )
    mock_key_file.assert_called_once_with(
        config['forge_pem_secret'], config['region'], config['aws_profile']
    )
    mock_sub_run.assert_called_once_with(
        expected_cmd, check=True, universal_newlines=True
    )


@mock.patch('forge.ssh.get_ip')
@mock.patch('forge.ssh.ec2_ip')
def test_ssh_no_instances(mock_ec2_ip, mock_get_ip, caplog):
    """Test an execution of the 'ssh' sub-command with no valid instances."""
    ec2_details = [{'ip': None, 'id': None, 'fleet_id': [], 'state': None}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = []
    config = {
        'name': 'test-run',
        'date': '2021-02-01',
        'service': 'single',
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'forge_env': 'test',
        'market': ['spot', 'spot'],
    }

    with pytest.raises(SystemExit):
        ssh.ssh(config)

    n = f"{config['name']}-spot-single-{config['date']}"

    mock_ec2_ip.assert_called_once_with(n, config)
    mock_get_ip.assert_called_once_with(ec2_details, ('running',))
    assert caplog.record_tuples == [
        ('forge.ssh', logging.ERROR, 'Could not find any valid instances to SSH to')
    ]


@mock.patch('forge.ssh.subprocess.run')
@mock.patch('forge.ssh.key_file')
@mock.patch('forge.ssh.get_ip')
@mock.patch('forge.ssh.ec2_ip')
@pytest.mark.parametrize('err_code,err_msg', [
    (142, 'Missing proper SSH credentials'),
    (111, 'SSH failed with error code 111')
])
def test_ssh_connection_error(mock_ec2_ip, mock_get_ip, mock_key_file, mock_sub_run,
                              caplog, err_code, err_msg):
    """Test an execution of the 'ssh' sub-command with connection errors."""
    ip = '123.456.789'
    ec2_details = [{'ip': ip, 'id': 'i-abc', 'fleet_id': ['fleet-def'], 'state': 'running'}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = [(ip, 'i-abc')]
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
        'market': ['spot', 'spot'],
    }
    expected_cmd = [
        'ssh', '-t', '-o', 'UserKnownHostsFile=/dev/null',  '-o',
        'StrictHostKeyChecking=no', '-i', key_path, f'root@{ip}',
    ]
    mock_sub_run.side_effect = subprocess.CalledProcessError(
        returncode=err_code, cmd=expected_cmd
    )

    with pytest.raises(SystemExit, match=str(err_code)):
        ssh.ssh(config)

    n = f"{config['name']}-spot-single-{config['date']}"

    mock_ec2_ip.assert_called_once_with(n, config)
    mock_get_ip.assert_called_once_with(ec2_details, ('running',))
    mock_key_file.assert_called_once_with(
        config['forge_pem_secret'], config['region'], config['aws_profile']
    )
    mock_sub_run.assert_called_once_with(
        expected_cmd, check=True, universal_newlines=True
    )
    assert err_msg in caplog.text
