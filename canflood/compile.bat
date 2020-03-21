@echo off
set OSGEOW_HOME=C:\OSGeo4W64\

call %OSGEOW_HOME%\bin\o4w_env.bat
call %OSGEOW_HOME%\bin\qt5_env.bat
call %OSGEOW_HOME%\bin\py3_env.bat

@echo on
pyrcc5 -o resources.py resources.qrc

