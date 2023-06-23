# Contributing to the CanFlood project

CanFlood is an open source project with major contributions from IBI Group funded by NRCan

## CanFlood Plugin update

Whether fixing a bug or introducing a new feature to CanFlood, contributors should adhere to the following in order to make their work accessible to users via the QGIS plugin repository.

To help track the workflow, the following template is generally copied into a new issue and associated with a github project.

### Integrate changes to dev branch

the dev branch is where new features and fixes are collected and tested before release. The following should be executed on the dev branch in preparation for pushing to the main branch:

- [ ] add/update [sphinx+RTD english documentation]([url](https://github.com/NRCan/CanFlood/tree/master/docs/source)) where applicable

- [ ] backwards merge master into dev to capture any upstream changes (these should be minor and limited to documentation tweaks as all development is done on the dev branch)

- [ ] ensure the version tag is updated on \canflood\build\build.ui

- [ ] update the README.md to summarize any new features for users

- [ ] similarly update canflood\metadata.txt

- [ ] execute all pytests. investigate warnings. fix errors. 

- [ ] perform a 'person test' by having a non-developer follow relevant tutorials. investigate warnings and fix errors.

- [ ] Once these tests are complete **and passing**, a pull request should be completed and the dev branch merged into the main. 

### Add french language 

The following files/items may need french language content to be updated to reflect any new content from above

- [ ] canflood\metadata.txt
- [ ] sphinx+RTD documentation
- [ ] project readme.md
- [ ] release tag (see below)

### Publish the plugin

Now that all the code is tested and in the main branch, perform the following:

- [ ] delete all instances of \__pycache__\ in the source code

- [ ] zip the \canflood subfolder to some temporary directory

- [ ] login to [plugins.qgis.org](https://plugins.qgis.org/accounts/login/?next=/plugins/my) using the CanFlood credentials (ask Nicky). Navigate to **Upload a plugin** and select the zip file.

- [ ] In QGIS, refresh the repository and ensure that the new version is available (may take ~10mins for the version to be available). Upgrade and check that it works.

### Publish release on git-hub

- [ ] in git-hub, create a new release tag (e.g., v1.2.0), summarize new features for developers (in english and french). upload the same zip file. 

- [ ] notify the management team

## Development environment

We usually develop CanFlood to target the QGIS LTR. The plugin itself (./canflood) does not require any additional dependencies and is easily installed via the repository. 
However, development requires some additional dependencies (e.g., pytest_qgis for testing and sphinx for building the documentation). 

### Building dev environment

To isolate this development environment from your main pyqgis build,  it's best to use a virtual environment.. which can be tricky to set up.
The batch script `./dev/pyqgis_venv_build.bat` has been provided to do this which requires the following steps: 
    1) create a batch script to initialize your system's pyqgis environment (if you haven't already done so). 
    2) create a `./env/settings.bat` to set your environment variables (see example below)
    3) call `./dev/pyqgis_venv_build.bat`, changing the value to 'true' when prompted. this should create a python virtual environment in `./env/pyqgis_cf` and install the additional dependencies. 
    
### Activating dev environment
The batch script `./dev/activate_py.bat` should activate the development environment (if the above is configured correctly). 
This is useful for running tests from command line. 
Note the amendments to PYTHONPATH

### Testing the environment
A simple way to test if the dependencies are installed is to import them within python:
```
python
>>> import qgis.core
>>> import pytest
>>> import pytest_qgis
```
if you encounter any errors, your environment is not set up correctly.

### Example settings.bat
```
:: CanFlood development environment variables and batch scripts

:: system pyqgis environment config file (should call c:\OSGeo4W\bin\o4w_env.bat at a minimum)
set PYQGIS_ENV_BAT=L:\09_REPOS\01_COMMON\Qall\bin\setup_pyqgis_ltr.bat

:: set the target directory for the environment
SET VDIR=%~dp0\pyqgis_cf

:: set the venv activation script
SET ACTIVATE_BAT=%VDIR%/Scripts/activate.bat
```
## Tests
see `./tests2/CONTRIBUTING.md`
    


        
