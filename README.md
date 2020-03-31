# CanFlood
Flood Risk modelling toolbox for Canada

## Beta 0.2.0 Release

Here are the working tools:

  Build: Setup, Hazard Sampler, Event Variables, Conditional Probabilities, DTM Sampler, Validation, Other

  Model: Setup, Risk (L1), Impacts (L2), Risk (L2)

  Results: Setup, Risk Plot, Join Geo

We welcome/encourage any comments, bugs, or issues you have or find. Please create a GitHub 'issue' ticket (on the issue tab) to let us know about these things.

Happy flood risk modelling!

## Installation Instructions 

1) ensure Qgis 3.10.3-A Coruña LTR is installed and working on your system [link](https://qgis.org/en/site/forusers/download.html) with all the required python packages [requirements](https://github.com/IBIGroupCanWest/CanFlood/tree/master/requirements). We recommend using the OSGeo4W installer (selecting 'advanced install') to better manage versions and dependnecies (in particular, 'pandas' doesn't seem to be installed by default with some distributions).

2) In Qgis, install the plugin 'First Aid' from the plugin repository (https://plugins.qgis.org/plugins/firstaid/). This plugin provides additional support for viewing errors in other plugins (essential for communicating your crash reports back to the develpoment team).

3) Download the latest Plugin zip from the above [plugin_zips folder](https://github.com/IBIGroupCanWest/CanFlood/tree/master/plugin_zips) to your computer (Right Click...> Save As).

4) In Qgis, install the plugin to your profile from this zip  (Plugins > Manage and Install... > Install from Zip > navigate to the .zip > Install Plugin)

5) In Qgis, Turn the plugin on (Plugins > Manage and Install ... > Installed > check 'CanFlood'. If a dependency error is thrown, see 'troubleshooting' below.  If successful, you should see the three CanFlood buttons on your toolbar.

6) Ensure the plugin 'Processing' is similarly activated

### Troubleshooting Installation.

Some installations of QGIS may not come pre-installed with all the required python packages and dependencies listed in the [requirements](https://github.com/IBIGroupCanWest/CanFlood/tree/master/requirements) file. If you get a ModuleNotFound error, see the following [solution](https://github.com/IBIGroupCanWest/CanFlood/issues/6#issuecomment-592091488) with screenshots with guidance on installing third party python modules to your Qgis  build.


## Getting Started

Read the latest users manual from the  '[manuals folder](https://github.com/IBIGroupCanWest/CanFlood/tree/master/manual)' and work through the tutorials.


## I'm getting Errors!
Check to see if there is a similar issue on the above '[Issues](https://github.com/IBIGroupCanWest/CanFlood/issues)' tab.  Hopefully this thread will resolve the problem, if not, reply to the thread with more details on your problem and why the posted solution did not work.

If there is no issue ticket yet, create a new one on the above '[Issues](https://github.com/IBIGroupCanWest/CanFlood/issues)' tab with a screen shot of the error (and output from the QGIS plugin 'First Aid' if possible). 

Using this issue tracker will help us track all the problems, and provide a useful reference for other users.
