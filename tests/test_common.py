"""Tests for the common functions of Forge."""
import json
from datetime import datetime
from unittest import mock

import pytest

from forge import common


TEST_DEFAULT_ARG_VALS = {
    'market': ['bar', 'baz'],
    'default_ratio': [2, 3],
}
TEST_ADDITIONAL_KEYS = ['fake', 'not_real']

@mock.patch.dict('forge.common.DEFAULT_ARG_VALS', TEST_DEFAULT_ARG_VALS)
@pytest.mark.parametrize('config,expected', [
    # Overriding default ratio
    ({'aws_az': 'us-east-1a', 'ratio': [6, 8]},
     {'aws_az': 'us-east-1a', 'region': 'us-east-1'}),
    # Regular config
    ({'ram': ['8', [256, 512]], 'cpu': ['1, 2', '7,8'], 'aws_az': 'testing',
      'market': 'on-demand, spot'},
     {'ram': [[8], [256, 512]], 'cpu': [[1, 2], [7, 8]], 'aws_az': 'testing',
      'region': 'testin', 'market': ['on-demand', 'spot'], 'ratio': None}),
    # No-market config
    ({'ram': ['8', [256, 512]], 'cpu': ['1, 2', '7,8']},
     {'ram': [[8], [256, 512]], 'cpu': [[1, 2], [7, 8]], 'ratio': None}),
])
def test_normalize_config(config, expected):
    """Test the normalization of config options."""
    actual = common.normalize_config(config)
    if config.get('ratio'):
        assert config['ratio'] == common.DEFAULT_ARG_VALS['default_ratio']

    assert actual == expected


@mock.patch.dict('forge.common.DEFAULT_ARG_VALS', TEST_DEFAULT_ARG_VALS)
@pytest.mark.parametrize('config,additional_config,expected', [
    ({},
     [{'name': 'pip', 'type': 'list', 'default': [], 'constraints': []},
      {'name': 'version', 'type': 'float', 'default': 2.3, 'constraints': [2.3, 3.0, 3.1]}],
     {'version': 2.3})
])
def test_parse_additional_config(config, additional_config, expected):
    """Test the normalization of config options."""
    actual = common.parse_additional_config(config, additional_config)
    if config.get('ratio'):
        assert config['ratio'] == common.DEFAULT_ARG_VALS['default_ratio']

    assert actual == expected


@mock.patch.dict('forge.common.DEFAULT_ARG_VALS', TEST_DEFAULT_ARG_VALS, clear=True)
@mock.patch.object(common, 'ADDITIONAL_KEYS', TEST_ADDITIONAL_KEYS)
@pytest.mark.parametrize('config,kwargs,expected', [
    # Config with cluster markets and various configs, including one that should
    # not be exposed.
    ({'service': 'cluster', 'market': ['spot', 'on-demand'], 'a': 1, 'b': 1.23,
      'c': 'foo', 'd': ['some', 'list'], 'e': {'not': 'shown'}},
     {},
     {'service': 'cluster', 'market_master': 'spot', 'market_worker': 'on-demand',
      'a': 1, 'b': 1.23, 'c': 'foo'}),
    # Config with no market
    ({'service': 'single', 'a': 1, 'b': 'foo'},
     {},
     {'service': 'single', 'market': TEST_DEFAULT_ARG_VALS['market'][0], 'a': 1,
      'b': 'foo'}),
    # Config with single market
    ({'service': 'single', 'market': ['spot'], 'a': 1, 'b': 'foo'},
     {},
     {'service': 'single', 'market': 'spot', 'a': 1, 'b': 'foo'}),
    # Config with single market and extra variables
    ({'service': 'single', 'market': ['spot'], 'a': 1},
     {'task': 'single'},
     {'service': 'single', 'market': 'spot', 'a': 1, 'task': 'single'}),
    # Config and extra variables both pass the same key
    ({'service': 'single', 'market': ['spot'], 'a': 1},
     {'market': 'on-demand'},
     {'service': 'single', 'market': 'on-demand', 'a': 1}),
    # Config with additional admin-defined keys that are passed as-is
    ({'service': 'single', 'market': ['spot'], 'fake': [1,2,3], 'not_real': {'a': 'b'}},
     {},
     {'service': 'single', 'market': 'spot', 'fake': [1,2,3], 'not_real': {'a': 'b'}}),
])
def test_user_accessible_vars(config, kwargs, expected):
    """Test creating the dict of user-accessible variables."""
    actual = common.user_accessible_vars(config, **kwargs)
    assert actual == expected


@mock.patch('forge.common.boto3')
@mock.patch('forge.common.datetime')
def test_get_ec2_pricing_spot(mock_dt, mock_boto):
    """Test getting spot EC2 hourly pricing."""
    exp_price = 0.123
    response = {'SpotPriceHistory': [{'SpotPrice': str(exp_price)}]}
    mock_client = mock_boto.client.return_value = mock.Mock()
    mock_describe = mock_client.describe_spot_price_history
    mock_describe.return_value = response
    now = datetime(2022, 1, 1, 12, 0, 0)
    mock_dt.utcnow.return_value = now

    config = {'aws_az': 'us-east-1a', 'region': 'us-east-1'}
    ec2_type = 'r5.large'
    act_price = common.get_ec2_pricing(ec2_type, 'spot', config)
    assert act_price == exp_price

    mock_boto.client.assert_called_once_with('ec2')
    mock_dt.utcnow.assert_called_once()
    mock_describe.assert_called_once_with(
        StartTime=now,
        ProductDescriptions=['Linux/UNIX (Amazon VPC)'],
        AvailabilityZone=config['aws_az'],
        InstanceTypes=[ec2_type]
    )


@mock.patch('forge.common.boto3')
@mock.patch('forge.common.get_regions')
def test_get_ec2_pricing_ondemand(mock_regions, mock_boto):
    """Test getting on-demand EC2 hourly pricing."""
    exp_price = 0.123
    region = 'us-east-1'
    long_region = 'US East (N. Virginia)'
    response = {'PriceList': [json.dumps(
        {"terms": {"OnDemand": {
            "XYZ": {"priceDimensions": {"XYZ.ABC": {"pricePerUnit": {"USD": "0.1230000000"}}}}
        }}}
    )]}

    mock_client = mock_boto.client.return_value = mock.Mock()
    mock_products = mock_client.get_products
    mock_products.return_value = response
    mock_regions.return_value = {region: long_region}

    config = {'region': region}
    ec2_type = 'r5.large'
    act_price = common.get_ec2_pricing(ec2_type, 'on-demand', config)
    assert act_price == exp_price

    mock_boto.client.assert_called_once_with('pricing', region_name=region)
    mock_regions.assert_called_once()
    mock_products.assert_called_once_with(
        ServiceCode='AmazonEC2', Filters=[
            {'Field': 'tenancy', 'Value': 'shared', 'Type': 'TERM_MATCH'},
            {'Field': 'operatingSystem', 'Value': 'Linux', 'Type': 'TERM_MATCH'},
            {'Field': 'preInstalledSw', 'Value': 'NA', 'Type': 'TERM_MATCH'},
            {'Field': 'location', 'Value': long_region, 'Type': 'TERM_MATCH'},
            {'Field': 'capacitystatus', 'Value': 'Used', 'Type': 'TERM_MATCH'},
            {'Field': 'instanceType', 'Value': ec2_type, 'Type': 'TERM_MATCH'}
        ]
    )
