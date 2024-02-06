# Contributing to the CanFlood project

CanFlood is an open source project with major contributions from IBI Group funded by NRCan

## CanFlood Plugin update

Whether fixing a bug or introducing a new feature to CanFlood, contributors should adhere to the following in order to make their work accessible to users via the QGIS plugin repository.

To help track the workflow, the following template is generally copied into a new issue and associated with a github project.

### Integrate changes to dev branch

the dev branch is where new features and fixes are collected and tested before release. The following should be executed on the dev branch in preparation for pushing to the main branch:

- [ ] ensure the version tag is updated on \canflood\build\build.ui
      
- [ ] update \canflood\requirements.txt

- [ ] execute all pytests. investigate warnings. fix errors. 

- [ ] perform a 'person test' by having a non-developer follow relevant tutorials. investigate warnings and fix errors.

- [ ] Once these tests are complete, a pull request should be completed and the dev branch merged into the main. 

### Prepare main branch for publication

Now that all the code is tested and in the main branch, perform the following:

- [ ] update the README.md to summarize any new features for users

- [ ] similarly update canflood\metadata.txt

### Publish the plugin

- [ ] delete all instances of \__pycache__\ in the source code

- [ ] zip the \canflood subfolder to some temporary directory

- [ ] login to [plugins.qgis.org](https://plugins.qgis.org/accounts/login/?next=/plugins/my) using the CanFlood credentials (ask Nicky). Navigate to **Upload a plugin** and select the zip file.

- [ ] In QGIS, refresh the repository and ensure that the new version is available (may take ~10mins for the version to be available). Upgrade and check that it works.

### Publish release on git-hub

- [ ] in git-hub, create a new release tag (e.g., v1.2.0), summarize new features for developers. upload the same zip file. 

- [ ] notify the management team
