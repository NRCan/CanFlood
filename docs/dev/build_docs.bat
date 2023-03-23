:: building CanFlood sphinx documentation from source 

:: set environment settings
call "%~dp0..\env\settings.bat"

:: clear the old
RMDIR /S /Q %OUT_DIR%

:: setup pyqgis environment
 
call %ACTIVATE_BAT%

:: ammend path
:: something is wonky with the virtual env... not sure why it's tracking packages from my appdata/roaming
:: using pip install, it shows this as installed.. but it's not in the PATH
SET PATH=%PATH%;c:\Users\cefect\appdata\roaming\python\Python39\Scripts

 
:: call the sphinx HTML builder
ECHO on
call sphinx-build -b html -v -T -n -w sphinx_warnings.txt %SRC_DIR_DOC% %OUT_DIR_DOC%

:: launch the result
call %OUT_DIR_DOC%\index.html

ECHO sphinx documentation built. check log file for details.

cmd.exe /k