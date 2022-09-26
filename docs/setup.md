[Home](index.md)

---

# Setup

1. [Install](install.md) Forge on your computer or an EC2. 
2. In AWS, create a role that the Forge EC2 will use. The name of the role should be "forge-{aws_role}-{forge-env}".
	- Give this role any permission you need to complete the job. 
	- You should give this role ec2:Describe* permissions so the worker can attach to the master. 
	- Select EC2 as the trusted AWS service
3. Create a new user, group, or role that will run the Forge commands.
	- An example IAM policy can be found [here](https://github.com/carsdotcom/cars-forge/blob/main/examples/forge_user_IAM). This has the minimum permission Forge needs to run but can be modified. 
		- Replace `ACCOUNT_ID` with your AWS account id. 
		- Replace the IAM names if you changed them. 
	- If you are creating a user, make sure to select Access key and download the keys. 
4. If you created a user, you need to setup the profile on the computer you will be running forge.
	- `aws configure --profile forge-test`
	- Enter in the Access key ID and then Secret access key 
5. [Create new key pair](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html)
6. Encode the key pair with base64. You can use [this site](https://www.base64encode.org/).
7. Create a new secret in [Secrets Manager](https://aws.amazon.com/secrets-manager/). The secret type is `Other type of secret` The secret name will be used in the [environment yaml](environmental_yaml.md) in the parameter "forge_pem_secret".
	- The secret key is `encoded_pem` and the value is the base64 encrypted key pair.
8. Set up the forge environment using [environment yaml](environmental_yaml.md). There are two options to choose from.
9. Create a user yaml. An example can be found [here](https://github.com/carsdotcom/cars-forge/blob/main/examples/single_example/single_example.yaml)
10. Test by running `forge create --yaml example.yaml`. Once successful, destroy the cluster by running `forge destroy --yaml example.yaml`.
