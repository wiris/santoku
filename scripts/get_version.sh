#!/bin/bash

FILENAME=$1

grep version $FILENAME | sed -e 's|version=||g' -e 's|[\", \t]||g'
