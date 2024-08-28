#!/bin/bash

# Define variables
VENV_DIR=".venv"                  # Directory for the virtual environment
REQUIREMENTS_FILE="requirements.txt" # Path to the requirements file
SOURCE_DIR="$HOME/aeries-importer/"         # Directory where source code resides
NEEDED_FILES=("credentials.json") # List of files that need to be present

# Function to ensure needed files are in the source directory
ensure_files() {
    if [ ! -d "$SOURCE_DIR" ]; then
        echo "Save aeries-importer in your home directory."
        exit 1
    fi

    for file in "${NEEDED_FILES[@]}"; do
        if [ ! -f "$SOURCE_DIR/$file" ]; then
            echo "File $file is missing in $SOURCE_DIR. Please ensure it is present."
            exit 1
        fi
    done
}

# Ensure necessary files are in the source directory
ensure_files

cd "$SOURCE_DIR"

# Check if the virtual environment directory exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"  # Create virtual environment
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Install the required packages
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing required packages..."
    pip install -r "$REQUIREMENTS_FILE"  # Install packages from requirements.txt
else
    echo "Requirements file not found!"
    exit 1
fi

pip install --editable .

# Aeries Chrome session setup; default profile (created with webdriver) should point to existing profile
ln -s $HOME/Library/Application\ Support/Google/Chrome/Profile\ 1 $HOME/Library/Application\ Support/Google/Chrome/Profile\ 1/Default

# Run the Click CLI application
$VENV_DIR/bin/aeries-importer

# Deactivate the virtual environment
deactivate