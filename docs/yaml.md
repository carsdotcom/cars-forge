[Home](index.md)

---

# Yaml

Each forge command certain parameters. A yaml file with all the parameters can be provided or you can submit the parameters as a CLI parameter at runtime. The CLI parameters will always overwrite the yaml parameters.

- **aws_role** - The IAM role forge-*aws_role*-*forge_env* will be attached to the EC2s spun up by Forge.
- **cpu** - Minimum amount of vCPU required. Can be a range e.g. [2, 4].
    - If using a cluster, you must specify both the master and worker. Master first, worker second. 
      ```yaml
      cpu:
      - 2, 4
      - 32, 64
      ```
    - If using single, only 1 value is needed.
      ```yaml
      cpu:
        - 2,4
      ```
    - If running via the command line, a range of values is passed as: ``--cpu [[1,2]]``.
    - If cpu is not provided, ram is needed. cpu is calculated using ram and ram-to-cpu ratio (default is 8)
- **date** - An optional parameter. Can be used in the run_cmd or name. 
- **destroy_after_failure** - Runs `forge destroy` if `forge create`, `forge engine`, or `forge run` has an unsuccessful run. True or False. Default is True
    - If running via the command line use `no_destroy_after_failure` 
- **destroy_after_success** - Runs `forge destroy` if `forge engine` or `forge run` has a successful run. True or False. Default is True
    - If running via the command line use `no_destroy_after_success` 
- **disk** - Disk size of the instance. Default is set up by the admin depending on the ami.
- **forge_env** - The environment that corresponds with the environment yaml created by the admin. This houses all the AWS information that is required but won't change much between each run.
- **gpu_flag** - Starts an instance with a GPU. Can be used only with docker. True or False. Default is False
- **log_level** - Override the default logging level (`info`). Valid options are: `debug`, `info`, `warning`, or `error`.
- **market** - Start the instances as spot or on-demand. The default is spot.
    - If using a cluster, you must specify both the master and worker. Master first, worker second.
      ```yaml
      market:
        - on-demand
        - spot
      ```
    - If using single, only 1 value is needed.
      ```yaml
      market: spot
      ```
    - If running via the command line, a range of values is passed as: ``--market on-demand spot``.
- **name** - Name of the instance/cluster
- **on_demand_failover** - If using engine mode and all spot attempts (market: spot + spot retries) have failed, run a final attempt using on-demand.
- **ram** - Minimum amount of RAM required. Can be a range e.g. [16, 32]. 
    - If using a cluster, you must specify both the master and worker. Master first, worker second.
      ```yaml
      ram:
        - 8
        - 256, 512
      ```
    - If using single, only 1 value is needed.
      ```yaml
      ram:
        - 32
      ```
    - If running via the command line, a range of values is passed as: ``--ram [[8,16][512]]``.
    - If ram is not provided, cpu is needed. ram is calculated using cpu and ram-to-cpu ratio (default is 8)
- **ratio** - the ratio of ram-to-cpu. The default is 8 but can be overwritten.
    - If using a cluster, you must specify both the master and worker. Master first, worker second. 
      ```yaml
      ratio:
        - 8
        - 6,8
      ```
    - If using single, only 1 value is needed.
      ```yaml
      ratio:
        - 8
      ```
    - If running via the command line, a range of values is passed as: ``--ratio [[8][6,8]]``.
- **rsync_path** - The folder or file that will be copied to the instance. Folder or file will be written to the /root directory. 
    - Use the `--all` flag to rsync the file or folder to all the instances in a cluster.
- **run_cmd** - The command that will be ran on the master or single instance. The path is relative to `rsync_path`. Any arguments will be passed to the script as is. Special variables `{env}`, `{date}`, and `{ip}` are available and will be replaced at runtime by the instance values. All commands will run as the root user.
    - Use the `--all` flag to run the script on all the instances in a cluster.
    - E.g. `run_cmd: scripts/run.sh {env} {date} {ip}`
- **s3_path** - An AWS S3 URI to rsync to the Forge instance. Downloads the file locally and sends it to the instance.
- **service** - `cluster` or `single`
- **spot_strategy** - Select the [spot allocation strategy](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/create_fleet.html).
- **spot_retries** - If using engine mode, sets the number of times to retry a spot instance. Only retries if either market is spot.
- **user_data** - Custom script passed to instance. Will be run only once when the instance starts up.
- **valid_time** - How many hours the fleet will stay up. After this time, all EC2s will be destroyed. The default is 8.