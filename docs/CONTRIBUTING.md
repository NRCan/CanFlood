# Contributing to the CanFlood project Documentation

We use Sphinx/RST and ReadTheDocs for the documentation.
Originally, the documentation was written in MS Word. 
It was ported to RST in ~2021 with much difficulty.
Some artifacts remain from this port. 

## Documentation standards
Each sentence should be on its own line (this makes it easier to track changes). 


### Cross-referencing
Tables and Figures should be cross-linked using Sphinx's [numref](https://www.sphinx-doc.org/en/master/usage/restructuredtext/roles.html#cross-referencing-figures-by-figure-number) role.
Reference labels should begin with 'tab' for tables, 'fig' for figures followed by a dash and a description of the asset.
For example:
```
Some international guidelines are provided in :numref:`tabl-guidelines`.

.. _tabl-guidelines:
```


### Tables
For tables, I suggest using the [CSV Table directive](https://docutils.sourceforge.io/docs/ref/rst/directives.html#csv-table-1). 
For example:
```
.. csv-table:: International Guidelines 
   :file: tables\international_guidelines.csv
   :widths: 30, 70
   :header-rows: 1
```
This makes it much easier to edit the content and control the display.


## Configuring Hosted docs (RTD)
We use [ReadTheDocs](https://readthedocs.org/projects/canflood/) to automate building, versioning, and hosting of the CanFlood documentation. 
To configure the project, you will need to request to be added to the project.

RTD builds documentation for the tags/branches shown on the **Active Versions** tab.
This list should automatically include the following:
- all new pull requests (hidden)
- any new tag
- dev
- latest=master




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
