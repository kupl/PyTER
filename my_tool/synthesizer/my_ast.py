# -*- coding: utf-8 -*-

import ast
import glob
import os

class MyAST() :
    def __init__(self, usage_file) :
        self.usage_file = usage_file

    def files_to_asts(self, dir, project) :
        asts = {}
        files_src = {}

        for filename in glob.iglob(dir + '/' + project + "/**/*.py", recursive=True) :
            if not filename in self.usage_file : # 안쓰인 파일은 스킵
                continue

            if "tests" in filename : # test 포함한건 제외
                continue

            with open(filename, 'r', encoding='utf-8-sig') as f :
                #print(filename)
                src = f.read()
                files_src[filename] = src
                tmp = ast.parse(src)
                asts[filename] = tmp
 
        return asts, files_src

    # project/test_number 의 파일들을 읽어오는 것
    def get_asts(self, dir, project) :
        asts, files_src = self.files_to_asts(dir, project)

        return asts, files_src

    