#!/bin/bash
ENVLOG="/app/output/environment.log"

echo "Setting up environment - Don't worry, something is happening ;)..." | tee -a $ENVLOG
python3 -m venv .submission
source .submission/bin/activate
python3 -m pip install --upgrade pip >> $ENVLOG 2>&1
python3 -m pip install muniverse-emg >> $ENVLOG 2>&1

echo "Building scoring program..." | tee -a $ENVLOG
python3 -m pip install -e . >> $ENVLOG 2>&1

echo "Running scoring program..."
python3 main.py /app/input/res /app/input/ref /app/output isometric
