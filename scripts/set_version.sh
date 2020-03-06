#!/bin/bash

FILENAME=$1
VERSION_NUMBER=$2

sed -i "s|version=\x22.*\x22,|version=\x22${VERSION_NUMBER}\x22,|g" $FILENAME