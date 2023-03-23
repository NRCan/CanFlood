:: run pytest suite on all tests in the directory

:: activate the environment
call "%~dp0../dev/activate_py.bat"
 
:: call pytest
python -m pytest --maxfail=10 %~dp0

cmd.exe /k