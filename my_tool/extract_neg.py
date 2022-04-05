# -*- coding: utf-8 -*-

import pytest
import json
from pyannotate_runtime import collect_types
import argparse 
import os
import sys
import subprocess
import shutil

def running() :
    with open('./pyfix/pytest.json', 'r') as readfile :
        pytest_option = json.load(readfile)

    pytest.main(pytest_option['neg'])



def preprocessing(args) :
    project = os.getcwd()[os.getcwd().rfind('/')+1:]
    project_name = project[:project.find('-')]

    if project_name == 'scikit' :
        project_name = 'scikit-learn'

    directory = args.bench
    dir_name = directory + '/pytest-'+project_name+'.json'

    

    with open(directory + '/pytest-'+project_name+'.json', 'r') as readfile :
        pytest_option = json.load(readfile)

    nopos = ""
    if args.nopos :
        test_option = pytest_option[project+'-noassert']['neg']
        nopos = '-nopos'
    else :
        test_option = pytest_option[project]['neg']

    del args

    test_methods = list()
    for test_method in test_option :
        place = test_method.rfind(':')
        test_method = test_method[place+1:]
        test_methods.append(test_method)

    if project_name == 'airflow' :
        airflow_dir = os.path.expanduser('~') + '/airflow'

        if os.path.exists(airflow_dir) :
            shutil.rmtree(airflow_dir)

        if project == 'airflow-5686' or project == 'airflow-6036' or project == 'airflow-14513' or project == 'airflow-14686':
            subprocess.run(["airflow", "db", "init"])
        else :
            subprocess.run(["airflow", "initdb"])

    if project_name == 'salt' :
        if not os.path.isdir("/tmp/salt-tests-tmpdir") :
            os.mkdir("/tmp/salt-tests-tmpdir")

        if project == 'salt-38947' :
            sys.path.append('./tests')

    collect_types.init_types_collection(test_option=test_option, test_func=test_methods)
    with collect_types.collect():
        #print(test_option)
        retcode = pytest.main(test_option)


    err, msg, result, localize, additional = collect_types.my_stats()
    
    if not os.path.isdir('pyfix') :
        os.mkdir('pyfix')

    with open("./pyfix/neg"+nopos+".json", 'w') as outfile:
        json.dump(err, outfile, indent=4)

    with open("./pyfix/neg_msg"+nopos+".json", 'w') as outfile:
        json.dump(msg, outfile, indent=4)

    with open("./pyfix/neg_func"+nopos+".json", 'w') as outfile:
        json.dump(result, outfile, indent=4)

    with open("./pyfix/neg_localize"+nopos+".json", 'w') as outfile:
        json.dump(localize, outfile, indent=4)

    with open("./pyfix/neg_additional"+nopos+".json", 'w') as outfile:
        json.dump(additional, outfile, indent=4)

if __name__ == "__main__" :
    parser = argparse.ArgumentParser()
    # argument는 원하는 만큼 추가한다.
    parser.add_argument('--bench', type=str, help='bench name')
    parser.add_argument('--nopos', type=str, help='no pos')
    args = parser.parse_args()

    preprocessing(args)