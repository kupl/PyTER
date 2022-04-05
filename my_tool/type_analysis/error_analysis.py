'''
error line을 static anlaysis를 통해
문제 변수를 이끌어내는 파일입니다~~
'''

import ast
import itertools
import typing
from copy import copy
from collections import abc
from pprint import pprint

from type_analysis.var_type_inference import VarTypeInference
from .util import abstract_type, abstract_type_list, dict_output_type, abstract_input_types, get_type_list
from .custom_type_system import NUMERIC_LIST


class NameAnalysis(ast.NodeVisitor) :
    def __init__(self) :
        self.name_set = set([])

    def visit_Attribute(self, node) :
        def extract_value(node) :
            if isinstance(node.value, ast.Attribute) :
                value_name = extract_value(node.value)

            elif isinstance(node.value, ast.Name) :
                value_name = node.value.id

            elif isinstance(node.value, ast.Constant) :
                return ""
            
            elif isinstance(node.value, ast.Call) :
                '''
                이거 어떻게 해야하지? (as_uri.PurePosixPath(path) 같은 느낌)
                beets-3360이 이 예시
                '''
                func = node.value.func

                if isinstance(func, ast.Name) :
                    value_name = func.id

                elif isinstance(func, ast.Attribute) :
                    value_name = extract_value(func)

                else :
                    print("What? ", func)
                    raise Exception

            if value_name == "" :
                return ""
            
            name = value_name + "." + node.attr

            return name
        name = extract_value(node)

        self.name_set.add(name)

    def visit_Name(self, node) :
        self.name_set.add(node.id)

    def extract_name_list(self, node) :
        self.name_set = set([])
        self.visit(node)
        return self.name_set

