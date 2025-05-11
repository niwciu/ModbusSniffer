#!/bin/bash

# Variables
APP_NAME="ModbusSniffer"
MAIN_PY="modbus_sniffer_GUI.py"
ICON="images/icon-4.png"
DESKTOP_FILE="$APP_NAME.desktop"
BUILD_DIR="build"
DIST_DIR="dist"
LOCAL_APP_DIR="$HOME/.local/share/applications"
VENV_DIR=".venv"

# Clean previous build
rm -rf "$BUILD_DIR" "$DIST_DIR" __pycache__ *.spec

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install PyInstaller in the virtual environment
pip install pyinstaller

# Create executable with PyInstaller
echo "Creating executable with PyInstaller..."
pyinstaller --onefile --name "$APP_NAME" "$MAIN_PY"

# Create application directory
mkdir -p "$BUILD_DIR"
cp "$DIST_DIR/$APP_NAME" "$BUILD_DIR/"
cp "$ICON" "$BUILD_DIR/"
cp "$DESKTOP_FILE" "$BUILD_DIR/"

# Update .desktop file paths
sed -i "s|Exec=.*|Exec=$(pwd)/$DIST_DIR/$APP_NAME|" "$BUILD_DIR/$DESKTOP_FILE"
sed -i "s|Icon=.*|Icon=$(pwd)/$BUILD_DIR/$(basename "$ICON")|" "$BUILD_DIR/$DESKTOP_FILE"
sed -i "s|Name=.*|Name=$APP_NAME|" "$BUILD_DIR/$DESKTOP_FILE"

# Make executable and .desktop file executable
chmod +x "$DIST_DIR/$APP_NAME"
chmod +x "$BUILD_DIR/$DESKTOP_FILE"

# Copy .desktop file to local applications directory
mkdir -p "$LOCAL_APP_DIR"
cp "$BUILD_DIR/$DESKTOP_FILE" "$LOCAL_APP_DIR/"

# Deactivate virtual environment
deactivate

# Output info
echo "Application built in $BUILD_DIR/"
echo "Shortcut added to menu at: $LOCAL_APP_DIR/$DESKTOP_FILE"
