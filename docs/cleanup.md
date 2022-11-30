[Home](index.md)

---

# Cleanup

Forge cleanup will delete all the old [launch templates](https://docs.aws.amazon.com/autoscaling/ec2/userguide/launch-templates.html). Forge creates a template for every `forge create` request. `forge cleanup` deletes all the old templates that are no longer needed. Forge adds a tag called valid_time to each launch template which has the instance destroy time. If the valid_time is older than the forge cleanup runtime, the template will be destroyed.

### How to Run

1. `forge cleanup --forge_env`*forge_env*

### Parameters

#### Required

1. `forge_env`
