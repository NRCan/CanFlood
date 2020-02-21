@echo off
call "C:\IBI\_QGIS_\QGIS 3.8\bin\o4w_env.bat"
call "C:\IBI\_QGIS_\QGIS 3.8\bin\qt5_env.bat"
call "C:\IBI\_QGIS_\QGIS 3.8\bin\py3_env.bat"

@echo on
pyrcc5 -o resources.py resources.qrc