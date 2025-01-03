# Contributing to the CanFlood project

CanFlood is an open source project with numerous contributors

## Branches

### dev
the dev branch is where new features and fixes are collected and tested before release.

### master
the deployed project version

## CanFlood Plugin update

Whether fixing a bug or introducing a new feature to CanFlood, contributors should adhere to the following in order to make their work accessible to users via the QGIS plugin repository.
Execute the below steps to prepare and release an update.

### Step 1: Pull Request

- [ ] merge feature branches into dev branch. test and fix. 

- [ ] create a PR (dev > master) named "<plugin version> release candidate" (e.g., v1.2.0 release candidate). Copy this checklist into the description. 

- [ ] pull changes from master into dev branch (should just be small changes to .md files) 

- [ ] update the [documentation](./docs/CONTRIBUTING.md) if necessary. 

- [ ] ensure the documentation builds are passing on ReadTheDocs

- [ ] update the QGIS and CanFlood version tag on [build.ui](./canflood/build/build.ui) and the project [README.md](./README.md). 

- [ ] update the **Updates** section of the project [README.md](./README.md). 

- [ ] similarly update [plugin metadata file](./canflood/metadata.txt)
      
- [ ] update the plugin [requirements file](./canflood/requirements.txt) to capture the exact dependencies (`pip freeze`)

- [ ] execute all pytests. investigate warnings. fix errors. 

- [ ] use [plug_zip.bat](./dev_tools/plug_zip.bat) to create the plugin zip (`canflood.zip`) installable version of the release candidate in `./plugin_zips`

- [ ] perform a **person test** by having a non-developer follow relevant tutorials. investigate warnings and fix errors.

### Step 2: Release update on github

- merge and close the above PR (do not delete the dev branch)

- in git-hub, create a new release tag matching the plugin version tag (e.g., v1.2.0) from the recently updated master branch, summarize new features for developers. upload the plugin zip. 

### Step 3: Publish the plugin on the QGIS plugin repo

- login to [plugins.qgis.org](https://plugins.qgis.org/accounts/login/?next=/plugins/my) using the CanFlood credentials (ask Nicky). Navigate to **Upload a plugin** and select the plugin zip file.

- In QGIS, refresh the repository and ensure that the new version is available (may take ~10mins for the version to be available). From a clean profile, upgrade and check that it works.


## Setting up your development environment

For development, we generally use a virtual pyqgis environment pinned to the QGIS target version (see .\README.md) with the additional dependencies installed from `./requirements.txt`.
Generally, we launch this with batch scripts in the .\env folder (.gitignored)


### PYTHONPATH
Some tests and utilities expect the following PYTHONPATH:

 - ./
 - ./canflood
 - ./tools

