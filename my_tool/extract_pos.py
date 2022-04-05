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

    pytest.main(pytest_option['pos'])


def preprocessing(args) :
    nopos=""
    if args.nopos :
        nopos = "-nopos"
    project = os.getcwd()[os.getcwd().rfind('/')+1:]
    project_name = project[:project.find('-')]

    if project_name == 'scikit' :
        project_name = 'scikit-learn'

    directory = args.bench

    with open('./pyfix/neg'+nopos+'.json', 'r') as readfile :
        neg = json.load(readfile)

    with open(directory + '/pytest-'+project_name+'.json', 'r') as readfile :
        pytest_option = json.load(readfile)
    
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

    collect_types.init_types_collection(negative_info=neg)
    if args.nopos :   
        execute_name = project+'-noassert'
    else :
        execute_name = project

    del args

    with collect_types.collect():
        # timeout 5 seconds
        retcode = pytest.main(pytest_option[execute_name]['pos'])


    args, result, localize = collect_types.pos_stats()
    
    with open("./pyfix/func"+nopos+".json", 'w') as outfile :
        json.dump(result, outfile, indent=4)

    with open("./pyfix/pos"+nopos+".json", 'w') as outfile:
        json.dump(args, outfile, indent=4)

    with open("./pyfix/pos_localize"+nopos+".json", 'w') as outfile:
        json.dump(localize, outfile, indent=4)

if __name__ == "__main__" :
    pyfix_parser = argparse.ArgumentParser()
    # argument는 원하는 만큼 추가한다.
    pyfix_parser.add_argument('--bench', type=str, help='bench name')
    pyfix_parser.add_argument('--nopos', type=str, help='no pos')
    args = pyfix_parser.parse_args()
    

    preprocessing(args)