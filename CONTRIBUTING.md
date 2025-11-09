# Contribution guidelines

Contributing to this project should be as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints (using `scripts/lint`).
4. Test you contribution.
5. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People _love_ thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

Use [black](https://github.com/ambv/black) to make sure the code follows the style.

## Test your code modification

This custom component provides a Home Assistant integration for ActronAir Neo systems.

It comes with development environment in a container, easy to launch
if you use Visual Studio Code. With this container you will have a stand alone
Home Assistant instance running and already configured with the included
[`configuration.yaml`](./config/configuration.yaml)
file.

### Development Workflow

1. **Setup Development Environment**

   ```bash
   scripts/setup
   ```

2. **Start Development Mode**

   ```bash
   scripts/develop
   ```

   This starts Home Assistant with the integration loaded for testing.

3. **Run Linting**

   ```bash
   scripts/lint
   ```

   Always run linting before committing changes.

4. **Check Logs**
   Monitor `config/home-assistant.log` for errors and warnings.

## Release Process

This section documents the complete process for creating a new release of the ActronAir Neo integration.

### Version Number Management

This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html) with a calendar-based major version:

- **Format**: `YYYY.MINOR.PATCH`
- **Example**: `2025.10.3`
  - `2025` - Year (major version)
  - `10` - Minor version (new features, non-breaking changes)
  - `3` - Patch version (bug fixes, minor improvements)

### Files Requiring Version Updates

When preparing a release, update the version number in the following file:

1. **`custom_components/actronair_neo/manifest.json`**
   ```json
   {
     "version": "2025.10.3"
   }
   ```

### Step-by-Step Release Process

#### 1. Prepare the Release

1. **Update Version Numbers**

   - Update `custom_components/actronair_neo/manifest.json` with the new version number
   - Ensure the version follows the `YYYY.MINOR.PATCH` format

2. **Update CHANGELOG.md**

   - Move all items from `[Unreleased]` section to a new version section
   - Create the new version header with the release date:
     ```markdown
     ## [2025.11.0] - 2025-11-09
     ```
   - Ensure all changes are properly categorized under:
     - `### Added` - New features
     - `### Changed` - Changes to existing functionality
     - `### Fixed` - Bug fixes
     - `### Removed` - Removed features
   - Leave the `[Unreleased]` section empty for future changes

3. **Run Tests and Validation**

   ```bash
   # Run linting
   scripts/lint

   # Start development mode and verify integration loads
   scripts/develop

   # Check logs for errors
   tail -f config/home-assistant.log
   ```

4. **Commit Version Changes**
   ```bash
   git add custom_components/actronair_neo/manifest.json CHANGELOG.md
   git commit -m "Bump version to 2025.11.0"
   git push origin main
   ```

#### 2. Create and Push the Release Tag

1. **Create the Git Tag**

   ```bash
   # Create an annotated tag with the version number
   git tag -a 2025.11.0 -m "Release 2025.11.0"
   ```

2. **Push the Tag to GitHub**

   ```bash
   git push origin 2025.11.0
   ```

   **Important**: Pushing the tag will automatically trigger the GitHub Actions workflow that creates the release.

#### 3. Automated Release Creation

Once the tag is pushed, the GitHub Actions workflow (`.github/workflows/release.yml`) will automatically:

1. Extract the version number from the tag
2. Extract the corresponding section from CHANGELOG.md
3. Create a release archive (`.zip` file) containing the integration
4. Generate SHA256 checksums for the archive
5. Create a GitHub Release with:
   - Release title matching the version number
   - Release notes from CHANGELOG.md
   - Integration archive as a downloadable asset
   - SHA256 checksum file

#### 4. Verify the Release

1. Go to the [Releases page](https://github.com/ruaan-deysel/ha-actronair-neo/releases)
2. Verify the new release appears with:
   - Correct version number
   - Complete release notes from CHANGELOG.md
   - Downloadable `.zip` file
   - SHA256 checksum file

#### 5. Post-Release Tasks

1. **Announce the Release**

   - Update any relevant documentation
   - Notify users through appropriate channels

2. **Monitor for Issues**
   - Watch for bug reports related to the new release
   - Be prepared to create a patch release if critical issues are found

### Hotfix Release Process

For critical bug fixes that need immediate release:

1. Create a hotfix branch from the release tag:

   ```bash
   git checkout -b hotfix/2025.11.1 2025.11.0
   ```

2. Make the necessary fixes

3. Update version to `2025.11.1` (increment PATCH version)

4. Update CHANGELOG.md with the fix

5. Commit, merge to main, and create a new tag:
   ```bash
   git checkout main
   git merge hotfix/2025.11.1
   git tag -a 2025.11.1 -m "Hotfix 2025.11.1"
   git push origin main
   git push origin 2025.11.1
   ```

### Release Checklist

Use this checklist when creating a release:

- [ ] All changes are committed and pushed to `main`
- [ ] Version number updated in `manifest.json`
- [ ] CHANGELOG.md updated with new version section
- [ ] All items moved from `[Unreleased]` to new version section
- [ ] Linting passes (`scripts/lint`)
- [ ] Integration loads successfully in development mode
- [ ] No errors in Home Assistant logs
- [ ] Version changes committed and pushed
- [ ] Git tag created with correct version number
- [ ] Git tag pushed to GitHub
- [ ] GitHub Actions workflow completed successfully
- [ ] Release appears on GitHub with correct assets
- [ ] Release notes are complete and accurate

## License

By contributing, you agree that your contributions will be licensed under its Apache License 2.0.
