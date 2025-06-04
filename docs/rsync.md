[Home](index.md)

---

# Rsync

Forge rsync makes it simple for you to copy a folder or file from local to the forge instance(s).

### How to Run

1. `forge rsync` 
	- **ALL** the parameters must be the same as when `forge create` was ran
	- A yaml file with all the required parameters can be provided
	- Each yaml parameter can be overwritten at run time.
	- E.g. `forge rsync --yaml /home/docker.yaml --rsync_path /home/test/run.sh`
2. By default, the folder or file will be moved to /root/ of the single or master instance.
	- The `--all` flag will copy the folder of file to all of the instances in the cluster

### Parameters

#### Required 
1. `name`
2. `service`
3. `forge_env`
4. `rsync_path`

#### Optional 
1. `market`
2. `date`
3. `all`
4. `yaml`
5. `s3_path`