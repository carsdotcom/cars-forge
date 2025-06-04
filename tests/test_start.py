import logging
from unittest import mock

import pytest

from forge import start
from forge.configuration import Configuration


BASE_CONFIG = {
    'region': 'us-east-1',
    'ec2_amis': {},
    'ec2_key': '',
    'forge_env': 'dev',
    'forge_pem_secret': '',
    'job': 'start'
}


logger = logging.getLogger("start")


@mock.patch('forge.start.start_fleet')
@pytest.mark.parametrize(
    'service, markets',
    [
        ('cluster', ['on-demand', 'on-demand']),
        ('single', ['on-demand']),
    ]
)
def test_start(mock_start_fleet, service, markets):
    config = Configuration(**{
        **BASE_CONFIG,
        "name": "some name",
        "date": "2022-01-01",
        "market": markets,
        "service": service,
        "region": "us-east-1",
        'aws_profile': "dev"
    })

    start.start(config)
    n_list = []
    if service == "cluster":
        for index, market in enumerate(markets):
            worker_name = "master" if index == 0 else "worker"
            n_list.append(f'{config["name"]}-{market}-{service}-{worker_name}-{config["date"]}')
    else:
        for market in markets:
            n_list.append(f'{config["name"]}-{market}-{service}-{config["date"]}')

    mock_start_fleet.assert_called_once_with(n_list, config)


@mock.patch('forge.start.start_fleet')
@pytest.mark.parametrize(
    'service, markets',
    [
        ('cluster', ['spot']),
        ('cluster', ['on-demand', 'spot']),
        ('single', ['spot']),
    ]
)
def test_start_error_in_spot_instance(mock_start_fleet, caplog, service, markets):
    config = Configuration(**{
        **BASE_CONFIG,
        "name": "some name",
        "date": "2022-01-01",
        "market": markets,
        "service": service,
    })

    error_msg = ""
    if 'spot' in markets:
        error_msg = 'Master or worker is a spot instance; you cannot start a spot instance'

    with caplog.at_level(logging.ERROR):
        start.start(config)
    assert error_msg in caplog.text
