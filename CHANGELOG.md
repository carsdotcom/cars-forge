# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-01-30

### Added
- **S3 sync** - Allow files to be synced to the Forge instance from an S3 bucket

### Changed
- **Subcommand arguments** - Allowed CLI arguments from any subcommand to be specified for any other

## [1.1.1] - 2024-12-12

### Changed
- **Python Version** - Bump minimum python version to 3.9.
- **Rsync** - Properly triggers retry sequence
- **Rsync** - Gives a return code now

### Fixed
- **Create** - Fix GPU AMI not being selected.
- **Parser** - Fix GPU flag not being passed properly to the config dict.
- **Create** - Better error reporting regarding RAM and CPU misconfigurations.


## [1.1.0] - 2024-02-26

### Added
- **Create** - Added `destroy_on_create`
- **Create** - Added `create_timeout` option
- **Common** - Moved all `n_list` functions to `get_nlist()`
- **Dependencies** - Updated dependencies and tested on latest versions
- **Create** - Set default boto3 session at beginning of create to resolve region bug
- **Create**
  - Multi-AZ functionality
  - Spot retries
  - On-demand Failover

### Changed
- **Create** - Configurable spot strategy
- **Documentation** - Updated with new changes


## [1.0.2] - 2022-10-27

### Added
- **Tests** - Test for `ssh.py` and `rsync.py` module.
- **GitHub** - Workflow to run unittests on every PR and push to main.

### Changed
- **SSH** - Add error to show when SSH credentials are invalid.
- **Dependencies** - Add `coverage` as a test dependency.
- **Readme** - Add new badges to the Readme.
- **Common** - Move EC2 pricing calls to single function in `common.py`.


## [1.0.1] - 2022-09-28

### Added
- **gitignore** - Use a `.gitignore` file to prevent accidentally committing unneeded files.
- **Version** - Use `bump2version` to manage project version.
- **Dependencies** - Add `bump2version` as a dev dependency.

### Changed
- **Metadata** - Fix License field and capitalize project urls.
- **GitHub** - Add step to create GitHub release after uploading to PYPI.
- **GitHub** - Update action to build and publish package only when version is bumped.
- **Forge** - Added automatic tag `forge-name` to allow `Name` tag to be changed.


## [1.0.0] - 2022-09-27

### Added
- **Initial commit** - Forge source code, unittests, docs, pyproject.toml, README.md, and LICENSE files.

[unreleased]: https://github.com/carsdotcom/cars-forge/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/carsdotcom/cars-forge/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/carsdotcom/cars-forge/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/carsdotcom/cars-forge/compare/v1.0.2...v1.1.0
[1.0.2]: https://github.com/carsdotcom/cars-forge/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/carsdotcom/cars-forge/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/carsdotcom/cars-forge/releases/tag/v1.0.0
