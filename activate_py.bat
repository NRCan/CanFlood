echo off
REM script to activate python environment (for tests)

REM set the caller paths
call %~dp0/settings.bat
echo on
REM check it exists
if exist %PYQGIS_ENV_BAT% (
  echo valid PYQGIS_ENV_BAT 
) else (
  echo PYQGIS_ENV_BAT does not exist
)

REM activate the system pyqgis environment
ECHO off
call "%PYQGIS_ENV_BAT%"
ECHO python environment activated from %PYQGIS_ENV_BAT%

REM activate virtual environment
call "%ACTIVATE_BAT%"

REM ammend paths
set PYTHONPATH=%PYTHONPATH%;%~dp0\canflood;%~dp0\tools

ECHO PYTHONPATH:
ECHO %PYTHONPATH%
