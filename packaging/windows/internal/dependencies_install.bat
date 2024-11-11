@echo on

:: Call the install_vcpkg.bat script to ensure vcpkg is installed and bootstrapped
call vcpkg_install.bat
if %errorlevel% neq 0 (
    echo Failed to install or bootstrap vcpkg
    exit /b %errorlevel%
)

:: Define the directory where vcpkg is installed
set VCPKG_DIR=%~dp0vcpkg

:: Install vcpkg dependencies using the vcpkg.json manifest file
echo vcpkg installing libraries
%VCPKG_DIR%\vcpkg install --feature-flags=manifests
if %errorlevel% neq 0 (
    echo Failed to install dependencies
    exit /b %errorlevel%
)
    