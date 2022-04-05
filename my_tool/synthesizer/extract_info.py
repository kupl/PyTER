import ast
from collections.abc import Sequence
from typing import (
    Iterable, NamedTuple, List, Optional, NamedTuple, OrderedDict, Dict
)

import copy

#from . import make_hole

class IterArg() :
    typ : str
    diff : Dict
    args : List
    def __init__(self, **kv) :
        self.__dict__.update(kv)

    def __str__(self) :
        return "IterArg(typ : {}, diff : {}, args : {})".format(self.typ, self.diff, self.args)

class Arg() :
    typ : str
    diff : Dict
    def __init__(self, **kv) :
        
        self.__dict__.update(kv)

    def __str__(self) :
        return "Arg(typ : {}, diff : {})".format(self.typ, self.diff)


#IterArg = Dict('IterArg', [('typ', str), ('diff', int), ('args', List)])
#Arg = Dict('Arg', [('typ', str), ('diff', int)])

POS_FUNC_TYPE = None

def comment_to_typlist(type_comment) :
    # str -> ArgTypes()
    '''
    Type -> Type에서
    Type을 이끌어내기 위해
    '''
    last_idx = type_comment.find("->") # 이래야 ( , , ) 이렇게 나옴
    get_args_typs = type_comment[1:(last_idx-2)]

    def split_args(args) :
        start_idx = 0
        paren_num = 0
        result_args = []

        args = args.strip()
        type_name = ""

        single_arg = True

        for i, char in enumerate(args) :
            if char == "[" :
                paren_num = paren_num + 1
            if char == "]" :
                paren_num = paren_num - 1
            if (char == "," and paren_num == 0) :
                single_arg = False
                new_arg_typ = split_args(args[start_idx:i].strip())
                result_args.append(new_arg_typ)

                start_idx = i+1

        if single_arg : # arg 한개

            if args[-1] == "]" : # 이러면 List이거나 Tuple이거나 등등 ....
                paren_start = args.find("[")
                type_name = args[:paren_start]
                args = args[(paren_start+1):-1]

                result_args = split_args(args)
                if not isinstance(result_args, list) :
                    result_args = [result_args]

                return IterArg(typ=type_name.strip(), diff={}, args=result_args)
            return Arg(typ=args, diff={})

        new_arg_typ = split_args(args[start_idx:].strip())
        result_args.append(new_arg_typ)
        return result_args

    result_args = split_args(get_args_typs)
    if not isinstance(result_args, list) :
        result_args = [result_args]
    return result_args

def extract_funcname(func) :
    # A.B.C 일 때, C를 가져오기 위한 함수
    funcname = None 

    if isinstance(func, ast.Attribute) :
        funcname = func.attr

    if isinstance(func, ast.Name) :
        funcname = func.id

    return funcname

def extract_call_var_typ(expr, var, call_expr, idx) :
    if isinstance(expr, ast.Name) and expr.id == var :
        func = call_expr.func

        funcname = extract_funcname(func)

        result_typ = set()

        #print(funcname, var)

        for func_infos in POS_FUNC_TYPE.values() :
            for func_info in func_infos :
                if func_info['func_name'] == funcname :
                    type_comments = func_info['type_comments']

                    for type_comment in type_comments :
                        args = comment_to_typlist(type_comment)
                        #print(args)
                        #print(idx)

                        for i in idx :
                            # 미완성...
                            result_typ.add(args[i])

        if not result_typ :
            return None
        return result_typ

    if isinstance(expr, ast.Call) :
        for i, e in enumerate(expr.args) :
            result_typ = extract_call_var_typ(e, var, expr, [i])

        if result_typ is not None :
            return result_typ

    for i, e in enumerate(ast.iter_child_nodes(expr)) :
        if isinstance(e, ast.expr) :
            if isinstance(e, ast.Call) :
                result_typ = extract_call_var_typ(e, var, e, [])
            elif isinstance(e, (ast.List, ast.Tuple, ast.Dict, ast.Set)) :
                result_typ = extract_call_var_typ(e, var, call_expr, idx.append(i))
                del idx[-1]
            else :
                result_typ = extract_call_var_typ(e, var, call_expr, idx)
            
            if result_typ is not None :
                return result_typ

    return None

def make_expr_hole(node, candidates, origin) :
    if isinstance(node, list) :
        for i, n in enumerate(node) :
            if not isinstance(n, (ast.mod, ast.stmt, ast.expr)) :
                break

            if isinstance(n, ast.expr) :
                setattr(node[i], "hole", True)
                candidates.append(copy.deepcopy(origin))
                delattr(node[i], "hole")

            _fields = n._fields

            for field in _fields :
                attr = getattr(n, field)
                if isinstance(attr, ast.stmt) :
                    candidates = make_expr_hole(attr, candidates, origin)
                
                elif isinstance(attr, ast.expr) :
                    setattr(node[i], "hole", True)
                    candidates.append(copy.deepcopy(origin))
                    delattr(node[i], "hole")
                    candidates = make_expr_hole(attr, candidates, origin)

                elif isinstance(attr, list) :
                    candidates = make_expr_hole(attr, candidates, origin)

    elif isinstance(node, (ast.mod, ast.stmt, ast.expr)) :
        _fields = node._fields

        for field in _fields :
            attr = getattr(node, field)
            if isinstance(attr, ast.stmt) :
                candidates = make_expr_hole(attr, candidates, origin)
            
            elif isinstance(attr, ast.expr) :
                setattr(node, "hole", True)
                candidates.append(copy.deepcopy(origin))
                delattr(node, "hole")
                candidates = make_expr_hole(attr, candidates, origin)

            elif isinstance(attr, list) :
                candidates = make_expr_hole(attr, candidates, origin)

    return candidates


