# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **GitHub** - Workflow to run unittests on every PR and push to main.

### Changed
- **Common** - Move EC2 pricing calls to single function in `common.py`.
- **Readme** - Added new badges to the Readme
- **Forge** - Added error to show when SSH credentials are invalid


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

[unreleased]: https://github.com/carsdotcom/cars-forge/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/carsdotcom/cars-forge/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/carsdotcom/cars-forge/releases/tag/v1.0.0
