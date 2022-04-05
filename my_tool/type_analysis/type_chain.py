'''
실행을 거슬러 올라가면서
타입 체크 하기
'''

from .util import split_input_output, abstract_type
import ast

class FindTarget(Exception) :
    pass

class FindStmt(ast.NodeVisitor) :
    

    def __init__(self, target) :
        self.find_target = False
        self.target_stmt = None
        self.target = target

    def generic_visit(self, node) :
        if self.target_stmt is not None :
            return

        super().generic_visit(node)

        if isinstance(node, ast.expr) and node is self.target :
            self.find_target = True

        if isinstance(node, ast.stmt) and self.find_target and self.target_stmt is None:
            self.target_stmt = node

    def find_stmt(self, node) :
        self.visit(node)

        return self.target_stmt

class TypeChain(ast.NodeVisitor) :

    def __init__(self, localize, filename, target, node, target_arg, neg_funcs, pos_funcs) :
        self.localize = localize
        self.filename = filename

        find = FindStmt(target)
        self.target = find.find_stmt(node)
        self.target_arg = target_arg
        self.neg_funcs = neg_funcs
        self.pos_funcs = pos_funcs

        self.func_start = False

        self.stmt_list = list()

    def generic_visit(self, node) :
        if self.func_start :
            return

        if isinstance(node, ast.stmt) :
            self.stmt_list.append(node)

        if node is self.target :
            self.func_start = True
            return

        super().generic_visit(node)

    def get_type_chain(self, node) :
        self.visit(node)

        find = FindTypeChain(self.localize, self.filename, self.stmt_list, self.target_arg, self.neg_funcs, self.pos_funcs)
        candidate = find.do()
        return candidate

class FindTypeChain(ast.NodeVisitor) :
    def __init__(self, localize, filename, stmt_list, target_arg, neg_funcs, pos_funcs) :
        self.localize = localize
        self.filename = filename

        stmt_list.reverse()
        self.stmt_list = stmt_list
        self.target_arg = target_arg
        self.neg_funcs = neg_funcs
        self.pos_funcs = pos_funcs

        self.in_call = False
        self.call_name = None
        self.localize_line = list()

        self.candidate_var = None

    def extract_call_info(self, lineno) :
        find_flag = False
        for l in self.localize :
            split = l.split()

            if find_flag :
                if split[1] == self.call_name :
                    return split[0]

            if split[0] == self.filename and int(split[2]) == lineno:
                find_flag = True

        return None

    def func_return_difference(self, call_filename, call_funcname) :
        #print(call_filename, call_funcname)
        neg_type = dict()
        pos_type = dict()

        neg_comments = list()
        pos_comments = list()

        for neg_func in self.neg_funcs :
            if neg_func['path'] in call_filename and call_funcname in neg_func['func_name'] :
                neg_comments = neg_func['type_comments']

        for pos_func in self.pos_funcs :
            if pos_func['path'] in call_filename and call_funcname in pos_func['func_name'] :
                pos_comments = pos_func['type_comments']

        for comment in neg_comments :
            _, output = split_input_output(comment['type'])
            output = abstract_type(output)

            neg_type[output] = neg_type.get(output, 0) + comment['samples']

        for comment in pos_comments :
            _, output = split_input_output(comment['type'])
            output = abstract_type(output)

            pos_type[output] = pos_type.get(output, 0) + comment['samples']

        neg_type = list(map(lambda x : x[0], neg_type.items()))
        sorted(pos_type, key=lambda x : x[1], reverse=True)

        return neg_type, pos_type


    def visit_Name(self, node) :
        if self.in_call == True and self.call_name is None:
            self.call_name = node.id

    def visit_Attribute(self, node) :
        if self.in_call == True and self.call_name is None:
            self.call_name = node.attr

    def visit_For(self, node) :
        if self.target_arg is None :
            return 
        if ast.unparse(node.target) == ast.unparse(self.target_arg) :
            if isinstance(node.iter, (ast.Name, ast.Attribute)) :
                self.target_arg = node.iter

    def visit_Assign(self, node) :
        if self.target_arg is None :
            return 
        for target in node.targets :
            if ast.unparse(target) == ast.unparse(self.target_arg) :
                value = node.value
                if isinstance(value, ast.Call) :
                    self.in_call = True
                    self.call_name = None
                    self.visit(value.func)
                    self.in_call = False

                    if self.call_name is None :
                        print("Type Chain Error!!")
                        raise Exception

                    call_filename = self.extract_call_info(value.lineno)
                    if call_filename is None : # 함수가 내장함수여서 추적 못함
                        return

                    neg_type, pos_type = self.func_return_difference(call_filename, self.call_name)

                    check_result = set(neg_type).intersection(pos_type.keys())
                    if check_result : # neg와 pos에 겹치는 타입이 있으면 안돼!
                        return

                    self.candidate_var = (ast.unparse(self.target_arg), (neg_type, pos_type))

                    raise FindTarget

                elif isinstance(value, (ast.Name, ast.Attribute)) :
                    self.target_arg = value

                elif isinstance(value, ast.Subscript) :
                    self.target_arg = value.value

    def do(self) :
        for i, stmt in enumerate(self.stmt_list) :
            try :
                self.visit(stmt)
            except FindTarget :
                return (self.stmt_list[i-1], self.candidate_var)