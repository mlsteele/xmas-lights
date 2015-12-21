#!/usr/bin/env bash

FILENAME=miles.py
echo $FILENAME | entr -r sh -c "scp $FILENAME xmas-pi:xmas-lights/$FILENAME"
