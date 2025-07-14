#!/bin/sh

# Function to log messages
log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting project validation and startup..."

# 1. Check for Python
if ! command -v python3 &> /dev/null
then
    log "Python3 is not installed. Please install Python3 to proceed."
    exit 1
fi
log "Python3 found."

# 2. Check for requirements.txt
if [ ! -f "requirements.txt" ]; then
    log "Error: requirements.txt not found. Cannot install dependencies."
    exit 1
fi
log "requirements.txt found."

# 3. Check for virtual environment and install dependencies
VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"
VENV_MARKER="$VENV_DIR/.venv_created"

if [ ! -d "$VENV_DIR" ]; then
    log "Virtual environment not found. Creating and installing dependencies..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        log "Error: Failed to create virtual environment."
        exit 1
    fi
    source "$VENV_DIR/bin/activate"
    pip install -r "$REQUIREMENTS_FILE"
    if [ $? -ne 0 ]; then
        log "Error: Failed to install dependencies from requirements.txt."
        exit 1
    fi
    touch "$VENV_MARKER"
    log "Virtual environment created and dependencies installed."
else
    log "Virtual environment found."
    source "$VENV_DIR/bin/activate"
    # Check if requirements.txt is newer than the venv marker, indicating new dependencies
    if [ "$REQUIREMENTS_FILE" -nt "$VENV_MARKER" ]; then
        log "requirements.txt has been updated. Reinstalling dependencies..."
        pip install -r "$REQUIREMENTS_FILE"
        if [ $? -ne 0 ]; then
            log "Error: Failed to update dependencies from requirements.txt."
            exit 1
        fi
        touch "$VENV_MARKER" # Update marker timestamp
        log "Dependencies updated."
    else
        log "Dependencies are up to date."
    fi
fi

# 4. Check for .env file
if [ ! -f ".env" ]; then
    log "Warning: .env file not found. Ensure environment variables are set or the application can run without them."
fi
log ".env file check complete."

# 5. Run the Flask application
log "Activating virtual environment and starting Flask application..."
# The 'app.py' file contains the main Flask application with the web interface.
# We need to ensure the FLASK_APP environment variable is set correctly.
export FLASK_APP=app.py
python -u -m flask run -p ${PORT:-5000} --debug
if [ $? -ne 0 ]; then
    log "Error: Flask application failed to start."
    exit 1
fi
