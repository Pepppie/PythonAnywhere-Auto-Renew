# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-01-25

### Changed

- Overhauled README documentation for clarity, structure, and additional usage details

## [1.1.0] - 2026-01-10

### Added

- Manual workflow trigger via GitHub Actions `workflow_dispatch`
- Success/failure run logging, committed to `.github/logs/workflow_runs.log`
- MIT License

### Changed

- Refactored renewal and keep-alive logic for reliability
- Renamed and reorganized the renewal script
- Revised README for clarity and additional feature coverage

## [1.0.0] - 2026-01-10

### Added

- Initial renewal script (`renew_python_anywhere.py`) using `requests` + `BeautifulSoup`
- GitHub Actions workflow to run the renewal job on a schedule
- `.gitignore` for environment and IDE files
- Initial README

[Unreleased]: https://github.com/tanishqmudaliar/PythonAnywhere-Auto-Renew/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/tanishqmudaliar/PythonAnywhere-Auto-Renew/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/tanishqmudaliar/PythonAnywhere-Auto-Renew/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/tanishqmudaliar/PythonAnywhere-Auto-Renew/releases/tag/v1.0.0
