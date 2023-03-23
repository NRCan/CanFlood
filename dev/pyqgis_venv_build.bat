:: build a CanFlood development virtual environment

:: set your environment settings (sets VDIR, ACTIVATE_BAT, PYQGIS_ENV_BAT)
call %~dp0..\env\settings.bat

:: activate the pyqgis environment
call %PYQGIS_ENV_BAT%
 
:: setup the virtual environment
ECHO building venv in %VDIR%
python -m venv --without-pip --copies "%VDIR%"
cd "%VDIR%"

ECHO launching pyvenv.cfg. set --system-site-packages = true
Notepad pyvenv.cfg

:: activate the venv
call "%ACTIVATE_BAT%"

:: install depdencies
python -m pip install -r %~dp0\requirements.txt

ECHO finished
cmd.exe /k

 