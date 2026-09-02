"""Tests for the create module of Forge."""
# pylint: disable=W0621,R0913
import re
from unittest import mock
from datetime import datetime

import pytest
from botocore.exceptions import ClientError

from forge import create
from forge.configuration import Configuration


BASE_CONFIG = {
    'region': 'us-east-1',
    'ec2_amis': {},
    'ec2_key': '',
    'forge_env': 'dev',
    'forge_pem_secret': '',
    'job': 'create'
}


@mock.patch('forge.create.get_instance_details')
@mock.patch('forge.create.search_and_create')
def test_create_single(mock_search_create, mock_get_instance_details):
    """Test entry-point for creation of single instance."""
    config = Configuration(**{**BASE_CONFIG, 'service': 'single', 'aws_az': 'us-east-1a'})
    mock_get_instance_details.return_value = {'single': {}}
    create.create(config)
    mock_search_create.assert_called_once_with(config, {'single': {}})


@mock.patch('forge.create.get_instance_details')
@mock.patch('forge.create.search_and_create')
def test_create_cluster_master_workers(mock_search_create, mock_get_instance_details):
    """Test entry-point for creation of cluster with master and workers."""
    config = Configuration(**{**BASE_CONFIG, 'service': 'cluster', 'aws_az': 'us-east-1a'})
    mock_get_instance_details.return_value = {'cluster-master': {}, 'cluster-worker': {}}
    create.create(config)
    mock_search_create.assert_called_once_with(config, {'cluster-master': {}, 'cluster-worker': {}})


@pytest.mark.parametrize(
    'in_ram,in_cpu,out_ram,out_cpu,out_total,out_ratio', [
        # Single job, single ram, default cpu
        ([8], None, [8, 8], [1, 2], 8, [4, 8]),
        ([4], None, [4, 4], [1, 2], 4, [2, 4]),
        ([32], None, [32, 32], [4, 4], 32, [8, 8]),
        # Single job, single ram, single cpu
        ([32], [12], [32, 32], [12, 12], 32, [32/12, 32/12]),
        # Single job, single ram, cpu range
        ([32], [1, 1], [32, 32], [1, 1], 32, [32, 32]),
        # Single job, ram range, default cpu
        ([32, 64], None, [32, 64], [4, 8], 32, [8, 8]),
        # Single job, ram range, single cpu
        ([32, 64], [8], [32, 64], [8, 8], 32, [4, 8]),
        # Single job, ram range, cpu range
        ([32, 64], [4, 8], [32, 64], [4, 8], 32, [8, 8]),
        # cluster master job, single ram
        ([16], None, [16, 16], [2, 2], 16, [8, 8]),
        # cluster master job, ram range
        ([16, 32], None, [16, 32], [2, 4], 16, [8, 8]),
        # cluster worker job, small single ram
        ([512], None, [512, 512], [64, 64], 512, [8, 8]),
        # cluster worker job, large single ram
        ([1024], None, [128, 768], [16, 96], 1024, [8, 8]),
        # cluster worker job, small ram range
        ([256, 514], None, [256, 514], [32, 64], 256, [8, 8.03125]),  # ToDo: Figure out better way
        # cluster worker job, large ram range
        ([1024, 1536], None, [128, 768], [16, 96], 1024, [8, 8]),
    ]
)
def test_calc_machine_ranges(in_ram, in_cpu, out_ram, out_cpu,
                             out_total, out_ratio):
    """Test the calculation of RAM and CPU ranges."""
    out_ram = [1024 * r for r in out_ram]
    out_total = 1024 * out_total
    job_ram, job_cpu, total_ram, ratio = create.calc_machine_ranges(
        ram=in_ram, cpu=in_cpu
    )
    assert job_ram == out_ram
    assert job_cpu == out_cpu
    assert total_ram == out_total
    assert ratio == out_ratio


