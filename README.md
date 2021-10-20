# CanFlood
Open source flood risk modelling toolbox for Canada

![alt text](https://github.com/NRCan/CanFlood/blob/master/img/logo_20210419_500.png)

## Phase 3 Development
Phase 3 is underway to incorporate all the excellent feedback received this year! Stay tuned for updates. 

## Beta 1.0 Release

[Launch Party!](https://www.ibiviz.com/CanFlood/)

Updated and tested against QGIS 3.16.6

We welcome/encourage any comments, bugs, or issues you have or find. Please create a GitHub 'issue' ticket (on the issue tab) to let us know about these things.

Happy flood risk modelling!

## Documentation
Select 'stable' in the [documentation](https://canflood.readthedocs.io/en/stable/#)

## Installation Instructions 

1) Ensure QGIS 3.16.6 LTR is installed and working on your system ([Qgis all releases download page](https://qgis.org/downloads/)). Ensure the 'processing' plugin is installed and enabled in QGIS.

2) Ensure the required python packages or dependencies shown in the [requirements file](https://github.com/NRCan/CanFlood/tree/master/requirements) are installed. Typically, this step is skipped and users just attempt to use the tool until an error is thrown. As of last test, a default install of QGIS 3.16.6 included all the CanFlood dependencies except 'openpyxl' (needed by the 'results - BCA' tools). Instructions for installing additional python packages in QGIS are provided [here](https://github.com/NRCan/CanFlood/issues/6).

3) Install the plugin from the QGIS repository (Plugins > Manage and Install... > All > search for CanFlood > Install). If a dependency error is thrown, see 'troubleshooting' below.  If successful, you should see the three CanFlood buttons on your toolbar and a 'CanFlood' entry in the 'Plugins' menu.

4) If you're re-installing or upgrading, it is safest to first uninstall CanFlood and restart QGIS before continuing with a new install.  

5) We recommend implementing the QGIS DEBUG logger for more detailed readouts and CanFlood model debugging. See [this post](https://stackoverflow.com/a/61669864/9871683) for insturctions.

### tl;dr
Install from the QGIS plugin repository.  

### Troubleshooting Installation

As both QGIS and CanFlood are active open source projects, getting your installation configured can be challenging, especially if you lack admin privileges to your machine and have no pyqgis experience. Some installations of QGIS may not come pre-installed with all the required python packages and dependencies listed in the [requirements](https://github.com/NRCan/CanFlood/tree/master/requirements) file.  If you get a ModuleNotFound error, your QGIS install does not have the required packages. This can easily be remedied by a user with admin privileges and working pyqgis knowledge.  The following [solution](https://github.com/NRCan/CanFlood/issues/6#issuecomment-592091488) provides some guidance on installing third party python modules, but you'll likely need admin privileges. 


## Getting Started

To get started with CanFlood, we recommend reading the latest users manual from the [manuals folder](https://github.com/NRCan/CanFlood/tree/master/manual) and working through the tutorials.


## I'm getting Errors!
As CanFlood is an active open-sourced project, users will often encounter errors which can be frustrating.  To work through these errors, we recommend first checking to see if there is a similar issue on the above '[Issues](https://github.com/NRCan/CanFlood/issues)' tab.  If so, hopefully the thread will resolve the problem, if not, reply to the thread with more details on your problem and why the posted solution did not work.

If there is no issue ticket yet, follow the instructions [here](https://github.com/NRCan/CanFlood/issues/49).

## CanFlood needs more features!
We agree. Consider contacting a CanFlood developer to sponsor new content that suites your needs, or joining the development community. Whether you'd like to integrate CanFlood modelling with some existing local databases, or integrate some other flood risk models into your analysis, or develop new output styles, the CanFlood project wants to hear from you. Please post a new issue [here](https://github.com/NRCan/CanFlood/issues/new) with an 'enhancement' label.
