[Home](index.md)

---

# Example for single EC2

- Below we will walk through an example of how to use Forge to set up a python jupyter notebook. 

## [Setup](setup.md)

### AWS Setup

1. [Install](install.md) Forge on your computer or an EC2. 
2. In AWS, create a role that the Forge EC2 will use. The name of the role should be "forge-{aws_role}-{forge-env}".
	- Give this role any permission you need to complete the job. 
	- You should give this role ec2:Describe* permissions so the worker can attach to the master.
	- Select EC2 as the trusted AWS service
	- For this example, we will use `forge-test-example`.
3. Create a new user, group, or role that will run the Forge commands.
	- An example IAM policy can be found [here](https://github.com/carsdotcom/cars-forge/blob/main/examples/forge_user_IAM). This has the minimum permission Forge needs to run but can be modified.
	- Replace `ACCOUNT_ID` with your AWS account id. 
	- Replace the IAM names if you changed them. 
	- For this example, we will create a user called `forge-example`.
		- When creating the user, make sure to select Access key and download the keys. 
4. If you created a user, you need to setup the profile on the computer you will be running forge.
	- `aws configure --profile forge-example`
	- Enter in the Access key ID and then Secret access key
5. [Create new key pair](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html)
	- For this example, we will name it `test`.
6. Encode the key pair with base64. You can use [this site](https://www.base64encode.org/).
7. Create a new secret in [Secrets Manager](https://aws.amazon.com/secrets-manager/). The secret type is `Other type of secret` The secret name will be used in the [environment yaml](environmental_yaml.md) in the parameter "forge_pem_secret".
	- The secret key is `encoded_pem` and the value is the base64 encrypted key pair.
	- For this example we will name the secret `forge-pem`

### [Environment Yaml](environmental_yaml.md)

1. Referring to the [example yaml](https://github.com/carsdotcom/cars-forge/blob/main/examples/env_yaml_example/example.yaml), create your environment yaml file. For more information about the environment yaml, please refer to [environmental_yaml](environmental_yaml.md).
	- The tags, excluded_ec2s, secret name, and user data are prefilled with examples. All of the above and be used as is or updated.
	- The AWS AZ, AMI, aws_subnet and aws_security_group need to be updated for your environment.
2. Create your default user data script (optional). An example can be found [here](https://github.com/carsdotcom/cars-forge/blob/main/examples/env_yaml_example/single.sh).
	- In the `user_data` parameter in the environment yaml, you can specify what the default user data script should be if the user does not provide one.
	- `echo "$(cat /root/.ssh/authorized_keys | sed 's/^.*ssh-rsa/ssh-rsa/')" > /root/.ssh/authorized_keys` is needed in all user data scripts because Forge runs all commands as root.
3. Run `forge configure -h`
	- This will output the location of the configure folder.
	- Example: `Configure env yaml and place it in /home/ec2-user/.local/lib/python3.7/site-packages/forge/config/`
4. Create a new folder under the config folder.
	- E.g.
	```bash
	mkdir -p /home/ec2-user/.local/lib/python3.7/site-packages/forge/config/example
	```
5. Copy your environment yaml and user data script to the new folder.
	- E.g.
	```bash
	cp example.yaml single.sh /home/ec2-user/.local/lib/python3.7/site-packages/forge/config/example/
	```

## Run Example

1. In the Git repo, you will find an [example folder](https://github.com/carsdotcom/cars-forge/tree/main/examples/single_example) we will be using for this example. It included the yaml, user data script, and run script. For more information about the user yaml, please see the [yaml.md](yaml.md).
	- The single EC2 instance will have 16 or 32GB of RAM.
	- It will only stay up for 3 hours.
	- If there is a failure or if you cancel out of jupyter, the instance will be killed.
2. From inside the single_example folder, run `forge create --yaml single_example.yaml --user_data single_ud.sh`. Once the instance is created the hourly price will be printed.
3. Run `forge rsync --yaml single_example.yaml`
4. Run `forge run --yaml single_example.yaml`
5. Once completed, the jupyter URL will be printed. Copy and paste that into your browser and you will be able to run a python notebook.
6. Once done you can run `forge destroy --yaml single_example.yaml`
7. To run create, rsync, run, and destroy in one command, run `forge engine --yaml single_example.yaml --user_data single_ud.sh`.
