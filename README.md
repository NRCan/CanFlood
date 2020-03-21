# CanFlood
Flood Risk modelling toolbox for Canada

## Beta 0.1.0 Release

Here are the working tools:

  Build: Setup, Hazard Sampler, Event Variables, Conditional Probabilities, DTM Sampler, Validation, Other

  Model: Setup, Risk (L1), Impacts (L2), Risk (L2)

  Results: none

We welcome/encourage any comments, bugs, or issues you have/find. Please create a GitHub 'issue' ticket (on the issue tab) to let us know about these things.

Happy flood modelling!

## Installation Instructions 

1) ensure Qgis 3.10.3-A Coruña LTR or newer  is installed and working on your system [link](https://qgis.org/en/site/forusers/download.html). We recommend using the OSGeo4W installer (selecting 'advanced install') to better manage versions and dependnecies (in particular 'pandas' doesn't seem to be installed by default with some distributions).

2) In Qgis, install the plugin 'First Aid' from the plugin repository (https://plugins.qgis.org/plugins/firstaid/). This plugin provides additional support for viewing errors in other plugins (essential during the development stage).

3) [Download the Plugin zip here](https://github.com/IBIGroupCanWest/CanFlood/raw/dev/CanFlood_010_20200320.zip) or from above CanFlood_010_20200320.zip (right click > save as) 

4) In Qgis, extract this plugin to your profile (Plugins > Manage and Install... > Install from Zip > navigate to the .zip > Install Plugin)

5) In Qgis, Turn the plugin on (Plugins > Manage and Install ... > Installed > check 'CanFlood'. If a dependency error is thrown, see 'troubleshooting' below.

6) Ensure that the plugin 'Processing' is similarly activated

### Troubleshooting Installation.

Some installations of QGIS may not come pre-installed with all required packages and dependencies. If you get a ModuleNotFound error regarding 'pandas', see the following [solution](https://github.com/IBIGroupCanWest/CanFlood/issues/6#issuecomment-592091488) with screenshots.


## Getting Started

Read the above '[CanFlood_UsersManual_010.pdf](https://github.com/IBIGroupCanWest/CanFlood/raw/dev/CanFlood_UsersManual_010.pdf)' and work through the tutorials.


## I'm getting Errors!
Check to see if there is a similar issue on the above '[Issues](https://github.com/IBIGroupCanWest/CanFlood/issues)' tab.  Hopefully this thread will resolve the problem, if not, reply to the thread.

If there is no issue ticket yet, create a new one on the above '[Issues](https://github.com/IBIGroupCanWest/CanFlood/issues)' tab with a screen shot of the error (and output from the QGIS plugin First Aid if possible). 

Using this issue tracker will help us track all the problems, and provide a useful reference for other users.

Happy Flood Modelling!


