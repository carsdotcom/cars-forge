"""Tests for the common functions of Forge."""
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
