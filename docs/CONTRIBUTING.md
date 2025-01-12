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
Some international guidelines are provided in :numref:`tab-guidelines`.

.. _tab-guidelines:

<table here>
```


### Tables
For tables, use the [CSV Table directive](https://docutils.sourceforge.io/docs/ref/rst/directives.html#csv-table-1). 
For example:
```
.. csv-table:: International Guidelines 
   :file: tables\international_guidelines.csv
   :widths: 30, 70
   :header-rows: 1
```
This makes it much easier to edit the content and control the display.


## Building the documentation
see `.docs\source\conf.py`
Requires the environment specified in `./docs/requirements.txt`

### using sphinx (local standalone)

 


### ReadTheDocs (web-hosted)
We use [ReadTheDocs](https://readthedocs.org/projects/canflood/) to automate building, versioning, and hosting of the CanFlood documentation. 
To configure the project, you will need to request to be added to the [project](https://app.readthedocs.org/projects/canflood/).

RTD builds documentation for the tags/branches shown on the **Active Versions** tab.
This list should automatically include the following:
- all new pull requests (hidden)
- any new tag
- dev
- latest=master


see `./docs/.readthedocs.yaml`






 
