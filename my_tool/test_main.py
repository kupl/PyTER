# -*- coding: utf-8 -*-
import os
import sys, getopt
import json
import traceback, sys

import load_benchmarks
import execute

from localizer import sbfl
from synthesizer import my_ast, validator, synthesize
import work

from pprint import pprint
import astpretty
import time
import signal

class Timeout(Exception) :
    pass

def handler(signum, frame) :
    print("Timeout!")
    raise Timeout("Timeout")

class Colors:
    RESET='\033[0m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'

def main(argv):
    BENCH_LIST = ['airflow', 'beets', 'click', 'core', 'luigi', 'numpy', 'pandas', 'rasa', 'requests', 'rich', 'salt', 'sanic', 'scikitlearn', 'tornado', 'transformers', 'Zappa']
    BUGSINPY_LIST = ['ansible', 'fastapi', 'keras', 'luigi', 'matplotlib', 'pandas', 'scrapy', 'spacy', 'tornado', 'tqdm', 'youtubedl']
    
    GITHUB_POS = [
        'airflow-5686',
        'airflow-6036',
        'airflow-14513',
        'core-1972',
        'core-8065',
        'core-20233',
        'core-32222',
        'core-40034',
        'pandas-15941',
        'pandas-17609',
        'pandas-19276',
        'pandas-20968',
        'pandas-21540',
        'pandas-21590',
        'pandas-22072',
        'pandas-22198',
        'pandas-22804',
        'pandas-25533',
        'pandas-25759',
        'pandas-26765',
        'pandas-32953',
        'pandas-33373',
        'pandas-36950',
        'pandas-38431',
        'rasa-8704',
        'requests-3179',
        'requests-3368',
        'requests-3390',
        'requests-4723',
        'salt-33908',
        'salt-38947',
        'salt-52624',
        'salt-53394',
        'salt-56094',
        'salt-56381',
        'sanic-1334',
        'sanic-2008-1',
        'sanic-2008-2',
        'scikitlearn-7064',
        'scikitlearn-8973',
        'tornado-1689',
        'Zappa-388'
    ]

    BUGSINPY_POS = [
        'keras-39',
        'luigi-4',
        'luigi-25',
        'luigi-26',
        'pandas-30',
        'pandas-48',
        'pandas-49',
        'pandas-106',
        'pandas-138',
        'pandas-142',
        'pandas-152',
        'scrapy-1',
        'scrapy-2',
        'scrapy-17',
        'scrapy-29',
        'scrapy-40',
        'tornado-9',
        'youtubedl-11'
    ]


    FILE_NAME = argv[0] # command line arguments의 첫번째는 파일명
    DIRECTORY = ""      # directory 초기화
    BENCHMARK = ""      # github이냐 bugsinpy냐
    PROJECT = ""        # project
    IDX = ""            # IDX
    ASSERT = ""

    try:
        # opts: getopt 옵션에 따라 파싱 ex) [('-i', 'myinstancce1')]
        # etc_args: getopt 옵션 이외에 입력된 일반 Argument
        # argv 첫번째(index:0)는 파일명, 두번째(index:1)부터 Arguments
        opts, etc_args = getopt.getopt(argv[1:], \
                                 "hd:b:p:i:c:n:", ["help","directory=", "project=", "idx=", "check=", "no="])

    except getopt.GetoptError: # 옵션지정이 올바르지 않은 경우
        print(FILE_NAME, '-d <directory>')
        sys.exit(2)

    for opt, arg in opts: # 옵션이 파싱된 경우
        if opt in ("-h", "--help"): # HELP 요청인 경우 사용법 출력
            print(FILE_NAME, '-d <directory>')
            sys.exit()

        elif opt in ("-d", "--directory"): # 인스턴명 입력인 경우
            DIRECTORY = arg

        elif opt in ("-b", "--bench"):
            BENCHMARK = arg

        elif opt in ("-p", "--project") :
            PROJECT = arg

        elif opt in ("-i", "--idx") :
            IDX = arg

        elif opt in ("-c", "--check") :
            CHECK = arg
        
        elif opt in ("-n", "--no") :
            ASSERT = arg

            

    if len(DIRECTORY) < 1: # 필수항목 값이 비어있다면
        print(FILE_NAME, "-d option is mandatory") # 필수임을 출력
        sys.exit(2)

    #if len(PROJECT) < 1: # 필수항목 값이 비어있다면
    #    print(FILE_NAME, "-p option is mandatory") # 필수임을 출력
    #    sys.exit(2)

    #if len(IDX) < 1: # 필수항목 값이 비어있다면
    #    print(FILE_NAME, "-i option is mandatory") # 필수임을 출력
    #    sys.exit(2)

    
    
    if PROJECT == "" :
        all_total = 0
        pass_total = 0
        if BENCHMARK == "" :
            for PROJECT in BENCH_LIST :
                pass_num, total = run(DIRECTORY, BENCHMARK, PROJECT, IDX, [] if CHECK == "" else GITHUB_POS, ASSERT)

                pass_total += pass_num
                all_total += total
        elif BENCHMARK == "bugsinpy" :
            for PROJECT in BUGSINPY_LIST :
                pass_num, total = run(DIRECTORY, BENCHMARK, PROJECT, IDX, [] if CHECK == "" else BUGSINPY_POS, ASSERT)

                pass_total += pass_num
                all_total += total

        print("Total : ", pass_total, "/", all_total)

    else :
        pass_num, total = run(DIRECTORY, BENCHMARK, PROJECT, IDX, [], ASSERT)

