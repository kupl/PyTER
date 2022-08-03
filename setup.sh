#! /bin/bash

#py_version=$(jq -r '.py_version' bug_info.json)
#repo=$(jq -r '.repo' bug_info.json)
#git=$(jq -r '.git' bug_info.json)
#fixed_pr_id=$(jq -r '.fixed_pr_id' bug_info.json)

#git clone ${git} 
#git clone https://github.com/kupl/pyter_tool.git
pyenv install 3.9.1
pyenv global 3.9.1
pip install astpretty
pip install iteration-utilities

mkdir benchmark
array=()

for project_folder in $(find /pyter/benchmark_info -mindepth 2 -maxdepth 2 -print)
do
    project="$( cut -d '/' -f 4 <<< "$project_folder" )";
    number="$( cut -d '-' -f 2 <<< "$project_folder" )";
    sub="$( cut -d '-' -f 3 <<< "$project_folder" )";

    if [[ ${sub} != '' ]] && [[ ${sub} != 'learn' ]]; then
        number=${number}-${sub}
    fi

    if [[ ${project} == 'scikit-learn' ]]; then
        number="$( cut -d '-' -f 4 <<< "$project_folder" )";
    fi

    cd $project_folder

    py_version=$(jq -r '.py_version' bug_info.json)
    repo=$(jq -r '.repo' bug_info.json)
    git=$(jq -r '.git' bug_info.json)
    fixed_pr_id=$(jq -r '.fixed_pr_id' bug_info.json)
    declare -a "files=($(jq -r '.code_files | .[] | @sh' bug_info.json))"

    cd /pyter/benchmark

    if [ ! -d "/pyter/benchmark/${repo}" ]; then
        git clone ${git} 
        array+=(${repo})
    fi

    if [[ ${repo} == 'scikit-learn' ]]; then
        cp -r ${repo} scikitlearn-${number}
        repo='scikitlearn'
    else
        cp -r ${repo} ${repo}-${number}
    fi
    cp ${project_folder}/dependency_setup.sh /pyter/benchmark/${repo}-${number}/dependency_setup.sh
    cp ${project_folder}/requirements.txt /pyter/benchmark/${repo}-${number}/pyter_requirements.txt

    
    cd ${repo}-${number}

    pyenv install -s ${py_version}
    pyenv virtualenv ${py_version} ${repo}-${number}
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
    source ~/.bashrc

    pyenv activate ${repo}-${number}
    pyenv local ${repo}-${number}

    git checkout ${fixed_pr_id}

    for file in "${files[@]}"; do
        git checkout HEAD~1 ${file}
    done

    for testfile in $(find $project_folder -name '*.py' -o -name '*.cfg')
    do
        testfile="$(realpath $testfile)"
        direc="$( cut -d '/' -f 6- <<< "$testfile" )";
        yes | cp $testfile /pyter/benchmark/${repo}-${number}/$direc
    done

    #../dependency_setup.sh

    pyenv deactivate
done

for i in "${array[@]}"
do
    rm -rf /pyter/benchmark/$i
done