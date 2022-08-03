#! /bin/bash

for project_folder in $(find /pyter/bugsinpy_info -mindepth 1 -maxdepth 1 -print)
do
    project_number="$( cut -d '/' -f 4 <<< "$project_folder" )";

    project="$( cut -d '-' -f 1 <<< "$project_number" )";
    number="$( cut -d '-' -f 2 <<< "$project_number" )";

    if [[ ${project} == 'youtubedl' ]]; then
        project='youtube-dl'
    fi

    bug_info=/pyter/BugsInPy/projects/${project}/bugs/${number}/bug.info
    echo $bug_info
    information=$(<${bug_info})

    information="$( cut -d '"' -f 2 <<< "$information" )";
    py_version=${information:0:5}

    if [[ -d "/pyter/BugsInPy/benchmark/$project-$number" ]]; then
        echo $project-$number Skip
        continue
    fi

    mkdir /pyter/BugsInPy/benchmark
    bugsinpy-checkout -p $project -v 0 -i $number -w /pyter/BugsInPy/benchmark
    cd /pyter/BugsInPy/benchmark
    if [[ $project == "youtube-dl" ]]; then
        project="youtubedl"
        mv youtube-dl $project-$number
    else 
        mv $project $project-$number
    fi
    cd $project-$number

    pyenv install $py_version -s
    pyenv virtualenv $py_version $project-$number
    pyenv local $project-$number

    bugsinpy-compile
done


