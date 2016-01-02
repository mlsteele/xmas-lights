#!/usr/bin/env bash

cd `dirname $0`
find . -name \*.py | entr -r rsync -aizF . pi@xmas-pi:xmas-lights
