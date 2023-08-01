#!/bin/sh
rm -rf /workspaces/phaenonet-functions/.venv/lib
rm -rf /workspaces/phaenonet-functions/.pytest_cache
find . | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf
