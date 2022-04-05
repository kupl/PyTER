'''
call chain...
'''
import ast
from copy import deepcopy

from .util import FindTargetFunc, abstract_input_types
from synthesizer.extract_info import find_error_stmt

from template.util import ChangeNode, Template

class StmtChain(ast.NodeVisitor) :
    def __init__(self, lineno_list, target, node) :
        self.lineno_list = lineno_list

        find = FindTargetFunc(target)
        self.target_func = find.get_func(node)
        self.target = target

        self.func_start = False
        self.stmt_list = list()

    def generic_visit(self, node) :
        if self.func_start :
            return

        if isinstance(node, ast.stmt) and node.lineno in self.lineno_list :
            self.stmt_list.append(node)

        if node is self.target :
            self.func_start = True
            return

        super().generic_visit(node)

    def get_stmt_chain(self) :
        if self.target_func is None : 
            return self.stmt_list
            
        self.visit(self.target_func)

        self.stmt_list = [self.target_func] + self.stmt_list

        return self.stmt_list

class CallChain(ast.NodeVisitor) :
    def __init__(self, localize, files, neg_infos, pos_info, pos_func_infos, test) :
        self.localize = localize
        self.files = files
        self.neg_infos = neg_infos
        self.pos_info = pos_info
        self.pos_func_infos = pos_func_infos
        self.test = test
        
        self.lookup_var_set = set([])
        self.argument_dict = dict([])

        self.candidate_arg = set([])
        self.candidate_keyword = set([])
        self.candidate_call = set([])

    def call_analysis(self, node) :
        for expr in ast.walk(node) :
            if isinstance(expr, ast.Call) :
                args = expr.args
                keywords = expr.keywords

                for i, arg in enumerate(args) :
                    if isinstance(arg, ast.Constant) and i in self.argument_dict :
                        self.candidate_arg.add((arg, self.argument_dict[i]))
                    if isinstance(arg, ast.Call) and i in self.argument_dict :
                        self.candidate_call.add((i, expr, arg, self.argument_dict[i]))

                for keyword in keywords :
                    if hasattr(keyword, 'arg') and keyword.arg in list(self.argument_dict.values()) :
                        if isinstance(keyword.value, ast.Constant) :
                            self.candidate_keyword.add(keyword)

                break


    def get_all_name(self, node) :
        var_set = set([])
        for expr in ast.walk(node) :
            if isinstance(expr, ast.Name) :
                var_set.add(ast.unparse(expr))

        return var_set

    def visit_FunctionDef(self, node) :
        args = node.args
        self.argument_dict = dict()

        index = 0
        for arg in args.args :
            if arg.arg == 'self' :
                continue

            if arg.arg in self.lookup_var_set :
                self.argument_dict[index] = arg.arg
            index += 1

            

    def visit_Assign(self, node) :
        change = False
        for target in node.targets :
            target_var_set = self.get_all_name(target)

            if target_var_set.issubset(self.lookup_var_set) :
                self.lookup_var_set = self.lookup_var_set - target_var_set
                change = True

        if change :
            value_var_set = self.get_all_name(node.value)
            self.lookup_var_set.update(value_var_set)

    def generic_visit(self, node) :
        # 볼 필요가 없다
        return

    def get_lineno_list(self, neg_funcname, neg_filename, neg_lineno) :
        localize = list(reversed(self.localize))
        is_target = False

        lineno_list = list()

        for loc in localize :
            filename, funcname, lineno = loc.split()

            lineno = int(lineno)

            if lineno_list and filename == neg_filename and funcname == neg_funcname :
                if lineno_list[-1] <= lineno :
                    continue

            if filename == neg_filename and funcname == neg_funcname and lineno == neg_lineno :
                is_target = True

            if filename == neg_filename and funcname == neg_funcname and is_target :
                lineno_list.append(lineno)

        return lineno_list 

    def get_change_node_list(self, name, constant) :
        # Todo 여기를 강화 시킬 필요가 있음
        node_list = []

        node_list.append(
            ast.Name(id=name, ctx=ast.Load(), mark=True)
        )

        constant_type = type(constant.value).__name__

        if constant_type == 'int' :
            node_list.extend(
                [
                    ast.Constant(value=0, ctx=ast.Load(), mark=True)
                ]
            )
        if constant_type == 'float' :
            node_list.extend(
                [
                    ast.Constant(value=0.0, ctx=ast.Load(), mark=True)
                ]
            )
        if constant_type == 'bool' :
            node_list.extend(
                [
                    ast.Constant(value=False, ctx=ast.Load(), mark=True),
                    ast.Constant(value=True, ctx=ast.Load(), mark=True),
                ]
            )
        if constant_type == 'str' :
            node_list.extend(
                [
                    ast.Constant(value="", ctx=ast.Load(), mark=True)
                ]
            )

        return node_list

    def do_call_chain(self) :
        ast_list = []
        chain_start = False

        for neg_idx, neg_info in enumerate(self.neg_infos) :
            neg_filename = neg_info['info']['filename']
            neg_funcname = neg_info['info']['funcname']
            neg_classname = neg_info['info']['classname']
            neg_lineno = neg_info['info']['line']
            neg_args = neg_info['args']
            test = set(neg_info['idx'])

            if test != self.test :
                continue 

            try :
                neg_file_node = deepcopy(self.files[neg_filename])
            except :
                continue

            prev_funcname = None if neg_idx == 0 else self.neg_infos[neg_idx-1]['info']['funcname']

            target = find_error_stmt(neg_file_node, neg_lineno)

            if chain_start : # call 분석
                self.call_analysis(target)

                if self.candidate_arg :
                    for (arg, name) in self.candidate_arg :
                        change_node_list = self.get_change_node_list(name, arg)

                        for change_node in change_node_list :
                            change = ChangeNode(arg, change_node)

                            change.get_node(neg_file_node)
                            new_ast = deepcopy(neg_file_node)
                            ast_list.append((neg_filename, neg_funcname, neg_classname, neg_args, new_ast))
                            change.revert_node(neg_file_node)

                    self.candidate_arg = set([])

                
                if self.candidate_keyword :
                    for keyword in self.candidate_keyword :
                        change_node_list = self.get_change_node_list(keyword.arg, keyword.value)

                        for change_node in change_node_list :
                            change = ChangeNode(keyword.value, change_node)

                            change.get_node(neg_file_node)
                            new_ast = deepcopy(neg_file_node)
                            ast_list.append((neg_filename, neg_funcname, neg_classname, neg_args, new_ast))
                            change.revert_node(neg_file_node)

                    self.candidate_keyword = set([])

                if self.candidate_call :
                    for (index, call_node, arg_node, name) in self.candidate_call :
                        arg_typs = self.neg_infos[neg_idx-1]['args'].get(name, [])

                        if not arg_typs :
                            continue

                        funcname = None

                        # Name만 추적
                        if isinstance(call_node.func, ast.Name) :
                            funcname = call_node.func.id

                        if funcname :
                            input_types = []
                            for pos_func_info in self.pos_func_infos :
                                if pos_func_info['func_name'] == funcname :
                                    input_types = abstract_input_types(pos_func_info['path'], pos_func_info['func_name'], self.pos_func_infos)

                            should_fix = True
                            to_typs = list()

                            for input_type in input_types :
                                try :
                                    if input_type[index] in arg_typs :
                                        should_fix = False
                                        break
                                    to_typs.append(input_type[index])
                                except Exception as e :
                                    print("input_type Overflow")

                            if should_fix :
                                for arg_typ in arg_typs :
                                    for to_typ in to_typs :
                                        if arg_typ == "None" :
                                            test = ast.Call(
                                                func=ast.Name(id='isinstance', ctx=ast.Load()),
                                                args=[
                                                    deepcopy(arg_node),
                                                    ast.Call(
                                                        func=ast.Name(id='type', ctx=ast.Load()),
                                                        args=[
                                                            ast.Name(id=arg_typ, ctx=ast.Load())
                                                        ],
                                                        keywords=[]
                                                    )
                                                ],
                                                keywords=[]
                                            )
                                        else :
                                            test = ast.Call(
                                                func=ast.Name(id='isinstance', ctx=ast.Load()),
                                                args=[
                                                    deepcopy(arg_node),
                                                    ast.Name(id=arg_typ, ctx=ast.Load())
                                                ],
                                                keywords=[]
                                            )

                                        new_node = ast.IfExp(
                                            test=test,
                                            body=ast.Constant(value='<pyfix_template>', is_template=True, template_type=Template.TypeCasting, from_typ=arg_typ, to_typ=to_typ, args='constant'),
                                            orelse=deepcopy(arg_node),
                                            mark=True
                                        )

                                        change = ChangeNode(arg_node, new_node)

                                        change.get_node(neg_file_node)
                                        new_ast = deepcopy(neg_file_node)
                                        ast_list.append((neg_filename, neg_funcname, neg_classname, neg_args, new_ast))
                                        change.revert_node(neg_file_node)


            lineno_list = self.get_lineno_list(neg_funcname, neg_filename, neg_lineno)
            chain = StmtChain(lineno_list, target, neg_file_node)
            stmt_chain = chain.get_stmt_chain()
            
            stmt_chain = list(reversed(stmt_chain))
            
            if not chain_start :
                look_if = False
                for target_child in ast.walk(target) :
                    if isinstance(target_child, ast.Raise) :
                        look_if = True

                if look_if : 
                    # if문에서 보는 Name들을 싹다 모으자
                    for stmt in stmt_chain :
                        if isinstance(stmt, ast.If) :
                            var_set = self.get_all_name(stmt.test)
                            self.lookup_var_set.update(var_set)

                            break

                else :
                    # type 차이가 나는 variable을 모으자
                    for neg_arg, neg_typ in neg_args.items() :
                        add_arg = True
                        for pos_filename, pos_infos in self.pos_info.items() :
                            for pos_lineno, pos_info in pos_infos.items() :
                                if pos_filename == neg_filename and pos_lineno == neg_lineno :
                                    for info in pos_info :
                                        pos_typ = info['info'].get(neg_arg, None)

                                        if pos_typ is not None :
                                            add_arg = add_arg and (pos_typ not in neg_typ)

                        if add_arg :
                            self.lookup_var_set.add(neg_arg)

                chain_start = True

            for stmt in stmt_chain :
                self.visit(stmt)

        return ast_list
    