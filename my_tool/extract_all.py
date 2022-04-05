# -*- coding: utf-8 -*-

import pytest
import json
from pyannotate_runtime import collect_types
import os
import sys
import argparse

def main(args) :
    project = os.getcwd()[os.getcwd().rfind('/')+1:]
    project_name = project[:project.find('-')]

    with open('/home/wonseok/pyfix/pytest-'+project_name+'.json', 'r') as readfile :
        pytest_option = json.load(readfile)

    test_option = pytest_option[project]['all']

    if project_name == 'salt' :
        if not os.path.isdir("/tmp/salt-tests-tmpdir") :
            os.mkdir("/tmp/salt-tests-tmpdir")

        if project == 'salt-38947' :
            sys.path.append('./tests')

    collect_types.init_types_collection(only_func=True)
    with collect_types.collect():
        # timeout 5 seconds
        #pytest.set_trace(collect_types._trace_dispatch)
        retcode = pytest.main(test_option)


    _, result = collect_types.my_stats()

    with open("./pyfix/all.json", 'w') as outfile:
        json.dump(result, outfile, indent=4)

if __name__ == "__main__" :
    main()