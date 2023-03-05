REM pytest suite on all tht

REM activate hte environment
call "%~dp0../activate_py.bat"
 
REM call pytest
python -m pytest --maxfail=10 %~dp0

pause