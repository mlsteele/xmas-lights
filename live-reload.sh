#!/usr/bin/env bash

cd `dirname $0`
find . -name \*.py | entr -r sh -c "python lights.py"
