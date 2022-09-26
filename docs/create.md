[Home](index.md)

---

# Create

Forge create will create an EC2 fleet using the yaml file you provide. It will be able to determine the right EC2s to use for the fleet, create the fleet, and apply the correct tags and permissions.

### How to Run

1. `forge create` 
	- A yaml file with all the required parameters can be provided
	- Each yaml parameter can be overwritten at run time.
	- E.g. `forge create --yaml /home/docker.yaml --name test123`
2. It will take 2-8 minutes to spin up the fleet depending on the service and resources
3. You will get the IP of the master or single instance once completed 

### Parameters

#### Required 
1. `name`
2. `service`
3. `aws_role`
4. `forge_env`
5. Either `ram` or `cpu`

#### Optional 
1. `disk`
2. `valid_time`
3. `user_data`
4. `gpu_flag`
5. `log_level`
6. `market`
7. `ratio`
8. `destroy_after_success`
9. `destroy_after_failure`
10. `date`
11. `yaml`