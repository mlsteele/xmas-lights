#!/usr/bin/env bash -eu

die() { echo "$@" 1>&2; exit 1; }

USERNAME=pi
HOSTNAME=xmas-pi

while test $# -gt 0
do
  case "$1" in
    -h|--hostname|--host)
      shift
      HOSTNAME="$1"
      ;;

    *)
      die "error: unknown argument $1"
      ;;
  esac
  shift
done

cd `dirname $0`
find . -name \*.py | entr -r rsync -aizF . ${USERNAME}@${HOSTNAME}:xmas-lights
