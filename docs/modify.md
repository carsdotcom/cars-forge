[Home](index.md)

---

# Modify (Experimental)

Forge modify will modify an existing EC2 fleet based on the supplied parameters.
How these changes are enacted may be unpredictable, and as such this action has been marked experimental.

### How to Run

1. `forge modify` 
	- A yaml file with all the required parameters can be provided
	- Each yaml parameter can be overwritten at run time.
	- E.g. `forge modify --yaml /home/docker.yaml --name test123`
2. The EC2 fleet configuration will be modified immediately, but the changes may take time to complete

### Parameters

#### Required 
1. `name`
2. `service`
3. `forge_env`
4. Either `ram`, `cpu`, or `instance_type`

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
12. `instance_type`
13. `architecture`