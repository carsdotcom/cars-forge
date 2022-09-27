"""Extract a section of the changelog specific to a given version."""
import configparser

config = configparser.ConfigParser()
with open(".bumpversion.cfg", "r", encoding="utf-8") as fobj:
    config.read_file(fobj)
    version = config['bumpversion']['current_version']

rn = f"""
```
pip install cars-forge=={version}
```

---"""
with open("CHANGELOG.md", "r", encoding="utf-8") as changelog:
    is_read = False
    for line in changelog:
        # Starting current version section of changelog
        if version in line:
            is_read = True
        # Done with current version
        elif line.startswith("## [") and version not in line:
            is_read = False
        elif is_read and (line != ""):
            rn += line

# Print version to stdout. This should be captured by a workflow step:
# python generate_rn.py >> $GITHUB_ENV
print(f"VERSION={version}")

with open("release_notes.md", "w", encoding="utf-8") as release_notes:
    release_notes.write(rn)
