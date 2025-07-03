#!/bin/bash

set -xe

python3 -m venv venv
source venv/bin/activate

which python3
python3 --version