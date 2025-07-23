
[Home](index.md)

---

# Environmental Yaml (setup by admins)

Each forge job requires an environment created. This includes an environment yaml and the default user data scripts (optional). 

## Setup
https://github.com/carsdotcom/cars-forge/blob/main/examples/env_yaml_example/example.yaml
### Option 1: Copy files to the config folder

1. Referring to the [example yaml](https://github.com/carsdotcom/cars-forge/blob/main/examples/env_yaml_example/example.yaml), create your environment yaml file.
2. Create your default user data script (optional). An example can be found [here](https://github.com/carsdotcom/cars-forge/blob/main/examples/env_yaml_example/single.sh).
	- In the `user_data` parameter in the environment yaml, you can specify what the default user data script should be if the user does not provide one.
	- `echo "$(cat /root/.ssh/authorized_keys | sed 's/^.*ssh-rsa/ssh-rsa/')" > /root/.ssh/authorized_keys` is needed in all user data scripts because Forge runs all commands as root.
3. Run `forge configure -h`
	- This will output the location of the configure folder.
	- Example: `Configure env yaml and place it in /home/ec2-user/.local/lib/python3.7/site-packages/forge/config/`
4. Create a new folder under the config folder.
	- E.g.
	```bash
	mkdir -p /home/ec2-user/.local/lib/python3.7/site-packages/forge/config/example`
	```
5. Copy your environment yaml and user data script to the new folder.

### Option 2: Use forge configure 
1. Run `forge configure` and fill in all the parameters.
2. Create your default user data script (optional). An example can be found [here](https://github.com/carsdotcom/cars-forge/blob/main/examples/env_yaml_example/single.sh).
	- In the `user_data` parameter in the environment yaml, you can specify what the default user data script should be if one is not provided.
	- `echo "$(cat /root/.ssh/authorized_keys | sed 's/^.*ssh-rsa/ssh-rsa/')" > /root/.ssh/authorized_keys` is needed in all user data scripts because Forge runs all commands as root.
3. Run `forge configure -h`
	- This will output the location of the configure folder.
	- Example: `Configure env yaml and place it in /home/ec2-user/.local/lib/python3.7/site-packages/forge/config/`
4. Locate the environment under the config folder. The folder name will be the same as the `name` you used when you ran `forge configure`.
5. Copy your user data script to the new folder.

## Environmental parameters (setup by admins)

- **additional_config** - Additional configuration options allowed in user config files
	- Needs four parameters: 
		- name: name of the parameter
		- type: data type
		- default: default value if one isn't given.
		- constraints: options they must choose
		- error: error message if a given value is the wrong type or not within constraints
	- E.g.
    ```yaml
	additional_config:
	  - name: pip
	    type: list
	    default: []
	    constraints: []
	    error: ""
	  - name: version
	    type: float
	    default: 2.3
	    constraints: [2.3, 3.0, 3.1]
	    error: "Invalid Spark version. Only 2.3, 3.0, and 3.1 are supported."
    ```
- **aws_az** - The [AWS availability zone](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html) where Forge will create the EC2 instance. If set, multi-az placement will be disabled.
- **aws_imds_v2** - Toggle if [AWS IMDSv2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-service.html) is required.
- **aws_region** - The AWS region for Forge to run in- **aws_profile** - [AWS CLI profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-profiles.html) to use
- **aws_security_group** - [AWS Security Group](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html) for the instance
- **aws_subnet** - [AWS subnet](https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html) where the EC2s will run
- **aws_multi_az** - [AWS subnet](https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html) where the EC2s will run organized by AZ
  - E.g.
  ```yaml
  aws_multi_az:
  	us-east-1a: subnet-aaaaaaaaaaaaaaaaa
  	us-east-1b: subnet-bbbbbbbbbbbbbbbbb
  	us-east-1c: subnet-ccccccccccccccccc
  ```
- **default_ratio** - Override the default ratio of RAM to CPU if the user does not provide one. Must be a list of the minimum and maximum.
	- default is [8, 8]
- **ec2_amis** - A dictionary of dictionaries to store [AMI](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/AMIs.html) info.
	- Needs three parameters: 
		- ami id
        - minimum disk size
        - [device name](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/device_naming.html)
    - Optional parameters:
      	- [AWS IMDS max hops](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html)
	- E.g.
	```yaml
	ec2_amis:
	  single:
	    ami: ami-abcdefghi12345678
	    disk: 30
	    disk_device_name: /dev/sda1
	    aws_imds_max_hops: 2
	  cluster:
	    ami: ami-12345678abcdefghi
	    disk: 30
	    disk_device_name: /dev/xvda
	  single_gpu:
	    ami: ami-abcdefghi00000000
	    disk: 90
	    disk_device_name: /dev/sda1
	    aws_imds_max_hops: 2
	```
- **ec2_key** - The [key pair](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html) name used to ssh into the EC2. This will be stored in `forge_pem_secret`
- **ec2_max** - Override the default maximum amount of RAM a single instance can have. The default is 768.
- **excluded_ec2s** - List of EC2 types to not consider when creating instances. You can use strings with one or more wild cards, represented by an asterisk (\*)
	- E.g.
	```yaml
	excluded_ec2s: ["*g.*", "gd.*", "*metal*", "g4ad*"]
	```
- **forge_env** - Name of the Forge environment. The user will refer to this in their yaml.
- **forge_pem_secret** - The secret name where the `ec2_key` is stored
- **on_demand_failover** - If using engine mode and all spot attempts (market: spot + spot retries) have failed, run a final attempt using on-demand.
- **spot_retries** - If using engine mode, sets the number of times to retry a spot instance. Only retries if either market is spot.
- **tags** - [Tags](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html) to apply to instances created by Forge. Follows the AWS tag format. 
	- Forge also exposes all string, numeric, and some extra variables from the combined user and environmental configs that will be replaced at runtime by the matching values (e.g. `{name}` for job name, `{date}` for job date, etc.) See the [variables](variables.md) page for more details.
	- E.g.
	```yaml
	tags:
	  - Key: "Name"
	    Value: "{name}-{market}-{task}-{date}"
	  - Key: "Application"
    	Value: "{name}"
	  - Key: "User"
	    Value: "{user}"
  ```
- **user_data** - Paths to the default [user_data](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html) scripts. Can be overwritten by the user.
	- Forge also exposes all string, numeric, and some extra variables from the combined user and environmental configs that will be replaced at runtime by the matching values (e.g. `{name}` for job name, `{date}` for job date, etc.) See the [variables](variables.md) page for more details.
	- **Note** Forge uses the root user to rsync and run. One way to allow this is to add the below to the user data.
	```bash
	#!/bin/bash
	set -x
	echo "$(cat /root/.ssh/authorized_keys | sed 's/^.*ssh-rsa/ssh-rsa/')" > /root/.ssh/authorized_keys
	```