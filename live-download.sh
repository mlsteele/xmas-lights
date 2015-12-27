#!/usr/bin/env bash

cd `dirname $0`
find . -name \*.py | entr -r rsync -aiz --exclude .git . pi@xmas-pi:xmas-lights
