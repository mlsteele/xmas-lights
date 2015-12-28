#!/usr/bin/env bash

cd `dirname $0`
find . -name \*.py | entr -r python lights.py "${@}"
