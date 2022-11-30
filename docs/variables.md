[Home](index.md)

---

# Variables

Forge exposes all string and numeric (ints and floats) variables from the combined user and environmental configs, some extra variables, and any environment-specific additional variables (regardless of type) to be used in `tags` (defined in the environment yaml), `run_cmd`, and `user_data` configs.

- E.g.
  - `tags`

  ```yaml
  tags:
    - Key: "Name"
      Value: "{name}-{market}-{task}-{date}"
  ```

  - `user_data`

  ```bash
  aws ec2 describe-instances --filters "Name=tag:Name,Values={name}-{market_master}-{service}-master-{date}"
  ```

  - `run_cmd`

  ```yaml
  run_cmd: single_run.sh {ip} carsforge/jupyter-example:latest
  ```

### List of available variables

- **aws_az**
- **aws_profile**
- **aws_security_group**
- **aws_subnet**
- **ec2_key**
- **forge_env**
- **forge_pem_secret**
- **aws_role**
- **date**
- **disk**
- **forge_env**
- **gpu_flag**
- **log_level**
- **market_master**
- **market_worker**
- **name**
- **service**
- **task** - Either `cluster_master`, `cluster_worker`, or `single`
- **ip** - This is the IP of the master in a cluster (only exposed to run_cmd)

- **additional_config** - The `name` of each individual parameters defined in `additional_config` will be passes.
