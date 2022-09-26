[Home](index.md)

---

# Engine

Forge engine runs [create](create.md), [rsync](rsync.md), and [run](run.md) in order. If `destroy_after_success` and `destroy_after_failure` are set to the default `true`, Forge engine will also destroy the fleet after run. This makes it easy for you to run any job end-to-end with one command. 

### How to Run

1. `forge engine` 
	- A yaml file with all the required parameters can be provided
	- Each yaml parameter can be overwritten at run time.
	- E.g. `forge engine --yaml /home/docker.yaml --name test123`

### Parameters

#### Required 
1. `name`
2. `service`
3. `aws_role`
4. `forge_env`
5. Either `ram` or `cpu`
6. `run_cmd`
7. `rsync_path`


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
