#! /usr/bin/env bash
set -ex

DIST_DIR=dist


rm -rf distenv
virtualenv -p python3 distenv
source ./distenv/bin/activate
pip install .
pip install .[develop]

rm -rf ${DIST_DIR}
python3 setup.py sdist

pip install twine
read -p "Do you want to push? (y/N)" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  twine upload ${DIST_DIR}/*.tar.gz
fi
REPLY= # unset REPLY after using it
