#!/bin/bash
PIPLOG="/app/output/environment.log"

echo "Setting up environment..." | tee -a $PIPLOG
python3 -m venv .submission
source .submission/bin/activate
python3 -m pip install --upgrade pip --quiet --quiet --log $PIPLOG
python3 -m pip install --extra-index-url https://test.pypi.org/simple/ muniverse==0.0.1.dev2 --quiet --quiet --log $PIPLOG

echo "Building scoring program..." | tee -a $PIPLOG
python3 -m pip install -e . --quiet --quiet --log $PIPLOG

echo "Running scoring program..."
python3 main.py /app/input/res /app/input/ref/ground-truth-spikes /app/output
