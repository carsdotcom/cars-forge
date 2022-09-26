[Home](index.md)

---

# Stop

Forge stop will stop an on-demand instances. The instance itself will no longer incur cost, but the attached EBS (disk space) will.

### How to Run

1. `forge stop` 
	- **ALL** the parameters must be the same as when forge create was ran
	- A yaml file with all the required parameters can be provided
	- Each yaml parameter can be over written at run time.
	- E.g. `forge stop --yaml /home/docker.yaml --market on-demand`
2. Works only on on-demand instances 

### Parameters

#### Required 
1. `name`
2. `service`
3. `forge_env`

#### Optional 
1. `market`
2. `date`