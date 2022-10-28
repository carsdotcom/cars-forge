from unittest import mock

from forge import destroy

import pytest


@mock.patch("forge.destroy.find_and_destroy")
@pytest.mark.parametrize("service, market", [("single", ["spot"]), ("cluster", ["spot", "spot"])])
def test_destroy(mock_find_and_destroy, service, market):
    config = {
        "name": "test-run",
        "date": "2021-02-01",
        "service": service,
        "market": market
    }

    destroy.destroy(config)
    
    if service == 'single':
        n = f'{config["name"]}-{market[0]}-{service}-{config["date"]}'
        mock_find_and_destroy.assert_called_once_with(n, config)

    if service == 'cluster':
        n1 = f'{config["name"]}-{market[0]}-{service}-master-{config["date"]}'
        n2 = f'{config["name"]}-{market[-1]}-{service}-worker-{config["date"]}'
        assert mock_find_and_destroy.call_args_list == [((n1, config),), ((n2, config),)]


@mock.patch("forge.destroy.ec2_ip")
@mock.patch("forge.destroy.pricing")
@mock.patch("forge.destroy.fleet_destroy")
@pytest.mark.parametrize("service, market", [("single", ["spot"]), ("cluster", ["spot", "spot"])])
def test_find_and_destroy(mock_fleet_destroy, mock_pricing, mock_ec2_ip, service, market):
    ip = "123.456.789"
    fleet_id = "abc-123"
    ec2_details = [{"ip": ip, "spot_id": ["abc"], "state": None, "fleet_id": fleet_id}]
    mock_ec2_ip.return_value = ec2_details

    config = {
        "name": "test-run",
        "date": "2021-02-01",
        "service": service,
        "market": market
    }

    destroy.destroy(config)

    if service == 'single':
        n1 = f'{config["name"]}-{market[0]}-{service}-{config["date"]}'
        assert mock_fleet_destroy.call_args_list == [((n1, fleet_id, config),)]
        assert mock_pricing.call_args_list == [((ec2_details, config, market[0]),)]

    if service == 'cluster':
        n2 = f'{config["name"]}-{market[0]}-{service}-master-{config["date"]}'
        n3 = f'{config["name"]}-{market[-1]}-{service}-worker-{config["date"]}'
        assert mock_fleet_destroy.call_args_list == [((n2, fleet_id, config),), ((n3, fleet_id, config),)]
        assert mock_pricing.call_args_list == [((ec2_details, config, market[0]),), ((ec2_details, config, market[1]),)]