def run(DIRECTORY, BENCHMARK, PROJECT, IDX, LIST, ASSERT) :
    skip_list = [
        'airflow-5955', 'airflow-12094', 
        'click-1551', 
        'locust-972', 
        'luigi-2168', 'luigi-2323', 
        'numpy-8200',
        'pandas-17779', 'pandas-21987', 'pandas-22852', 'pandas-32185', 'pandas-33585', 'pandas-41010',
        'salt-40465', 
        'Zappa-396'
    ]

    pyfix_dir = "/home/wonseok/pyfix" + ("" if not BENCHMARK else ("/" + BENCHMARK))
    lb = load_benchmarks.LoadBenchmarks()
    pytest_json = lb.load_pytest_info(pyfix_dir, DIRECTORY, PROJECT, IDX, ASSERT)

    total_project = len(pytest_json.keys())

    pass_num = 0

    for project, pytest_info in pytest_json.items() :
        if ASSERT != '' and '-noassert' not in project :
            continue

        if project in skip_list :
            total_project -= 1
            continue

        if ASSERT :
            project = project[:project.rfind('-')]
            if LIST and project not in LIST :
                total_project -= 1
                continue
        else :
            if LIST and project not in LIST :
                total_project -= 1
                continue

        exec_prog = execute.Execute(DIRECTORY, project, pytest_info)
        validate = validator.Validator(exec_prog)

        pos_infos = list()
        pos_func_infos = dict()
        neg_infos = dict()
        neg_func_infos = dict()
        neg_msg = list()
        neg_additional = dict()

        #file_path = DIRECTORY + exec_paths[PROJECT][IDX] + "/pyfix"
        file_path = DIRECTORY + '/' + project + "/pyfix"

        nopos = '-nopos' if ASSERT != '' else ''

        pos_func_infos_path = file_path + "/func" + nopos
        pos_infos_path = file_path + "/pos" + nopos
        neg_func_infos_path = file_path + "/neg_func" + nopos
        neg_infos_path = file_path + "/neg" + nopos
        neg_msg_path = file_path + "/neg_msg" + nopos
        constant_dict_path = file_path + "/neg_additional" + nopos

        try :
            with open(pos_func_infos_path + ".json", 'r') as file :
                pos_func_infos = json.load(file)

            if os.path.isfile(pos_infos_path + ".json") :
                with open(pos_infos_path + ".json", 'r') as file :
                    pos_infos = json.load(file)


            with open(neg_func_infos_path + ".json", 'r') as file :
                neg_func_infos = json.load(file)

            if os.path.isfile(neg_infos_path + ".json") :
                with open(neg_infos_path + ".json", 'r') as file :
                    neg_infos = json.load(file)

            with open(neg_msg_path + ".json", 'r') as file :
                neg_msg = json.load(file)

            with open(constant_dict_path + ".json", 'r') as file :
                neg_additional = json.load(file)
        except Exception as e :
            total_project -= 1
            continue

        # load localize info
        neg_localize = dict()
        pos_localize = dict()

        neg_localize_path = file_path + "/neg_localize" + nopos +".json"
        pos_localize_path = file_path + "/pos_localize" + nopos+".json"

        with open(neg_localize_path, 'r') as file :
            neg_localize = json.load(file)

        with open(pos_localize_path, 'r') as file :
            pos_localize = json.load(file)

        # extract execute file
        usage_file = set()
        for key in neg_localize :
            filename = key.split()[0]
            usage_file.add(filename)

        projects = {}

        print(Colors.CYAN + '[[[' + project + ']]]' + Colors.RESET)

        try :
            ast = my_ast.MyAST(usage_file)
            asts, files_src = ast.get_asts(DIRECTORY, project)

            projects[project] = {IDX : asts}

            start = time.time()

            prev = os.getcwd()
            os.chdir(DIRECTORY + '/' + project)

            remain_test = set([])

            for neg_info in neg_infos :
                remain_test = remain_test.union(set(neg_info['idx']))

            works = work.Work(files_src, validate, asts, neg_localize, pos_localize,
                pos_infos, pos_func_infos, neg_infos, neg_func_infos, neg_msg, neg_additional, remain_test, 0)

            works.done_patch_only_once = False
            works.patch_file_dict = dict()
            
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(3600)
            
            works.work()

            os.chdir(prev)
        except (synthesize.PassAllTests, synthesize.PassAllTestsMultiple) :
            print(Colors.GREEN + "PASSED!" + Colors.RESET)
            pass_num += 1
        except Timeout as e :
            pass
        except Exception as e :
            print(Colors.YELLOW + "ERROR..." + Colors.RESET)
            traceback.print_tb(e.__traceback__)
            print(e)
        else :
            print(Colors.RED + "FAILED..." + Colors.RESET)
        finally :
            print("Time : ", round(time.time() - start, 2), "seconds")

        print("")

    print("PASSED : ", pass_num, "/", total_project)

    return pass_num, total_project

# module이 아닌 main으로 실행된 경우 실행된다
if __name__ == "__main__":
    main(sys.argv)