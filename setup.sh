#! /bin/bash

py_version=$(jq -r '.py_version' bug_info.json)
repo=$(jq -r '.repo' bug_info.json)
git=$(jq -r '.git' bug_info.json)
fixed_pr_id=$(jq -r '.fixed_pr_id' bug_info.json)

git clone ${git} 
git clone https://github.com/kupl/pyter_tool.git

if cd ${repo}; then
    pyenv install -s ${py_version}
    pyenv virtualenv ${py_version} ${repo}
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
    source ~/.bashrc

    pyenv activate ${repo}
    pyenv local ${repo}

    git checkout ${fixed_pr_id}
    declare -a "files=($(jq -r '.code_files | .[] | @sh' ../bug_info.json))"

    for file in "${files[@]}"; do
        git checkout HEAD~1 ${file}
    done

    ../dependency_setup.sh

    pyenv deactivate

    cd ..

    mv ${repo} ${repo}-${fixed_pr_id}
    
fi