@mock.patch('forge.create.datetime')
def test_get_fleet_error_no_time(mock_dt):
    """Test getting the error details of a fleet with no create time passed."""
    fleet_id = 'abc-123'
    now = datetime(2022, 1, 1, 12, 0, 0)
    exp_start = datetime(2022, 1, 1, 11, 0, 0)
    mock_dt.utcnow.return_value = now
    mock_client = mock.Mock()
    msg = 'Error details.'
    mock_client.describe_fleet_history = mock.Mock(return_value={'HistoryRecords': [
        {'EventType': 'error', 'EventInformation': {
            'EventSubType': 'spotFleetRequestConfigurationInvalid',
            'EventDescription': msg
        }}
    ]})

    actual_details = create.get_fleet_error(mock_client, fleet_id)
    assert actual_details == msg

    mock_dt.utcnow.assert_called_once()
    mock_client.describe_fleet_history.assert_called_once_with(
        FleetId=fleet_id, StartTime=exp_start
    )


@mock.patch('forge.create.datetime')
def test_get_fleet_error_client_error(mock_dt):
    """Test getting the error details of a fleet when EC2 client returns errors."""
    now = datetime(2022, 1, 1, 12, 0, 0)
    exp_start = datetime(2022, 1, 1, 11, 0, 0)
    mock_dt.utcnow.return_value = now
    mock_client = mock.Mock()
    mock_client.describe_fleet_history = mock.Mock(side_effect=ClientError(
        {'Error': {'Code': 'Invalid'}}, 'Mistake'
    ))
    fleet_id = 'abc-123'

    actual_details = create.get_fleet_error(mock_client, fleet_id)
    assert actual_details == ''

    mock_dt.utcnow.assert_called_once()
    mock_client.describe_fleet_history.assert_called_once_with(
        FleetId=fleet_id, StartTime=exp_start
    )


@pytest.mark.parametrize('history,exp_details', [
    # Valid response but no history (shouldn't happen)
    ({'foo': 'key'}, ''),
    # Valid response but empty history
    ({'HistoryRecords': []}, ''),
    # Valid response but history has no valid events
    ({'HistoryRecords': [{'bar': '123'}]}, ''),
    # Valid response but history has no error events
    ({'HistoryRecords': [{'EventType': 'all-good'}]}, ''),
    # Valid response but history has an error with no event information
    ({'HistoryRecords': [{'EventType': 'error', 'not-info': {'a': 'b'}}]}, ''),
    # Valid response but history has an error with the subtype we don't want
    ({'HistoryRecords': [
        {'EventType': 'error', 'EventInformation': {
            'EventSubType': 'allLaunchSpecsTemporarilyBlacklisted'
        }
    }]}, ''),
    # Valid response but history has an error with no description
    ({'HistoryRecords': [
        {'EventType': 'error', 'EventInformation': {
            'EventSubType': 'spotFleetRequestConfigurationInvalid',
            'EventDescription': 'Now this is a useful error message.'
        }}
    ]}, 'Now this is a useful error message.'),
    # Valid response with multiple errors in history
    ({'HistoryRecords': [
        {'EventType': 'error', 'EventInformation': {
            'EventSubType': 'spotFleetRequestConfigurationInvalid',
            'EventDescription': 'First error.'
        }},
        {'EventType': 'error', 'EventInformation': {
            'EventSubType': 'spotFleetRequestConfigurationInvalid',
            'EventDescription': 'Do not care about this one.'
        }}
    ]}, 'First error.'),
])
def test_get_fleet_error(history, exp_details):
    """Test getting the error details of a fleet."""
    fleet_id = 'abc-123'
    create_time = datetime(2022, 1, 1, 12, 0, 0)
    start_time = datetime(2022, 1, 1, 11, 30, 0)
    mock_client = mock.Mock()
    mock_client.describe_fleet_history = mock.Mock(return_value=history)

    actual_details = create.get_fleet_error(mock_client, fleet_id, create_time)
    assert actual_details == exp_details

    mock_client.describe_fleet_history.assert_called_once_with(
        FleetId=fleet_id, StartTime=start_time
    )