class TypeCheckStmt(ast.NodeVisitor) :
    def __init__(self) :
        super().__init__()
        self.candidates_stmt = list()

    def visit_Try(self, node) :
        super().generic_visit(node)

        for handler in node.handlers :
            if hasattr(handler, 'type') :
                if isinstance(handler.type, ast.Name) and handler.type.id == 'TypeError' :
                    self.candidates_stmt.extend(handler.body)
            else :
                self.candidates_stmt.extend(handler.body)

    def visit_If(self, node) :
        super().generic_visit(node)

        else_flag = False
        for test in ast.walk(node.test) :
            if isinstance(test, ast.Call) :
                funcname = extract_funcname(test.func)

                if funcname == 'isinstance' :
                    #if isinstance(test_child.args[0], (ast.Name, ast.Attribute)) and ast.unparse(test_child.args[0]#) == var_name :
                    if isinstance(test.args[0], (ast.Name, ast.Attribute)) :
                        self.candidates_stmt.extend(node.body)
                        else_flag = True
                
                #if 'is' in funcname and 'type' in funcname :
                if 'is_' in funcname  :
                    self.candidates_stmt.extend(node.body)
                    else_flag = True

            if isinstance(test, ast.Compare) and isinstance(test.ops[0], (ast.Is, ast.IsNot)) : # None check
                # left check
                #if not (isinstance(test_child.left, (ast.Name, ast.Attribute)) and ast.unparse(test_child.left) == #var_name) :
                if not isinstance(test.left, (ast.Name, ast.Attribute)) :
                    continue

                # right check
                if isinstance(test.comparators[0], ast.Constant) :
                    if test.comparators[0].value is None:
                        self.candidates_stmt.extend(node.body)
                        else_flag = True

            if isinstance(test, ast.Expr) : # None Check
                if isinstance(test.value, (ast.Name, ast.Attribute)) : 
                    self.candidates_stmt.extend(node.body)
                    else_flag = True

            if isinstance(test, ast.UnaryOp) :
                if isinstance(test.op, ast.Not) and isinstance(test.operand, ast.Name) :
                    self.candidates_stmt.extend(node.body)
                    else_flag = True

        if else_flag == True :
            # if type_checking
            # else 
            # 이거도 타입체킹임
            def check_if_stmt(node) :
                orelse = node.orelse

                if orelse :
                    if isinstance(orelse[0], ast.If) :
                        self.candidates_stmt.extend(orelse[0].body)
                        check_if_stmt(orelse[0])
                    else :
                        self.candidates_stmt.extend(orelse)

            check_if_stmt(node)

    def extract_isinstance_stmt(self, node) :
        self.candidates_stmt = []
        self.visit(node)
        return self.candidates_stmt
            


def extract_isinstance_stmt_info(target_func) :
    candidates_stmt = []
    extractor = TypeCheckStmt()

    if target_func is None :
        return []

    candidates_stmt.extend(extractor.extract_isinstance_stmt(target_func))

    return candidates_stmt

'''
def extract_isinstance_stmt(var, files_src) :
    
    #var 에 해당하는 isinstance문의 body를 다 끌어내자
    

    candidates_stmt = []

    for src in files_src.values() :
        node = ast.parse(src)

        for child in ast.walk(node) :
            if isinstance(child, ast.If) :
                for test_child in ast.walk(child.test) :
                    # isinstance Call 이거나
                    if isinstance(test_child, ast.Call) :
                        funcname = extract_funcname(test_child.func)

                        if funcname == 'isinstance' :
                            if isinstance(test_child.args[0], ast.Name) and test_child.args[0].id == var:
                                candidates_stmt.append(child.body)
                    # var is None 이거나
                    if isinstance(test_child, ast.Compare) and isinstance(test_child.ops[0], ast.Is) : 
                        # left check
                        if not (isinstance(test_child.left, ast.Name) and test_child.left.id == var) :
                            continue

                        # right check
                        if isinstance(test_child.comparators[0], ast.Constant) :
                            if test_child.comparators[0].value is None:
                                candidates_stmt.append(child.body)

    candidates_hole = list()
    for candidate in candidates_stmt :
        candidate_hole = make_expr_hole(candidate, [], candidate)
        candidates_hole.append(candidate_hole)

    return candidates_hole
'''


def check_error_node(error_node, var, func_type) :
    '''
    error 노드가 return이거나 call이면
    type 정보 이용 가능

    error_node는 stmt
    expr value 를 이끌어내야함
    '''
    global POS_FUNC_TYPE
    POS_FUNC_TYPE = func_type

    if hasattr(error_node, "value") :
        expr = error_node.value
        typ = extract_call_var_typ(expr, var, expr, [])

        if typ is None :
            return set(["int"]) # 임시
        return typ

