#!/bin/bash
set -e -x

cd /rainbow/core
pip install -r requirements.txt
pip install -r requirements-priv.txt
python setup.py develop
$@