class ErrorAnalysis(ast.NodeVisitor) :
    

    def __init__(self, var_infos, neg_file_node, pos_func_infos) :
        self.IterableType = ['str', 'List', 'Set', 'Tuple']
        self.var_infos = var_infos
        self.neg_file_node = neg_file_node
        self.pos_func_infos = pos_func_infos

        self.var_score = dict()
        self.operator_mutate = set([])
        self.name_analysis = NameAnalysis()

    def extract_typ(self, var_typ_list) :
        '''
        서로 다른 타입이면 None
        같은 타입이면 그 타입
        '''
        result_typ = var_typ_list[0][1]

        for (_, typ) in var_typ_list :
            if result_typ != typ :
                return None

        return result_typ

    def add_score(self, var_typ_list) :
        '''
        다른 타입이면 서로 변수에다가 score + 1 시킴
        '''
        var_typ_list = list(filter(lambda x: x is not None, var_typ_list)) # None 제거

        for product in itertools.product(*var_typ_list) :
            for ((var1, typ1), (var2, typ2)) in itertools.combinations(product, 2) :
                # Iterable Type Check
                #print(var1, typ1, var2, typ2)
                if isinstance(typ1, list) :
                    #if str(typing.Any) not in typ2 and not isinstance(var2, str) :
                    if not isinstance(var2, str) :
                        for typ in typ1 :
                            if typ in typ2 :
                                continue
                            var_dict = self.var_score.get(var2, dict())
                            var_dict[typ] = var_dict.get(typ, 0) + 1

                            self.var_score[var2] = var_dict

                if isinstance(typ2, list) :
                    #if str(typing.Any) not in typ1 and not isinstance(var1, str):
                    if not isinstance(var1, str) :
                        for typ in typ2 :
                            if typ in typ1 :
                                continue
                            var_dict = self.var_score.get(var1, dict())
                            var_dict[typ] = var_dict.get(typ, 0) + 1

                            self.var_score[var1] = var_dict

                if not (isinstance(typ1, list) or isinstance(typ2, list)) :
                    typ1 = abstract_type(typ1)
                    typ2 = abstract_type(typ2)

                    if typ1 != typ2 :
                        if not isinstance(var1, str) and typ2 != str(typing.Any) :
                            var_dict = self.var_score.get(var1, dict())
                            var_dict[typ2] = var_dict.get(typ2, 0) + 1

                            self.var_score[var1] = var_dict
                        if not isinstance(var2, str) and typ1 != str(typing.Any) : 
                            var_dict = self.var_score.get(var2, dict())
                            var_dict[typ1] = var_dict.get(typ1, 0) + 1

                            self.var_score[var2] = var_dict

    def single_add_score(self, var, typ, value = 1) :
        var_dict = self.var_score.get(var, dict())
        if typ :
            var_dict[typ] = var_dict.get(typ, 0) + value

        self.var_score[var] = var_dict

    # Stmt
    def visit_AugAssign(self, node) :
        target = self.visit(node.target)
        value = self.visit(node.value)

        # target, value 비교 필요
        self.add_score([target, value])

    def visit_Assign(self, node) :
        if len(node.targets) == 1 and isinstance(node.targets[0], (ast.Name, ast.Attribute)):
            value = self.visit(node.value)

            if value is None :
                return

            for (_, typs) in value :
                for typ in typs :
                    self.single_add_score(node.targets[0], typ)
        else :
            self.generic_visit(node)
        #self.visit(node.value)

    def visit_For(self, node) :
        inference_typ = None
        var_list = []
        for child in ast.walk(node.iter) :
            if isinstance(child, (ast.Name, ast.Attribute)) :
                var_list.append(child)

        for var in var_list :
            target_node = var
            var_type_inference = VarTypeInference(target_node, copy(self.var_infos), self.origin)
            typ_dict = var_type_inference.get_var_type(self.neg_file_node)
            
            #if not typ_dict :
            #    return [(node, [])]

            #typ_dict = dict(sorted(typ_dict.items(), key=lambda x : x[1], reverse=True))
            #inference_typ = list(typ_dict.keys())[0] # 1st key
            
            if typ_dict :
                for key, value in typ_dict.items() :
                    self.single_add_score(var, key, value)
            else :
                for iter_type in self.IterableType :
                    self.add_score([[(var, abstract_type_list(self.var_infos.get(var, [])))], [('__constant__', iter_type)]])

        self.generic_visit(node)

    def visit_If(self, node) :
        self.visit(node.test)


    # Expr
    def visit_IfExp(self, node) :
        # 웬만하면 body, else의 타입을 지켜주자
        #print("???")
        var_typ_list = []

        body_type = self.visit(node.body)
        var_typ_list.append(body_type)

        or_type = self.visit(node.orelse)
        var_typ_list.append(or_type)

        self.add_score(var_typ_list)

        body_type.extend(or_type)

        return body_type

    def visit_Dict(self, node) :
        self.generic_visit(node)
        return [("__constant__", ['Dict'])]

    def visit_Set(self, node) :
        self.generic_visit(node)
        return [("__constant__", ['Set'])]

    def visit_ListComp(self, node) :
        generators = node.generators
        

        for generator in generators :
            var_typ_list = [[(("__constant__iter__"), self.IterableType)]]
            iter = self.visit(generator.iter)
            var_typ_list.append(iter)

            self.add_score(var_typ_list)

    def visit_Call(self, node) :
        super().generic_visit(node)
        var_typs = copy(self.var_infos.get(ast.unparse(node.func), []))

        if var_typs :
            skip=False
            for var_typ in var_typs :
                if 'method' in var_typ :
                    skip=True
                    break
            if not skip :
                self.single_add_score(node, 'method')

        type_list = []
        if isinstance(node.func, ast.Name) :
            name_str = ast.unparse(node.func)

            get_typ = []
            if len(node.args) == 1 and isinstance(node.args[0], (ast.Name, ast.Attribute)) :
                arg_str = ast.unparse(node.args[0])
                get_typ = self.var_infos.get(arg_str, [])

            if name_str in ['int', 'float'] :
                if 'None' in get_typ :
                    self.single_add_score(node.args[0], 'empty', 1)
                type_list.append(('__constant__', [name_str]))

            if name_str in ['str', 'bool', 'bytes'] :
                type_list.append(('__constant__', [name_str]))

            if name_str in ['list', 'tuple', 'dict', 'set'] :
                if 'None' in get_typ :
                    self.single_add_score(node.args[0], 'empty', 1)
                type_list.append(('__constant__', [name_str.title()]))

            if name_str in ['len'] :
                if 'None' in get_typ :
                    self.single_add_score(node.args[0], 'empty', 1)
                type_list.append(('__constant__', ['int']))

        #if not type_list :
        #    for arg in node.args :
        #        arg_typ = self.visit(arg)

        #        if isinstance(arg_typ, list) :
        #            type_list.extend(arg_typ)
            
        return type_list
        
        '''
        funcname = None

        # Name만 추적
        if isinstance(node.func, ast.Name) :
            funcname = node.func.id

        if funcname :
            for pos_func_info in self.pos_func_infos :
                if pos_func_info['func_name'] == funcname :
                    input_types = abstract_input_types(pos_func_info['path'], pos_func_info['func_name'], self.pos_func_infos)

            check_index = [i for i in range(0, len(node.args))]

            for i, arg in enumerate(node.args) :
                if not arg 
                arg_type = self.visit(arg)[0][1]
                print(arg_type)

                if str(typing.Any) in arg_type :
                    check_index.remove(i)
                    continue
                
                for input_type in input_types :
                    try :
                        if input_type[i] in arg_type :
                            check_index.remove(i)
                    except :
                        print("input_type Overflow")

            print(check_index)

        if isinstance(node.func, ast.Attribute) and node.func.attr == 'get' :
        '''

    def visit_Compare(self, node) :
        var_typ_list = []
        result = []


        left = self.visit(node.left)
        var_typ_list.append(left)

        result.extend(left)
        isin = False

        for i, value in enumerate(node.comparators) :
            val = self.visit(value)
            var_typ_list.append(val)
            result.extend(val)
            
            if isinstance(node.ops[i], (ast.In, ast.NotIn)) :
                isin = True
                # value가 Iterable 해야한다
                inference_typ = None
                var_list = []
                for child in ast.walk(value) :
                    if isinstance(value, (ast.Name, ast.Attribute)) :
                        var_list.append(value)

                for var in var_list :
                    target_node = var
                    var_type_inference = VarTypeInference(target_node, copy(self.var_infos), self.origin)
                    typ_dict = var_type_inference.get_var_type(self.neg_file_node)
                    
                    #if not typ_dict :
                    #    continue

                    #typ_dict = dict(sorted(typ_dict.items(), key=lambda x : x[1], reverse=True))
                    #inference_typ = list(typ_dict.keys())[0] # 1st key
                    
                    if typ_dict :
                        for key, value in typ_dict.items() :
                            self.single_add_score(var, key, value)
                    else :
                        for iter_type in self.IterableType :
                            self.add_score([val, [('__constant__', iter_type)]])

                # 지금은 스킵
                continue 

        self.add_score(var_typ_list)
        result.append(('__constant__', ['bool']))

        if isin :
            result = [('__constant__', ['bool'])]

        return result

    def visit_BinOp(self, node) :
        var_typ_list = []

        
        
        left = self.visit(node.left)
        var_typ_list.append(left)

        right = self.visit(node.right)
        var_typ_list.append(right)

        # operator 체크
        # bool만 있는데 numeric operator 이상함
        # numeric만 있는데 bool operator 이상함
        left_has_bool = False
        left_has_numeric = False
        left_bool_node = set([])
        left_numeric_node = set([])

        right_has_bool = False
        right_has_numeric = False
        right_bool_node = set([])
        right_numeric_node = set([])

        for left_info in left :
            left_typs = left_info[1]

            for left_typ in left_typs :
                if 'bool' in left_typ : 
                    left_has_bool = True
                    left_bool_node.add(left_info[0])
                for numeric_typ in NUMERIC_LIST :
                    if numeric_typ in left_typ :
                        left_has_numeric = True
                        left_numeric_node.add(left_info[0])

        for right_info in right :
            right_typs = right_info[1]

            for right_typ in right_typs :
                if 'bool' in right_typ : 
                    right_has_bool = True
                    right_bool_node.add(right_info[0])
                for numeric_typ in NUMERIC_LIST :
                    if numeric_typ in right_typ :
                        right_has_numeric = True
                        right_numeric_node.add(right_info[0])

        can_bool_op = left_has_bool and right_has_bool
        can_numeric_op = left_has_numeric and right_has_numeric

        numeric_op = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv)
        bool_op = (ast.BitOr, ast.BitXor, ast.BitAnd)

        total_bool_node = tuple(left_bool_node | right_bool_node)
        total_numeric_node = tuple(left_numeric_node | right_numeric_node)

        if not can_numeric_op and bool_op and isinstance(node.op, numeric_op) :
            self.operator_mutate.add((node, bool_op, total_bool_node))

        if not bool_op and can_numeric_op and isinstance(node.op, bool_op) :
            self.operator_mutate.add((node, numeric_op, total_numeric_node))

        self.add_score(var_typ_list)
        left.extend(right)

        if isinstance(node.op, bool_op) :
            left.append(('__constant__', ['bool']))

        return left
        
    def visit_UnaryOp(self, node) :
        return self.visit(node.operand)

    def visit_Attribute(self, node) :
        def extract_value(node) :
            if isinstance(node.value, ast.Attribute) :
                value_name = extract_value(node.value)

            elif isinstance(node.value, ast.Name) :
                value_name = node.value.id

            elif isinstance(node.value, ast.Constant) :
                return ""
            
            elif isinstance(node.value, ast.Call) :
                '''
                이거 어떻게 해야하지? (as_uri.PurePosixPath(path) 같은 느낌)
                beets-3360이 이 예시
                '''
                func = node.value.func

                if isinstance(func, ast.Name) :
                    value_name = func.id

                elif isinstance(func, ast.Attribute) :
                    value_name = extract_value(func)
            
            try :
                if value_name == "" :
                    return ""
            except Exception as e :
                #print(ast.dump(node, indent=4))
                return ""

            name = value_name + "." + node.attr

            return name

        name = extract_value(node)

        typ = copy(self.var_infos.get(name, None))

        #if typ is None :
        #    if isinstance(node.value, ast.Subscript) : # 가능성이 있음 a[x].b 에서 a[x].b 가 없을 확률이...
        #        self.single_add_score(node, '')
        #    return [(node, [])]
        target_node = node
        var_type_inference = VarTypeInference(target_node, copy(self.var_infos), self.origin)
        typ_dict = var_type_inference.get_var_type(self.neg_file_node)
        
        if typ is None :
            if not typ_dict :
                return [(node, [])]
            
            inference_typ = []
            
            typ_dict = dict(sorted(typ_dict.items(), key=lambda x : x[1], reverse=True))

            max_score = 0
            for key, value in typ_dict.items() :
                if value < max_score :
                    break
                if value > max_score :
                    max_score = 0
                inference_typ += [key] * value
            #inference_typ = [list(typ_dict.keys())[0]] * list(typ_dict.values())[0]# 1st key
            #inference_typ = list(typ_dict.keys())

            #return [(node, abstract_type_list([inference_typ]))]
            return [(node, abstract_type_list(inference_typ))]
        else :
            inference_typ = []
            #for key, value in typ_dict.items() :
            #    inference_typ += [key] * value 

            if typ_dict :
                typ_dict = dict(sorted(typ_dict.items(), key=lambda x : x[1], reverse=True))

                max_score = 0
                for key, value in typ_dict.items() :
                    if value < max_score :
                        break
                    if value > max_score :
                        max_score = 0
                    inference_typ += [key] * value
                #inference_typ = [list(typ_dict.keys())[0]] * list(typ_dict.values())[0]# 1st key

            abs_typ = set(abstract_type_list(typ))
            abs_inf = set(abstract_type_list(inference_typ))

            #if not abs_typ.intersection(abs_inf) :
            #    for t in abs_inf :
            #        self.single_add_score(node, t, len(inference_typ))
            for t in abs_inf :
                #if t in abs_typ :
                #    continue
                if t == 'None' :
                    continue
                self.single_add_score(node, t, 1)
        
        
        return [(node, abstract_type_list(typ))]
        #return [(name, self.var_infos.get(name, typing.Any))]

    def visit_Subscript(self, node) :
        '''
        Subscript의 value는 Iterable 해야합니다...
        Slice에 따라 리턴 타입이 달라집니다...
        '''
        value_name = ast.unparse(node.value)
        value_type = copy(self.var_infos.get(value_name, []))

        if not value_type :
            return [(node, [])]

        abs_value_types = abstract_type_list(value_type)

        result = []

        slice_type = abstract_type_list(copy(self.var_infos.get(ast.unparse(node.slice), [""])))

        if isinstance(node.slice, (ast.Tuple, ast.Slice)) or set(slice_type).issubset(set(["Tuple", "slice"])):
            # 처리해주어야 하는데... iterable 하다? <- 이거 필요해..
            value_typ = abstract_type_list(copy(self.var_infos.get(ast.unparse(node.value), [""])))
            result.append((node.value, value_typ))
        else : # 단일 원소일 확률 높음
            '''
            value_type은 Mapping이어야 함
            '''
            is_in_dict = False
            for i, abs_value_type in enumerate(abs_value_types) :
                if 'Dict' == abs_value_type :
                    output = dict_output_type(value_type[i])
                    if output:
                        typ_list = get_type_list(output)
                        result.append((node, typ_list))
                    is_in_dict = True

            if not is_in_dict :
                self.single_add_score(node.value, "Dict")
                result.append((node, value_type))

        self.generic_visit(node)
        return result

    def visit_Slice(self, node) :
        var_typ_list = [[(("__constant__slice__"), ["int"])]] # slice의 lower, upper는 int형이어야함

        if getattr(node, "lower") is not None :
            lower = self.visit(node.lower)
            var_typ_list.append(lower)

        if getattr(node, "upper") is not None:
            upper = self.visit(node.upper)
            var_typ_list.append(upper)

        self.add_score(var_typ_list)

        return []

    def visit_Name(self, node) :
        name = node.id

        typ = copy(self.var_infos.get(name, None))
        #if typ is None :
        #    return [(node, [])]
        target_node = node
        var_type_inference = VarTypeInference(target_node, copy(self.var_infos), self.origin)
        typ_dict = var_type_inference.get_var_type(self.neg_file_node)

        if typ is None :
            if not typ_dict :
                return [(node, [])]
            
            inference_typ = []
            
            typ_dict = dict(sorted(typ_dict.items(), key=lambda x : x[1], reverse=True))

            max_score = 0
            for key, value in typ_dict.items() :
                if value < max_score :
                    break
                if value > max_score :
                    max_score = 0
                inference_typ += [key] * value
            #inference_typ = [list(typ_dict.keys())[0]] * list(typ_dict.values())[0]# 1st key
            #inference_typ = list(typ_dict.keys())

            #return [(node, abstract_type_list([inference_typ]))]
            return [(node, abstract_type_list(inference_typ))]
        else :
            inference_typ = []
            #for key, value in typ_dict.items() :
            #    inference_typ += [key] * value 

            if typ_dict :
                typ_dict = dict(sorted(typ_dict.items(), key=lambda x : x[1], reverse=True))

                max_score = 0
                for key, value in typ_dict.items() :
                    if value < max_score :
                        break
                    if value > max_score :
                        max_score = 0
                    inference_typ += [key] * value
                #inference_typ = [list(typ_dict.keys())[0]] * list(typ_dict.values())[0]# 1st key

            abs_typ = set(abstract_type_list(typ))
            abs_inf = set(abstract_type_list(inference_typ))

            #if not abs_typ.intersection(abs_inf) :
            #    for t in abs_inf :
            #        self.single_add_score(node, t, len(inference_typ))
            for t in abs_inf :
                #if t in abs_typ :
                #    continue
                if t == 'None' :
                    continue
                self.single_add_score(node, t, 1)
        
        return [(node, abstract_type_list(typ))]
        #return [(name, typ)]

    def visit_Constant(self, node) :
        return [("__constant__", [type(node.value).__name__])]

    def visit_JoinedStr(self, node) :
        # 이거 해결할수 있으면?!
        return [("__constant__", ["str"])]

    def visit_List(self, node) :
        self.generic_visit(node)
        return [("__constant__", ['List'])]

    def visit_Tuple(self, node) :
        self.generic_visit(node)
        return [("__constant__", ['Tuple'])]

    def extract_score(self, node) :
        self.origin = node
        self.var_score = dict()
        self.visit(node)

        # sorting
        for key, value in self.var_score.items() :
            self.var_score[key]['total'] = sum(value.values())
            self.var_score[key] = dict(sorted(value.items(), key=lambda x : x[1], reverse=True))

        self.var_score = dict(sorted(self.var_score.items(), key=lambda x : x[1]['total'], reverse=True))

        for value in self.var_score.values() :
            del value['total']

        #pprint(self.var_score)

        return self.var_score, self.operator_mutate

'''
test = ErrorAnalysis({"a" : int, "self.bool" : bool, "int" : int})

code = "a[:self.bool]"
print(test.extract_score(ast.parse(code)))


code = "a+self.bool>int"
print(test.extract_score(ast.parse(code)))
'''