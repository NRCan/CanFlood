# Contributing to the CanFlood project

CanFlood is an open source project with major contributions from IBI Group funded by NRCan

## Plugin update procedures

Whether fixing a bug or introducing a new feature to CanFlood, contributors should adhere to the following in order to make their work accessible to users via the QGIS plugin repository.

### Integrate changes to dev branch

the dev branch is where new features and fixes are collected and tested before release. The following should be executed on the dev branch in preparation for pushing to the main branch:

1) execute all pytests. investigate warnings. fix errors. 

2) perform a 'person test' by having a non-developer follow relevant tutorials. investigate warnings and fix errors.

Once these tests are complete, a pull request should be completed to merge with the main branch.