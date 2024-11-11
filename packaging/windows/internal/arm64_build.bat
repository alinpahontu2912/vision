@echo on

:: install external libraries
call dependencies_install.bat
if %errorlevel% neq 0 (
    echo Failed to install dependencies
    exit /b %errorlevel%
)

:: Create python virtual environment
@REM python -m venv venv
@REM echo * > ./venv/.gitignore 
@REM call venv\Scripts\activate

:: activate arm64 environment TODO ->replace visual studio
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" arm64

:: TODO replace with link to wheel
pip install "C:\Users\spahontu\Downloads\pytorch-wheel (3)\torch-2.6.0a0+gitc35a011-cp312-cp312-win_arm64.whl"
pip install numpy

set VCPKG_ROOT=%~dp0vcpkg_installed\arm64-windows

set TORCHVISION_LIBRARY=%VCPKG_ROOT%\lib
set TORCHVISION_INCLUDE=%VCPKG_ROOT%\include
set DISTUTILS_USE_SDK=1

cd ..\..\..\

python setup.py bdist_wheel
