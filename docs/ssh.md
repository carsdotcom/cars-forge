[Home](index.md)

---

# SSH

Forge will SSH you into your single or master instance. Forge will pull the pem file from secret manager. 

### How to Run

1. `forge ssh` 
	- **ALL** the parameters must be the same as when forge create was ran
	- A yaml file with all the required parameters can be provided
	- Each yaml parameter can be overwritten at run time.
	- E.g. `forge ssh --yaml /home/docker.yaml --name test123`
2. You will be SSHed in as the root user to the /root folder.

### Parameters

#### Required 
1. `name`
2. `service`
3. `forge_env`

#### Optional 
1. `market`
2. `date`