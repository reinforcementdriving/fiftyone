#!/bin/bash
# Installs dependencies needed to build the documentation.
#
# Usage:
#   docs/setup.bash
#
# Copyright 2017-2020, Voxel51, Inc.
# voxel51.com
#

set -e
cd "$(dirname "$0")"

command_exists() {
    type "$1" >/dev/null 2>&1
    return $?
}

echo "***** Installing pandoc *****"
if command_exists pandoc; then
    echo "Already installed: $(which pandoc)"
else
    if command_exists brew; then
        brew install pandoc
    else
        for cmd in apt apt-get dnf yum; do
            if command_exists "${cmd}"; then
                (set -x; sudo "${cmd}" install pandoc)
                break
            fi
        done
    fi
fi

if ! command_exists pandoc; then
    echo "Failed to install pandoc"
    exit 1
fi

echo "***** Installing documentation requirements *****"
pip install -r ../requirements/docs.txt
