REM build a CanFlood development virtual environment

REM call the project settings
call %~dp0\settings.bat

REM configure the pyqgis environmemt (should set QREL and PYVER)
call %PYQGIS_ENV_BAT%
 
REM setup the virtual environment
ECHO building venv in %VDIR%
python -m venv --without-pip --copies "%VDIR%"
cd "%VDIR%"

ECHO launching pyvenv.cfg. set --system-site-packages = true
Notepad pyvenv.cfg

REM activate the venv
call "%ACTIVATE_BAT%"

REM install depdencies
python -m pip install -r %~dp0\requirements.txt

ECHO finished
cmd.exe

 