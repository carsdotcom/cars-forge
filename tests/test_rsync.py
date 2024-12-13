"""Tests for the rsync module of Forge."""
import subprocess
from unittest import mock

import pytest

from forge import rsync


@mock.patch('forge.rsync.os.path')
@mock.patch('forge.rsync.subprocess.check_output')
@mock.patch('forge.rsync.key_file')
@mock.patch('forge.rsync.get_ip')
@mock.patch('forge.rsync.ec2_ip')
@pytest.mark.parametrize('service,out', [('single', 'single'), ('cluster', 'cluster-master')])
def test_rsync_file_success(mock_ec2_ip, mock_get_ip, mock_key_file, mock_sub_chk,
                            mock_os_path, service, out, caplog):
    """Test a successful execution of the 'rsync' sub-command for a file."""
    ip = '123.456.789'
    ec2_details = [{'ip': ip, 'spot_id': ['abc'], 'state': None}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = [(ip, None)]
    key_path = '/dummy/key/path'
    rsync_path = 'path/to/rsync/file.txt'
    mock_key_file.return_value.__enter__.return_value = key_path
    mock_os_path.isdir.return_value = False
    mock_os_path.isfile.return_value = True
    config = {
        'name': 'test-rsync',
        'date': '2021-02-01',
        'market': ['spot', 'spot'],
        'service': service,
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'rsync_path': rsync_path,
    }
    expected_cmd = 'rsync -rave "ssh -o UserKnownHostsFile=/dev/null -o'
    expected_cmd += f' StrictHostKeyChecking=no -i {key_path}" {rsync_path} root@{ip}:/root/'

    rsync.rsync(config)

    mock_ec2_ip.assert_called_once_with(
        f"{config['name']}-spot-{out}-{config['date']}", config
    )
    mock_get_ip.assert_called_once_with(ec2_details, ('running',))
    mock_os_path.isdir.assert_called_once_with(rsync_path)
    mock_os_path.isfile.assert_called_once_with(rsync_path)
    mock_key_file.assert_called_once_with(
        config['forge_pem_secret'], config['region'], config['aws_profile']
    )
    mock_sub_chk.assert_called_once_with(
        expected_cmd, stderr=subprocess.STDOUT, shell=True, universal_newlines=True
    )
    assert f'Copying file {rsync_path} to EC2.' in caplog.text


@mock.patch('forge.rsync.os.path')
@mock.patch('forge.rsync.subprocess.check_output')
@mock.patch('forge.rsync.key_file')
@mock.patch('forge.rsync.get_ip')
@mock.patch('forge.rsync.ec2_ip')
def test_rsync_dir_success(mock_ec2_ip, mock_get_ip, mock_key_file, mock_sub_chk,
                            mock_os_path, caplog):
    """Test a successful execution of the 'rsync' sub-command for a directory."""
    ip = '123.456.789'
    ec2_details = [{'ip': ip, 'spot_id': ['abc'], 'state': None}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = [(ip, None)]
    key_path = '/dummy/key/path'
    rsync_path = 'path/to/rsync/dir'
    mock_key_file.return_value.__enter__.return_value = key_path
    mock_os_path.isdir.return_value = True
    config = {
        'name': 'test-rsync',
        'date': '2021-02-01',
        'market': ['spot', 'spot'],
        'service': 'single',
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'rsync_path': rsync_path,
    }
    expected_cmd = 'rsync -rave "ssh -o UserKnownHostsFile=/dev/null -o'
    expected_cmd += f' StrictHostKeyChecking=no -i {key_path}" {rsync_path}/* root@{ip}:/root/'

    rsync.rsync(config)

    mock_ec2_ip.assert_called_once_with(
        f"{config['name']}-spot-single-{config['date']}", config
    )
    mock_get_ip.assert_called_once_with(ec2_details, ('running',))
    mock_os_path.isdir.assert_called_once_with(rsync_path)
    mock_key_file.assert_called_once_with(
        config['forge_pem_secret'], config['region'], config['aws_profile']
    )
    mock_sub_chk.assert_called_once_with(
        expected_cmd, stderr=subprocess.STDOUT, shell=True, universal_newlines=True
    )
    assert f'Copying folder {rsync_path} to EC2.' in caplog.text
    assert 'Rsync successful:\n' in caplog.text


@mock.patch('forge.rsync.os.path')
@mock.patch('forge.rsync.key_file')
@mock.patch('forge.rsync.get_ip')
@mock.patch('forge.rsync.ec2_ip')
def test_rsync_no_paths(mock_ec2_ip, mock_get_ip, mock_key_file, mock_os_path, caplog):
    """Test an execution of the 'rsync' sub-command with no valid file/folder."""
    ip = '123.456.789'
    ec2_details = [{'ip': ip, 'spot_id': ['abc'], 'state': None}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = [(ip, None)]
    key_path = '/dummy/key/path'
    rsync_path = 'fake/dir'
    mock_key_file.return_value.__enter__.return_value = key_path
    mock_os_path.isdir.return_value = False
    mock_os_path.isfile.return_value = False
    config = {
        'name': 'test-rsync',
        'date': '2021-02-01',
        'market': ['spot', 'spot'],
        'service': 'single',
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'rsync_path': rsync_path,
    }

    with pytest.raises(SystemExit, match='1'):
        rsync.rsync(config)

    mock_ec2_ip.assert_called_once_with(
        f"{config['name']}-spot-single-{config['date']}", config
    )
    mock_get_ip.assert_called_once_with(ec2_details, ('running',))
    mock_os_path.isdir.assert_called_once_with(rsync_path)
    mock_os_path.isfile.assert_called_once_with(rsync_path)
    mock_key_file.assert_called_once_with(
        config['forge_pem_secret'], config['region'], config['aws_profile']
    )
    assert "File or folder from 'rsync_path' parameter not found:" in caplog.text


@mock.patch('forge.rsync.os.path')
@mock.patch('forge.rsync.subprocess.check_output')
@mock.patch('forge.rsync.key_file')
@mock.patch('forge.rsync.get_ip')
@mock.patch('forge.rsync.ec2_ip')
def test_rsync_fail(mock_ec2_ip, mock_get_ip, mock_key_file, mock_sub_chk,
                    mock_os_path, caplog):
    """Test an execution of the 'rsync' sub-command with subprocess errors."""
    ip = '123.456.789'
    ec2_details = [{'ip': ip, 'spot_id': ['abc'], 'state': None}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = [(ip, None)]
    key_path = '/dummy/key/path'
    rsync_path = 'path/to/rsync/dir'
    mock_key_file.return_value.__enter__.return_value = key_path
    mock_os_path.isdir.return_value = True
    config = {
        'name': 'test-rsync',
        'date': '2021-02-01',
        'market': ['spot', 'spot'],
        'service': 'single',
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'rsync_path': rsync_path,
        'job': 'rsync',
    }
    expected_cmd = 'rsync -rave "ssh -o UserKnownHostsFile=/dev/null -o'
    expected_cmd += f' StrictHostKeyChecking=no -i {key_path}" {rsync_path}/* root@{ip}:/root/'

    mock_sub_chk.side_effect = subprocess.CalledProcessError(
        returncode=123, cmd=expected_cmd
    )

    assert rsync.rsync(config) == 123

    mock_ec2_ip.assert_called_once_with(
        f"{config['name']}-spot-single-{config['date']}", config
    )
    mock_get_ip.assert_called_once_with(ec2_details, ('running',))
    mock_os_path.isdir.assert_called_once_with(rsync_path)
    mock_key_file.assert_called_once_with(
        config['forge_pem_secret'], config['region'], config['aws_profile']
    )
    assert 'Rsync failed:\nNone' in caplog.text


@mock.patch('forge.rsync.os.path')
@mock.patch('forge.rsync.subprocess.check_output')
@mock.patch('forge.rsync.key_file')
@mock.patch('forge.rsync.get_ip')
@mock.patch('forge.rsync.ec2_ip')
def test_rsync_multi(mock_ec2_ip, mock_get_ip, mock_key_file, mock_sub_chk,
                    mock_os_path, caplog):
    """Test an execution of the 'rsync' sub-command to multiple instances."""
    ips = ['123.456.789', '987.654.321']
    ids = ['abc', 'def']
    ec2_details = [
        {'ip': ip, 'spot_id': [sid], 'state': None} for ip, sid in zip(ips, ids)
    ]
    mock_ec2_ip.side_effect = ec2_details
    mock_get_ip.side_effect = [[(ip, None)] for ip in ips]
    key_path = '/dummy/key/path'
    rsync_path = 'path/to/rsync/dir'
    mock_key_file.return_value.__enter__.return_value = key_path
    mock_os_path.isdir.return_value = True
    config = {
        'name': 'test-rsync',
        'date': '2021-02-01',
        'market': ['spot', 'spot'],
        'service': 'cluster',
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'rsync_path': rsync_path,
        'rr_all': True,
    }
    e_cmd = 'rsync -rave "ssh -o UserKnownHostsFile=/dev/null -o'
    e_cmd += f' StrictHostKeyChecking=no -i {key_path}" {rsync_path}/* root@{{0}}:/root/'
    expected_cmds = [e_cmd.format(ip) for ip in ips]

    rsync.rsync(config)

    mock_ec2_ip.assert_has_calls([
        mock.call(f"{config['name']}-spot-cluster-master-{config['date']}", config),
        mock.call(f"{config['name']}-spot-cluster-worker-{config['date']}", config)
    ])
    mock_get_ip.assert_has_calls([mock.call(d, ('running',)) for d in ec2_details])
    mock_os_path.isdir.assert_has_calls([mock.call(rsync_path) for _ in ips])
    mock_key_file.assert_has_calls([
        mock.call(
            config['forge_pem_secret'], config['region'], config['aws_profile']
        ) for _ in ips
    ],  any_order=True)
    mock_sub_chk.assert_has_calls([
        mock.call(
            e_cmd, stderr=subprocess.STDOUT, shell=True, universal_newlines=True
        ) for e_cmd in expected_cmds
    ], any_order=True)
    for ip in ips:
        assert f'Rsync destination is {ip}' in caplog.text


@mock.patch('forge.rsync.get_ip')
@mock.patch('forge.rsync.ec2_ip')
@pytest.mark.parametrize('targets', [[], [tuple()]])
def test_rsync_no_instances(mock_ec2_ip, mock_get_ip, targets, caplog):
    """Test an execution of the 'rsync' sub-command with no valid instances."""
    ec2_details = [{'ip': None, 'spot_id': [None], 'state': None}]
    mock_ec2_ip.return_value = ec2_details
    mock_get_ip.return_value = targets
    rsync_path = 'path/to/rsync/dir'
    config = {
        'name': 'test-rsync',
        'date': '2021-02-01',
        'market': ['spot', 'spot'],
        'service': 'single',
        'forge_pem_secret': 'forge-test',
        'region': 'us-east-1',
        'aws_profile': 'dev',
        'rsync_path': rsync_path,
    }

    rsync.rsync(config)

    mock_ec2_ip.assert_called_once_with(
        f"{config['name']}-spot-single-{config['date']}", config
    )
    mock_get_ip.assert_called_once_with(ec2_details, ('running',))
    assert 'Could not find any valid instances to rsync to' in caplog.text
