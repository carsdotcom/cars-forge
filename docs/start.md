[Home](index.md)

---

# Start

Forge start will start a stopped on-demand instance.

### How to Run

1. `forge start` 
	- **ALL** the parameters must be the same as when forge create was ran
	- A yaml file with all the required parameters can be provided
	- Each yaml parameter can be overwritten at run time.
	- E.g. `forge start --yaml /home/docker.yaml --market on-demand`
2. Works only on on-demand instances.

### Parameters

#### Required 
1. `name`
2. `service`
3. `forge_env`

#### Optional 
1. `market`
2. `date`