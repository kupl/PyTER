#!/bin/bash
pyenv install -s 3.9.1
pyenv global 3.9.1
pip install astpretty
pip install iteration-utilities

for project_folder in $(find /pyter/bugsinpy_info -mindepth 1 -maxdepth 1 -print)
do
    project="$( cut -d '/' -f 4 <<< "$project_folder" )";
    number="$( cut -d '-' -f 2 <<< "$project_folder" )";

    for testfile in $(find $project_folder -name '*.py' -o -name '*.cfg' -o -name '*.ini')
    do
        testfile="$(realpath $testfile)"
        direc="$( cut -d '/' -f 5- <<< "$testfile" )";
        yes | cp $testfile /pyter/BugsInPy/benchmark/$project/$direc
    done
done