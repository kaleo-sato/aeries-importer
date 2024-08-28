@echo off
setlocal

:: Define variables
set "VENV_DIR=.venv"
set "REQUIREMENTS_FILE=requirements.txt"
set "SOURCE_DIR=%USERPROFILE%\aeries-importer"
set "NEEDED_FILES=credentials.json"

:: Function to ensure needed files are in the source directory
call :ensure_files

:: Change to source directory
cd /d "%SOURCE_DIR%"

:: Check if the virtual environment directory exists
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
)

:: Activate the virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

:: Install the required packages
if exist "%REQUIREMENTS_FILE%" (
    echo Installing required packages...
    pip install -r "%REQUIREMENTS_FILE%"
) else (
    echo Requirements file not found!
    exit /b 1
)

pip install --editable .

:: Run the Click CLI application
%VENV_DIR%\Scripts\aeries-importer

:: Deactivate the virtual environment
deactivate

goto :EOF

:ensure_files
if not exist "%SOURCE_DIR%" (
    echo Save aeries-importer in your home directory.
    exit /b 1
)

for %%F in (%NEEDED_FILES%) do (
    if not exist "%SOURCE_DIR%\%%F" (
        echo File %%F is missing in %SOURCE_DIR%. Please ensure it is present.
        exit /b 1
    )
)

goto :EOF