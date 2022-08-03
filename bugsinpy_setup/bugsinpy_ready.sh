#! /bin/bash

for project_folder in $(find /pyter/BugsInPy/benchmark -mindepth 1 -maxdepth 1 -print)
do
    cd $project_folder

    if [[ $project_folder == *'fastapi'* ]]; then
        pip install pydantic
        pip install starlette==0.12.9
        if [[ $project_folder == *'fastapi-7'* ]]; then
            pip install requests
        fi
    elif [[ $project_folder == *'luigi'* ]]; then
        pip install mock
    elif [[ $project_folder == *'scrapy'* ]]; then
        if [[ $project_folder == *'scrapy-1'* ]]; then
            pip install pytest-twisted
    
        elif [[ $project_folder == *'scrapy-20'* ]]; then
            pip install testfixtures
            pip install twisted==20.3.0
        
        elif [[ $project_folder == *'scrapy-40'* ]]; then
            pip install parameterized
        fi
    fi

    pip install -e /pyter/pyter_tool/pyannotate/.
    pip install pytest-timeouts
done
