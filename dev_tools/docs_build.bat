:: Building CanCurve sphinx documentation (w/o RTD)

 

:: activate docs environment
call l:\09_REPOS\01_COMMON\sphinx\env\conda_activate.bat

:: call the shpinx make script
:: call %~dp0..\docs\make.bat html
:: difficult to customize


:: change to documentation
 
cd %~dp0..\docs

:: call builder CLI
ECHO on
 
sphinx-build -M html .\source .\build --jobs=4 --verbose --show-traceback --nitpicky --warning-file=.\build\sphinx_warnings.txt -c .\source


:: launch it
call build\html\index.html

cmd.exe