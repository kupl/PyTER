import ast
import itertools
from copy import deepcopy

from .util import dict_product

class FindFuncFromType() :
    def __init__(self, funcname, args, funcs) :
        self.funcname = funcname
        self.args = args
        self.funcs = funcs

    def find_method(self) :
        for arg, typs in self.args.items() :
            if 'method' in typs :
                rfind_idx = arg.rfind('.')
                other = arg[:rfind_idx]
                func = arg[rfind_idx+1:]
                if self.funcname == func :
                    other_typs = self.args[other]

                    for other_typ in other_typs :
                        split_typs = other_typ.split('.')

                        for i, split_typ in enumerate(split_typs) :
                            if not split_typ.islower() :
                                class_text = ""
                                for j in range(i, len(split_typs)) :
                                    class_text += (split_typs[j] + '.') 

                                return class_text + self.funcname

    def find_class(self) :
        candidates = list()
        for arg, typs in self.args.items() :
            for typ in typs :
                if typ.islower() :
                    continue

                split_typs = typ.split('.')
                for i, split_typ in enumerate(split_typs) :
                    if not split_typ.islower() :
                        class_text = ""
                        for j in range(i, len(split_typs)) :
                            class_text += (split_typs[j] + '.') 

                candidates.append(class_text)

        return candidates

class ChangeArgument(ast.NodeVisitor) :
    
    def __init__(self, funcname, argument, file_node) :
        self.is_changed = False
        self.funcname = funcname
        self.argument = argument
        self.origin = file_node
        self.ast_list = []

    def visit_FunctionDef(self, node) :
        if node.name == self.funcname :
            arguments = node.args
            for i, arg in enumerate(arguments.args) :
                if arg.arg == self.argument :
                    defaults = arguments.defaults
                    arg.mark = True
                    if i <= len(arguments.defaults) :
                        defaults.insert(i, ast.Constant(value=None))
                    else :
                        defaults.append(ast.Constant(value=None))

                    self.ast_list.append(deepcopy(self.origin))

                    if i <= len(arguments.defaults) - 1 :
                        del defaults[i]
                    else :
                        del defaults[-1]

                    arg.mark = False

        for body in node.body :
            if isinstance(body, ast.Expr) :
                value = body.value

                if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) :
                    func = value.func

                    if isinstance(func.value, ast.Call) and func.value.func.id == 'super' and func.attr == '__init__' :
                        # super 키워드 찾아서 넣기
                        value.args.append(
                            ast.arg(
                                arg=self.argument,
                                mark=True
                            )
                        )

                        self.ast_list = [deepcopy(self.origin)] + self.ast_list

                        del value.args[-1]

        self.generic_visit(node)


    def get_ast(self, node) :
        self.visit(node)

        #print(ast.unparse(ast.fix_missing_locations(node)))

        return self.ast_list

class PositionalUsage(ast.NodeVisitor) :
    is_target_func = True
    keyword_list = list()

    def __init__(self, target_arg) :
        self.target_arg = target_arg

    def visit_Call(self, node) :
        if self.is_target_func :
            keywords = node.keywords

            for keyword in keywords :
                if keyword.arg == self.target_arg :
                    self.keyword_list.append(keyword)

        self.generic_visit(node)

    def visit_FunctionDef(self, node) :
        args = node.args.args

        prev = self.is_target_func

        self.is_target_func = True
        for arg in args :
            if arg.arg == self.target_arg :
                self.is_target_func = False

        self.generic_visit(node)

        self.is_target_func = prev

    def get_keyword_list(self, node) :
        self.is_target_func = True
        self.keyword_list = list()

        self.visit(node)

        return self.keyword_list

class AddCallArgument(ast.NodeVisitor) :
    def __init__(self, funcname, argument) :
        self.funcname = funcname
        self.argument = argument

    def visit_Call(self, node) :
        if (isinstance(node.func, ast.Name) and node.func.id == self.funcname) or (isinstance(node.func, ast.Attribute) and node.func.attr == self.funcname):
            node.keywords.append(
                ast.keyword(
                    arg=self.argument,
                    value=ast.Name(id=self.argument, ctx=ast.Load())
                )
            )

            node.mark = True

        self.generic_visit(node)

