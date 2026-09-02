from unittest import mock

import pytest

from forge import destroy
from forge.configuration import Configuration


BASE_CONFIG = {
    'region': 'us-east-1',
    'ec2_amis': {
        'single': {
            'ami': 'ami-00000000000000000',
            'disk': 30,
            'disk_device_name': '/dev/sda1'
        },
        'cluster': {
            'ami': 'ami-00000000000000000',
            'disk': 30,
            'disk_device_name': '/dev/xvda'
        },
    },
    'ec2_key': '',
    'forge_env': 'dev',
    'forge_pem_secret': '',
    'job': 'destroy'
}


@mock.patch("forge.destroy.find_and_destroy")
@pytest.mark.parametrize("service, market", [("single", ["spot"]), ("cluster", ["spot", "spot"])])
def test_destroy(mock_find_and_destroy, service, market):
    config = Configuration(**{
        **BASE_CONFIG,
        "name": "test-run",
        "date": "2021-02-01",
        "service": service,
        "market": market
    })

    ami_spec = {'x86_64': 'ami-00000000000000000'}

    destroy.destroy(config)
    
    if service == 'single':
        n = f'{config["name"]}-{market[0]}-{service}-{config["date"]}'
        mock_find_and_destroy.assert_called_once_with(n, config, ami_spec)

    if service == 'cluster':
        n1 = f'{config["name"]}-{market[0]}-{service}-master-{config["date"]}'
        n2 = f'{config["name"]}-{market[-1]}-{service}-worker-{config["date"]}'
        assert mock_find_and_destroy.call_args_list == [((n1, config, ami_spec),), ((n2, config, ami_spec),)]


@mock.patch("forge.destroy.ec2_ip")
@mock.patch("forge.destroy.pricing")
@mock.patch("forge.destroy.fleet_destroy")
@mock.patch("forge.destroy.template_destroy")
@pytest.mark.parametrize("service, market", [("single", ["spot"]), ("cluster", ["spot", "spot"])])
def test_find_and_destroy(mock_template_destroy, mock_fleet_destroy, mock_pricing, mock_ec2_ip, service, market):
    ip = "123.456.789"
    fleet_id = "abc-123"
    ec2_details = [{"ip": ip, "spot_id": ["abc"], "state": None, "fleet_id": fleet_id}]
    mock_ec2_ip.return_value = ec2_details

    config = Configuration(**{
        **BASE_CONFIG,
        "name": "test-run",
        "date": "2021-02-01",
        "service": service,
        "market": market
    })

    destroy.destroy(config)

    if service == 'single':
        assert mock_fleet_destroy.call_args_list == [(mock.call(fleet_id))]
        assert mock_pricing.call_args_list == [((ec2_details, config, market[0]),)]

    if service == 'cluster':
        assert mock_fleet_destroy.call_args_list == [(mock.call(fleet_id)), (mock.call(fleet_id))]
        assert mock_pricing.call_args_list == [((ec2_details, config, market[0]),), ((ec2_details, config, market[1]),)]
