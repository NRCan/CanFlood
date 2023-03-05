# Contributing to the CanFlood project

CanFlood is an open source project with major contributions from IBI Group funded by NRCan

## CanFlood Plugin update

Whether fixing a bug or introducing a new feature to CanFlood, contributors should adhere to the following in order to make their work accessible to users via the QGIS plugin repository.

To help track the workflow, the following template is generally copied into a new issue and associated with a github project.

### Integrate changes to dev branch

the dev branch is where new features and fixes are collected and tested before release. The following should be executed on the dev branch in preparation for pushing to the main branch:

- [ ] backwards merge master into dev to capture any upstream changes (these should be minor and limited to documentation tweaks as all development is done on the dev branch)

- [ ] ensure the version tag is updated on \canflood\build\build.ui

- [ ] update the README.md to summarize any new features for users

- [ ] similarly update canflood\metadata.txt

- [ ] execute all pytests. investigate warnings. fix errors. 

- [ ] perform a 'person test' by having a non-developer follow relevant tutorials. investigate warnings and fix errors.

- [ ] Once these tests are complete **and passing**, a pull request should be completed and the dev branch merged into the main. 


### Publish the plugin

Now that all the code is tested and in the main branch, perform the following:

- [ ] delete all instances of \__pycache__\ in the source code

- [ ] zip the \canflood subfolder to some temporary directory

- [ ] login to [plugins.qgis.org](https://plugins.qgis.org/accounts/login/?next=/plugins/my) using the CanFlood credentials (ask Nicky). Navigate to **Upload a plugin** and select the zip file.

- [ ] In QGIS, refresh the repository and ensure that the new version is available (may take ~10mins for the version to be available). Upgrade and check that it works.

### Publish release on git-hub

- [ ] in git-hub, create a new release tag (e.g., v1.2.0), summarize new features for developers. upload the same zip file. 

- [ ] notify the management team

## Development environment


We usually develop CanFlood to target the QGIS LTR. The plugin itself (./canflood) does not require any additional dependencies and is easily installed via the repository. 
However, development requires some additional dependencies (e.g., pytest_qgis). 

### Building dev environment

To isolate this development environment from your main pyqgis build,  it's best to use a virtual environment.. which can be tricky.
The batch script `./pyqgis_venv_build.bat` has been provided to do this. 
    1) create a batch script to initialize your system's pyqgis environment (if you haven't already done so). 
    2) populate `./settings.bat` with this (and other) variables
    3) call `./pyqgis_venv_build.bat`, changing the value to 'true' when prompted. this should create a python virtual environment in ./venv and install the additional dependencies. 
    
    
### Activating dev environment
The batch script `./activate_py.bat` should activate the development environment (if the above is configured correctly). This is useful for running tests from command line. 
    
    


        