def check_error_var(error_node, pos_func_type, neg_func_type) :
    '''
    error 노드만 가지고
    variable과 type 우선순위 정하기
    '''

    global POS_FUNC_TYPE
    POS_FUNC_TYPE = pos_func_type

    if isinstance(error_node, ast.Call) :
        func = error_node.func
        funcname = extract_funcname(func)

        positive_funcs = []
        negative_funcs = []

        '''
        type_comment -> IterArg, Arg화
        '''
        for i, func_infos in pos_func_type.items() :
            for func_info in func_infos :
                if func_info['func_name'] == funcname :
                    type_comments = func_info['type_comments']

                    for type_comment in type_comments :
                        positive_funcs.append(comment_to_typlist(type_comment))
                        

        for i, func_infos in neg_func_type.items() :
            for func_info in func_infos :
                if func_info['func_name'] == funcname :
                    type_comments = func_info['type_comments']

                    for type_comment in type_comments :
                        negative_funcs.append(comment_to_typlist(type_comment))

        '''
        negative와 positive 다른 거 개수 세기
        '''
        for neg_args in negative_funcs :
            for pos_args in positive_funcs :

                def get_diff_args(neg_args, pos_args) :

                    for i in range(0, min(len(neg_args), len(pos_args))) :
                        neg_arg = neg_args[i]
                        pos_arg = pos_args[i]

                        if type(neg_arg) == type(pos_arg) :
                            if (neg_arg.typ != pos_arg.typ) :
                                neg_arg.diff[pos_arg.typ] = neg_arg.diff.get(pos_arg.typ, 0) + 1
                            
                            if hasattr(neg_arg, "args") :
                                get_diff_args(neg_arg.args, pos_arg.args)
                        else :
                            neg_arg.diff[pos_arg.typ] = neg_arg.diff.get(pos_arg.typ, 0) + 1
                        

                get_diff_args(neg_args, pos_args)

        '''
        negative case diff 순으로 변수 순서 배열
        '''
        func_args = error_node.args 

        def get_name_attr(args, neg_args) :
            arg_diff = dict()
            for i, arg in enumerate(args) :
                if isinstance(arg, (ast.Set, ast.List, ast.Tuple)) :
                    arg_diff.update(get_name_attr(arg.elts, neg_args[i]))

                if isinstance(arg, ast.Name) :
                    arg_diff[arg.id] = neg_args[i].diff

                if isinstance(arg, ast.Attribute) :
                    arg_diff[arg.attr] = neg_args[i].diff

            sorted_arg_diff = dict()
            for arg, diff in arg_diff.items() :
                sorted_arg_diff[arg] = dict(sorted(diff.items(), key=lambda x : x[1], reverse=True))

            return sorted_arg_diff

        sorted_arg_diff = []

        for neg_args in negative_funcs :
            arg_diff = get_name_attr(func_args, neg_args)
            
            filtered_arg_diff = dict(filter(lambda x : bool(x[1]), arg_diff.items()))
            # ㅇㅣ끌어낼 타입 정보가 없으면 스킵
            if not filtered_arg_diff :
                continue

            sorted_arg_diff.append(dict(sorted(arg_diff.items(), key=lambda x : sum(x[1].values()), reverse=True)))

        return sorted_arg_diff

def find_error_stmt(node, lineno) :
    '''
    에러가 난 node 중 가장 작은 단위의 stmt를 구하자
    '''
    result = None 
    smaller_stmt = None

    #print(ast.dump(node, include_attributes=True, indent=4))

    for child in ast.iter_child_nodes(node) :
        if isinstance(child, ast.stmt) and hasattr(child, "lineno") :
            if child.lineno <= lineno <= child.end_lineno :
                smaller_stmt = find_error_stmt(child, lineno)
                
                if smaller_stmt is None :
                    return child
    
                return smaller_stmt
        elif isinstance(child, ast.stmt) :
            smaller_stmt = find_error_stmt(child, lineno)

            return smaller_stmt

    return None

def find_error_call(error_node, funcname) :
    for child in ast.walk(error_node) :
        if isinstance(child, ast.Call) :
            if funcname == extract_funcname(child.func) :
                return child


def compare_args(pos_args_list, neg_args) :
    var_candidates = dict()
    for neg_arg, neg_typ in neg_args.items() :
        typs = dict()
        for pos_args in pos_args_list :
            for pos_arg, pos_typ in pos_args.items() :
                if pos_arg == neg_arg and pos_typ != neg_typ :
                    typs[neg_typ] = typs.get(neg_typ, 0) + 1

        if typs :
            var_candidates[neg_arg] = typs

    return var_candidates
        
def typ_str_modify(typ_str) :
    '''
    정제되지 않은 typ_str을 적절히 변형시켜주자
    ex) List[str, str] -> list ...
    '''
    index = typ_str.find('[')

    if index >= 0 :
        return typ_str[:index].lower()
    else :
        return typ_str