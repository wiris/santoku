#!/bin/bash
grep version setup.py | sed -e 's|version=||g' -e 's|[\", \t]||g'
