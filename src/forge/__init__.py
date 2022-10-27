__version__ = "1.0.2"

# Default values for forge's essential arguments
DEFAULT_ARG_VALS = {
    'market': ['spot', 'spot'],
    'log_level': 'INFO',
    'date': None,
    'gpu_flag': False,
    'config_dir': '{}/config/{}',
    'destroy_after_success': True,
    'destroy_after_failure': True,
    'default_ratio': [8, 8],
    'valid_time': 8,
    'ec2_max': 768
}

# Required arguments for each Forge job
REQUIRED_ARGS = {}

# additional admin-created configs
ADDITIONAL_KEYS = []
