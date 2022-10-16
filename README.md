# CanFlood
Open source flood risk modelling toolbox for Canada

![alt text](https://github.com/NRCan/CanFlood/blob/master/img/logo_20210419_500.png)


Updated and tested against QGIS 3.22.8 (Qt 5.15.3)

We welcome/encourage any comments, bugs, or issues you have or find. Please create a GitHub 'issue' ticket [following these instructions](https://github.com/NRCan/CanFlood/issues/6) to let us know about these things.

Happy flood risk modelling!


## Documentation
[Documentation](https://canflood.readthedocs.io/en/latest/#) is provided for the latest and archived versions. 


## Phase 3 Development

[v1.2.0](https://github.com/NRCan/CanFlood/releases/tag/v1.2.0) is released with the following major new features:
1) [new tool](https://canflood.readthedocs.io/en/dev/05_toolsets.html#report-automator) for generating a pdf report of your model.

[v1.1.0](https://github.com/NRCan/CanFlood/releases/tag/v1.1.0) is released with three major new features:
1) Very nice sphinx/readTheDocs [documentation](https://canflood.readthedocs.io/en/latest/#) thanks in large part to Dhanyatha. This is much easier to browse than the previous pdfs and facilitates preservation of previous, current, and development (and eventually French) versions of the manual.
2) [new module](https://canflood.readthedocs.io/en/latest/toolsets.html#sensitivity-analysis) providing workflow and tools for performing sensitivity analysis on a L1 or L2 CanFlood models. This can be helpful in understanding and communicating the uncertainty in your model, as well as help identify which parameters should be prioritized during data collection.
3) [per-asset Sampling for Complex Geometries](https://canflood.readthedocs.io/en/latest/toolsets.html#hazard-sampler) providing more flexibility in how hazard variables are sampled from complex geometries. 

## Installation Instructions 

1) Ensure the QGIS and Qt version 'tested' above is installed and working on your system ([Qgis all releases download page](https://qgis.org/downloads/)). Ensure the 'processing' plugin is installed and enabled in QGIS.  

2) Ensure the required python packages or dependencies shown in the [requirements file](https://github.com/NRCan/CanFlood/blob/master/canflood/requirements.txt) are installed. Typically, this step is skipped and users just attempt to use the tool until an error is thrown. As of last test, a default install of QGIS 3.16 included all the CanFlood dependencies except 'openpyxl' (needed by the 'results - BCA' tools). Instructions for installing additional python packages in QGIS are provided [here](https://github.com/NRCan/CanFlood/issues/6).

3) Install the plugin from the QGIS repository (Plugins > Manage and Install... > All > search for CanFlood > Install). If a dependency error is thrown, see 'troubleshooting' below.  If successful, you should see the three CanFlood buttons on your toolbar and a 'CanFlood' entry in the 'Plugins' menu.

4) If you're re-installing or upgrading, it is safest to first uninstall CanFlood and restart QGIS before continuing with a new install.  

5) We recommend implementing the QGIS DEBUG logger for more detailed readouts and CanFlood model debugging. See [this post](https://stackoverflow.com/a/61669864/9871683) for instructions.

### tl;dr
Install from the QGIS plugin repository.  

### Troubleshooting Installation

As both QGIS and CanFlood are active open source projects, getting your installation configured can be challenging, especially if you lack admin privileges to your machine and have no pyqgis experience. Check the [issues](https://github.com/NRCan/CanFlood/issues?q=is%3Aissue) for solutions.

QGIS has retired their old installer and is no longer supporting 32-bit binaries. If you get a 'Couldn't load plugin 'canflood'' error after installing the plugin (or you have a Qt version <5.15.2), you need to install QGIS using the new standalone (msi) installers, see [this solution](https://github.com/NRCan/CanFlood/issues/27).

Some installations of QGIS may not come pre-installed with all the required python packages and dependencies listed in the [requirements](https://github.com/NRCan/CanFlood/blob/master/canflood/requirements.txt) file.  If you get a ModuleNotFound error, your QGIS install does not have the required packages. This can easily be remedied by a user with admin privileges and working pyqgis knowledge.  The following [solution](https://github.com/NRCan/CanFlood/issues/6#issuecomment-592091488) provides some guidance on installing third party python modules, but you'll likely need admin privileges. 


## Getting Started

To get started with CanFlood, we recommend reading the [documentation](https://canflood.readthedocs.io/en/latest/#) and working through the tutorials.


## I'm getting Errors!
As CanFlood is an active open-sourced project, users will often encounter errors which can be frustrating.  To work through these errors, we recommend first checking to see if there is a similar issue on the above '[issues](https://github.com/NRCan/CanFlood/issues?q=is%3Aissue)' tab.  If so, hopefully the thread will resolve the problem, if not, reply to the thread with more details on your problem and why the posted solution did not work.

If there is no issue ticket yet, follow the instructions [here](https://github.com/NRCan/CanFlood/issues/6) to post a new issue.

## CanFlood needs improvement!
We agree. Consider contacting a CanFlood developer to sponsor improvement that suites your needs, or joining the development community. Whether you'd like to integrate CanFlood modelling with some existing local databases, or integrate some other flood risk models into your analysis, or develop new output styles, the CanFlood project wants to hear from you. Please post a new issue [here](https://github.com/NRCan/CanFlood/issues/new) with an 'enhancement' label.
