[Home](index.md)

---

# Run

Forge run will run any script on the single or master instance. You need to [rsync](rsync.md) the file over first. It will print the logs to the screen and provide a failure code if there is one. Forge will pull the pem file from secret manager.

### How to Run

1. `forge run`

- **ALL** the parameters must be the same as when `forge create` was ran
- A yaml file with all the required parameters can be provided
- Each yaml parameter can be overwritten at run time.
- Forge also exposes all string, numeric, and some extra variables from the combined user and environmental configs that will be replaced at runtime by the matching values (e.g. `{name}` for job name, `{date}` for job date, etc.) See the [variables](variables.md) page for more details.
  - If you are overriding the `run_cmd` parameter at run time, you must enclose it in quotes to prevent any argument misinterpretation.
- E.g. `forge run --yaml /home/docker.yaml --run_cmd '/home/test/run.sh ${date} ${env}'`

2. By default, the command will run on the single or master instance.

- The `--all` flag will run the command on all of the instances in the cluster

### Parameters

#### Required

1. `name`
2. `service`
3. `forge_env`
4. `run_cmd`

#### Optional

1. `market`
2. `date`
3. `all`
4. `destroy_after_failure`
5. `destroy_after_success`
