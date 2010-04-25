@echo off
setLocal EnableDelayedExpansion


if "%1" == "" goto error

set progname= %1 
set progname=%progname: =%
set "tempdir=%progname%_temp"
set "specfile=%progname%.spec"

echo progname = %progname%
echo tempdir  = %tempdir%

svn info http://pyrat.googlecode.com/svn/trunk > svn_info

for /f "tokens=* delims= " %%a in (svn_info) do (
    echo %%a | find "Revision:" > nul
    if not errorlevel 1 set str=%%a
)
set revision=!str:~10!
echo checking out %progname% (revision=%revision%)

del /Q /F /S %tempdir%
svn co http://pyrat.googlecode.com/svn/trunk/%progname% %tempdir%

sed -i s/REV/%revision%/ %tempdir%\%progname%.py
del .\sed*

del /Q /F /S dist
del /Q /F /S build
del %specfile%
python C:\pyinstaller-1.4\Makespec.py --onefile --console --icon=%progname%.ico %tempdir%\%progname%.py
python C:\pyinstaller-1.4\Build.py %specfile%
del %specfile%
del warn%progname%.txt

move dist\%progname%.exe  .\%progname%.exe

del /Q /F /S %tempdir%
del /Q /F    svn_info
del /Q /F /S dist
del /Q /F /S build

:error
echo "USAGE:    %0 progname"