class DelCallArgument(ast.NodeVisitor) :
    def __init__(self, funcname, argument) :
        self.funcname = funcname
        self.argument = argument

    def visit_Call(self, node) :
        if (isinstance(node.func, ast.Name) and node.func.id == self.funcname) or (isinstance(node.func, ast.Attribute) and node.func.attr == self.funcname):
            target_idx = None 
            for i, keyword in enumerate(node.keywords) :
                if keyword.arg == self.argument :
                    target_idx = i
                    break

            if target_idx is not None :
                del node.keywords[target_idx]

                insert_idx = -1
                for j, arg in enumerate(node.args) :
                    if isinstance(arg, ast.Starred) :
                        insert_idx = j
                        break

                node.args.insert(insert_idx, ast.Name(id=self.argument, ctx=ast.Load()))

            node.mark = True

        self.generic_visit(node)

class GetKeywordDefault(ast.NodeVisitor) :
    keyword_constant = None

    def visit_keyword(self, node) :
        if isinstance(node.value, ast.Constant) :
            self.keyword_constant = node.value

    def get_keyword_constant(self, node) :
        self.keyword_constant = None
        self.visit(node)

        return self.keyword_constant

class AddKeywordArgument(ast.NodeVisitor) :
    is_first_func = False
    constant_args = None
    argument = None

    def __init__(self, patch_list) :
        self.patch_list = patch_list

    def visit_FunctionDef(self, node) :
        args = node.args.args
        args.append(ast.arg(arg=self.argument))

        defaults = node.args.defaults
        if self.is_first_func :
            self.constant_args = node.args
        else :
            defaults.append(
                ast.Name(id=self.argument, ctx=ast.Load())
            )

        self.generic_visit(node)

    def get_ast_list(self) :
        ast_list = list()
        
        constant_defaults_list = list()
        modify_node_set = set()

        for patch_name, patch in self.patch_list.items() :
            self.keyword_constant_list = list()
            self.constant_args = None
            

            if patch_name == 'keyword' :
                for func_infos in patch :
                    for func_info in func_infos :
                        modify_node_set.add((func_info['origin'], func_info['filename']))
                        for keyword in func_info['keywords'] :
                            keyword_constant = GetKeywordDefault().get_keyword_constant(keyword)

                            if keyword_constant :
                                self.keyword_constant_list.append(keyword_constant)

                    # sharex = sharex 로 바꿔주는 거
                    for i, func_info in enumerate(func_infos) :
                        self.argument = func_info['argument']
                        self.is_first_func = True if i == 0 else False
                        self.visit(func_info['node'])
                        for keyword in func_info['keywords'] :
                            keyword.value = ast.Name(id=self.argument, ctx=ast.Load(), mark=True)

                    # 처음 부를때 기본 값 넣어주는거
                    if self.constant_args :
                        constant_defaults_list.append((self.constant_args, self.keyword_constant_list))
            
            elif patch_name == 'position' :
                for (origin, filename, stmt, funcname, argument) in patch :
                    modify_node_set.add((origin, filename))
                    add_call = AddCallArgument(funcname, argument)
                    add_call.visit(stmt)

            elif patch_name == 'multiple' :
                for (origin, filename, stmt, funcname, argument) in patch :
                    modify_node_set.add((origin, filename))
                    del_call = DelCallArgument(funcname, argument)
                    del_call.visit(stmt)


        def list_of_list_product(lists):
            new_list = list()
            arg_list = list()
            constant_list = list()
            for arg, constant in constant_defaults_list :
                arg_list.append(arg)
                constant_list.append(constant)

            for x in itertools.product(*constant_list) :
                new_list.append(list(zip(arg_list, x)))

            return new_list
            #return (dict(zip(dicts, x)) for x in itertools.product(*dicts.values()))

        get_patch_candidates = list_of_list_product(constant_defaults_list)
        

        for candidate in get_patch_candidates :
            if not candidate :
                copy_list = list()
                for origin, filename in modify_node_set :
                    copy_list.append((deepcopy(origin), filename))

                ast_list.append(copy_list)

                return ast_list

            for keywords, constant in candidate :
                constant.mark = True
                keywords.defaults.append(constant)
            
            copy_list = list()
            for origin, filename in modify_node_set :
                copy_list.append((deepcopy(origin), filename))

            ast_list.append(copy_list)

            for keywords, constant in candidate :
                keywords.defaults.pop()

        return ast_list

