import logging
from unittest import mock

from forge import start

import pytest

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
    config = {
        "name": "some name",
        "date": "2022-01-01",
        "market": markets,
        "service": service,
        "region": "us-east-1",
        'aws_profile': "dev"
    }
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
    config = {
        "name": "some name",
        "date": "2022-01-01",
        "market": markets,
        "service": service,
    }
    error_msg = ""
    if service == "cluster":
        if markets[0] == "spot":
            error_msg = "Master is a spot instance; you cannot start a spot instance"
        elif markets[1] == "spot":
            error_msg = "Worker is a spot fleet; you cannot start a spot fleet"
    else:
        if markets[0] == "spot":
            error_msg = "The instance is a spot instance; you cannot start a spot instance"

    with caplog.at_level(logging.ERROR):
        start.start(config)
    assert error_msg in caplog.text
