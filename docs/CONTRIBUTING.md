# Contributing to the CanFlood project Documentation

We use Sphinx and ReadTheDocs for the documentation.

## Building the documentation from source
To build from source, the following packages are needed:
- sphinx-rtd-theme
- Sphinx
 

The batch script `./docs/dev/build_docs.bat` is provided to demonstrate how to build from source using the same virtual environment described in `./CONTRIBUTING.md`. To use the script, do the following: 
- create a second `./docs/env/settings.bat` script to set the environment variables (see example below)
- run the `./docs/dev/build_docs.bat` to build to the specified location (NOTE: you may need to specify the path to sphinx-build in this script). This should launch an HTML of the documentation found in `./docs/source`. 
- review the log file for errors. 


## Example settings.bat
Note this requires the settings.bat described in `./CONTRIBUTING.md` to be configured as well.
```
:: settings for documentation development

:: main dev environment settings
call "%~dp0..\..\env\settings.bat"

:: location of documentation source
SET SRC_DIR_DOC=%~dp0..\source

:: directory to output build files to
SET OUT_DIR_DOC=%~dp0..\build
```
