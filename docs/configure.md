[Home](index.md)

---

# Configure

Forge configure makes it easy to create the environment yaml file. You will be asked to enter each variable one at a time. Once done, forge will check the provided information, create the yaml, and place it in the correct location.

This step should be needed only once per environment, usually done by someone on the administration team. The yaml this step creates stores all the parameters needed to start an ec2 that doesn't change between forge runs. You can create one yaml for each AWS environment or virtual environment in the same AWS account.

### How to Run

1. `forge configure`

- Refer to [environmental_yaml](environmental_yaml.md) for more information on each parameter
- After completion, the config directory will be given.
- E.g.:

  ```bash
  $ forge configure
  Environment Name?: test
  AWS profile?: aws-test
  AWS availability zone?: us-east-1a
  EC2 AMIs?: {'single': ['ami-05fa00d4c63e32376', 30, '/dev/xvda'], 'cluster': ['ami-05fa00d4c63e32376', 30, '/dev/xvda']}
  AWS Subnet?: subnet-123abc456def789gh
  AWS key used with EC2?: test
  AWS Security Group?: sg-abcdefghi12345678
  Name of Secret for pem key?: forge-pem
  EC2s to exclude from spot fleet (Optional): *g.*, gd.*, *metal*
  Tags applied to EC2 and fleet (Optional): [{'Key': 'Name', 'Value': 'n'}, {'Key': 'Application', 'Value': 'name'}, {'Key': 'User', 'Value': 'user'}]
  The default user_data files. Files are loaded to the config folder (Optional): {'single': 'single.sh', 'cluster': {'master': 'cluster-master.sh', 'worker': 'cluster-worker.sh'}}
  Additional configs needed for your application (Optional): [{'name': 'pip', 'type': 'list', 'default': [], 'constraints': [], 'error': ''}]
  Wed Sep 21 13:30:06 2022 -- INFO -- Config directory for /Users/test/envs/forge/lib/python3.6/site-packages/forge/config/test does no exist. Making directory.
  Wed Sep 21 13:30:06 2022 -- INFO -- Created test config file.
  ```
