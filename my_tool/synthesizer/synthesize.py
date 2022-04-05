from types import MethodType
import synthesizer

from . import my_ast
from . import local_info
#from . import make_hole, component
import ast
import astpretty
import copy

from . import extract_info
#from . import component
from .var_component import VarComponent

#from .ast_synthesize import AstSynthesize
from .template_synthesizer import TemplateSynthesizer


#import codegen

class PassAllTests(Exception) :
    def __init__(self, filename, node, test, targets) :
        self.filename = filename
        self.node = node
        self.test = test
        self.targets = targets

    def print_info(self) :
        print("Filename : ", self.filename)

        if self.targets :
            print("[[[ Patch Node ]]]")
            node = ast.fix_missing_locations(self.targets[0])
            print(ast.unparse(node))

class PassAllTestsMultiple(Exception) :
    def __init__(self, node_list, test, targets) :
        self.node_list = node_list
        self.test = test
        self.targets = targets

    def print_info(self) :
        for _, filename in self.node_list :
            print("Filename : ", filename)

        if self.targets :
            print("[[[ Patch Node ]]]")
            node = ast.fix_missing_locations(self.targets[0])
            print(ast.unparse(node))


class Synthesize() :
    def __init__(self, files_src, validate, files, func_type) :
        self.files_src = files_src
        self.validate = validate
        self.file_info = self.extract_files_info(files)
        self.func_type = func_type

        self.components = None

        self.origin_node = None # 전체 노드
        self.filename = None

    # file마다 local 정보 추려내기
    def extract_files_info (self, files) :
        info = local_info.LocalInfo()

        file_info = {}

        for file, node in files.items() :
            funcs_info = info.funcs_info(node)
            file_info[file] = funcs_info
        
        self.file_info = file_info
        return file_info

    def find_template(self) :
        for node in ast.walk(self.origin_node) :
            if hasattr(node, "mark") and node.mark :
                return node

    def synthesize(self, node, filename, funcname, classname, neg_args, pos_func_infos, components, context_aware, context_score, neg_additional, test, total_test_num, final=False, func_patch=False) :
        '''
        타입 체킹을 할 var를 고르고
        synthesize를 하자
        '''
        self.filename = filename
        self.origin_node = node
        self.components = components
        self.context_aware = context_aware
        template = self.find_template()


        '''
        template부터 합성해보자
        '''
        temp_synthesize = TemplateSynthesizer(self.validate, filename, funcname, classname, neg_args, pos_func_infos, context_aware, context_score, neg_additional, test, total_test_num, final, func_patch)
        temp_synthesize.template_synthesize(node)

        return

        