#! /bin/bash

for project_folder in $(find /pyter/benchmark -mindepth 1 -maxdepth 1 -print)
do
    cd $project_folder

    chmod +x dependency_setup.sh
    ./dependency_setup.sh

    pip install -e /pyter/pyter_tool/pyannotate/.
    pip install pytest-timeouts
done