REM CanFlood development settings

REM system pyqgis environment config file (should set QREL and PYVER)
set PYQGIS_ENV_BAT=l:\09_REPOS\01_COMMON\Qall\pyqgis_config\OSGeo\3.28.4\setup_ltr.bat

REM set the target directory for the environment
SET VDIR=%~dp0\venv\CanFlood_dev

REm set the venv activation script
SET ACTIVATE_BAT=%VDIR%/Scripts/activate.bat