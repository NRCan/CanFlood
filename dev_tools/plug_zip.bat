:: plugin deployment help

:: setup environment
call %~dp0../env/activate_py.bat

ECHO on

SET PATH=C:\ProgramData\chocolatey\bin;%PATH%

:: change to plugin directory
cd %SRC_DIR%
 
REM ** 1) Remove __pycache__ directories **
for /d /r %PLUGIN_DIR% %%d in (__pycache__) do rd /s /q "%%d"

REM ** 2) Create a zip file **
 
if exist %PROJ_NAME%.zip del %PROJ_NAME%.zip 
 
7z a %PROJ_NAME%.zip %PLUGIN_DIR%

 

REM ** 3) Copy the zip file **
::move %PROJ_NAME%.zip "%SRC_DIR%\plugin_zips" /Y
xcopy %PROJ_NAME%.zip %SRC_DIR%\plugin_zips /Y /I

if exist %PROJ_NAME%.zip del %PROJ_NAME%.zip 

ECHO finished creating plugin zip file

cmd.exe /k