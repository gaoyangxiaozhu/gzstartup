#!/bin/bash

set -xe

## Build
script_dir="$(cd "$(dirname "$0")"; pwd)"
root_dir="$(dirname "$script_dir")"

rm -rf "$root_dir"/dist "$root_dir"/build "$root_dir"/*.egg-info

source "${script_dir}"/active_env.sh

pip3 uninstall -y gzpearlagent-backend

mkdir -p "${root_dir}"/dist
dist_dir=${root_dir}/dist
echo "root dir : ${root_dir}"
rm -f "$dist_dir"/*
python3 -m pip install setuptools==65.5.0
python3 -m pip install wheel==0.45.1
python3 -m pip install parameterized==0.9.0

# install gzpearlagent-backend
cd "${root_dir}"
python3 -m pip install -r requirements.txt
python3 setup.py sdist bdist_wheel
cd dist

# shellcheck disable=SC2035
pip3 install *.whl

cd ..
rm -rf dist
rm -rf build
# shellcheck disable=SC2035
rm -rf *.egg-info

echo "Build finished. whl in $root_dir/dist"
