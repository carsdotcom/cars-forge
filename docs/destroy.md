[Home](index.md)

---

# Destroy

Forge destroy will terminate the EC2 fleet when the instances are no longer needed. All EC2s and EBS will be terminated to stop incuring cost.

### How to Run

1. `forge destroy`

- **ALL** the required parameters must be the same as when `forge create` was ran
- A yaml file with all the parameters can be provided
- Each yaml parameter can be overwritten at run time.
- E.g. `forge destroy --yaml /home/docker.yaml --name test123`

2. It will take about 1 minute depending on the service  

### Parameters

#### Required

1. `name`
2. `service`
3. `forge_env`

#### Optional

1. `market`
2. `date`
3. `yaml`
