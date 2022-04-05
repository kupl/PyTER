import ast
from .util import FindTargetFunc, abstract_type_list, abstract_type, dict_output_type, get_type_list
from . import custom_type_system
from copy import copy

class VarTypeInference(ast.NodeVisitor) :
    def __init__(self, target_var, neg_infos, origin, skip_var=[], infer_type_dict={}, is_arg=False) :
        self.target_var = target_var
        self.neg_infos = neg_infos
        self.find_var = False
        self.candidate_type = dict()
        self.origin = origin
        self.skip_var = skip_var
        self.infer_type_dict = infer_type_dict
        self.should_check = False
        self.arg_check = False
        self.is_arg = is_arg

    def visit_For(self, node) :
        if node == self.origin :
            return

        self.find_var = False

        if ast.unparse(node.iter) == ast.unparse(self.target_var) :
            iterable_typs = ['str', 'List', 'Set', 'Tuple']

            for typ in iterable_typs :
                self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1

        self.generic_visit(node)

    def visit_AugAssign(self, node) :
        if node == self.origin :
            return

        self.find_var = False
            
        #target_typs = self.visit(node.target)
        #value_typs = self.visit(node.value)
        if ast.unparse(node.target) == ast.unparse(self.target_var) :
            self.find_var = True
            self.should_check = True
            value_typs = self.visit(node.value)
            self.should_check = False
            self.find_var = False
            if value_typs : 
                for typ in value_typs :
                    self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1

            return

        else :
            self.visit(node.value)

            if self.find_var :
                self.find_var = True
                self.should_check = True
                target_typs = self.visit(node.target)
                self.should_check = False
                self.find_var = False
                if target_typs : 
                    for typ in target_typs :
                        self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1

            return

        self.generic_visit(node)

        self.find_var = False

    def visit_Assign(self, node) :
        if node == self.origin :
            return

        self.find_var = False

        if len(node.targets) == 1 :
            if ast.unparse(node.targets[0]) == ast.unparse(self.target_var) :
                self.find_var = True
                self.should_check = True
                value_typs = self.visit(node.value)
                self.should_check = False
                self.find_var = False
                if value_typs : 
                    for typ in value_typs :
                        self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1

            else :
                self.visit(node.value)

                if self.find_var :
                    self.find_var = True
                    self.should_check = True
                    target_typs = self.visit(node.targets[0])
                    self.should_check = False
                    self.find_var = False

                    if target_typs : 
                        for typ in target_typs :
                            self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
        else :
            self.generic_visit(node)

        self.find_var = False

    def visit_Call(self, node) :
        prev_find = self.find_var
        self.find_var = False
        self.generic_visit(node)
        self.find_var = prev_find

        name = node.func

        if isinstance(name, ast.Name) :
            name_str = ast.unparse(name)

            if name_str in ['str', 'int', 'float', 'bool', 'bytes'] :
                return [name_str]

            if name_str in ['list', 'tuple', 'dict', 'set'] :
                return [name_str.title()]

            if name_str in ['len'] :
                return ['int']

            
            if self.is_arg and name_str == 'isinstance' :
                if ast.unparse(self.target_var) == ast.unparse(node.args[0]) :
                    if isinstance(node.args[1], (ast.Name, ast.Attribute)) :
                        typ = ast.unparse(node.args[1])
                        if typ in ['list', 'tuple', 'dict', 'set'] :
                            typ = typ.title()
                        self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
                    elif isinstance(node.args[1], ast.Tuple) :
                        type_list = []
                        for elt in node.args[1].elts :
                            if isinstance(elt, (ast.Name, ast.Attribute)) :
                                typ = ast.unparse(node.args[1])
                                if typ in ['list', 'tuple', 'dict', 'set'] :
                                    typ = typ.title()
                                self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
                        return type_list
            



        #self.generic_visit(node)
        #self.find_var = prev_find

        return []
        

    def visit_JoinedStr(self, node) :
        prev_find = self.find_var
        self.find_var = False
        self.generic_visit(node)
        self.find_var = prev_find

        return ["str"]

    def visit_List(self, node) :
        prev_find = self.find_var
        self.find_var = False
        self.generic_visit(node)
        self.find_var = prev_find
        return ['List']

    def visit_ListComp(self, node) :
        prev_find = self.find_var
        self.find_var = False
        self.generic_visit(node)
        self.find_var = prev_find
        return ['List']

    def visit_Tuple(self, node) :
        prev_find = self.find_var
        self.find_var = False
        self.generic_visit(node)
        self.find_var = prev_find
        return ['Tuple']

    def visit_Dict(self, node) :
        prev_find = self.find_var
        self.find_var = False
        self.generic_visit(node)
        self.find_var = prev_find
        return ['Dict']

    def visit_DictComp(self, node) :
        prev_find = self.find_var
        self.find_var = False
        self.generic_visit(node)
        self.find_var = prev_find
        return ['Dict']

    def visit_Set(self, node) :
        prev_find = self.find_var
        self.find_var = False
        self.generic_visit(node)
        self.find_var = prev_find
        return ['Set']

    def visit_SetComp(self, node) :
        prev_find = self.find_var
        self.find_var = False
        self.generic_visit(node)
        self.find_var = prev_find
        return ['Set']

    def visit_Subscript(self, node) :
        #self.should_check = False
        if self.find_var :
            self.visit(node.slice)
            value = node.value
            value_typs = self.neg_infos.get(ast.unparse(node.value), None)
            cand_typ = []
            if value_typs :
                for value_typ in value_typs :
                    if 'Dict' == abstract_type(value_typ) :
                        output = dict_output_type(value_typ)
                        if output :
                            typ_list = get_type_list(output)
                            cand_typ.extend(typ_list)

            return cand_typ

        self.visit(node.value)
        if self.find_var :
            idx = node.slice
            if isinstance(idx, (ast.Name, ast.Attribute)) :
                if ast.unparse(idx) == ast.unparse(self.target_var) :
                    # 대상이 slice에 있으면...
                    self.find_var = False
                    return

                neg_typs = self.neg_infos.get(ast.unparse(idx), [])
                neg_typs = abstract_type_list(neg_typs)

                candidate = set([])
                for neg_typ in neg_typs :
                    if 'int' in neg_typ :
                        candidate.update(custom_type_system.iterable)

                if not candidate :
                    candidate.add('Dict')

                for cand in candidate :
                    self.candidate_type[cand] = self.candidate_type.get(cand, 0) + 1

            else :
                for cand in custom_type_system.iterable :
                    self.candidate_type[cand] = self.candidate_type.get(cand, 0) + 1

            #self.find_var = False
        prev_find = self.find_var
        self.visit(node.slice)
        self.find_var = prev_find
        value = node.value
        value_typs = self.neg_infos.get(ast.unparse(node.value), None)
        cand_typ = []
        if value_typs :
            for value_typ in value_typs :
                if 'Dict' == abstract_type(value_typ) :
                    output = dict_output_type(value_typ)
                    if output :
                        typ_list = get_type_list(output)
                        cand_typ.extend(typ_list)

        return cand_typ

    def visit_BoolOp(self, node) :
        result_typ = []

        if self.find_var :
            if isinstance(node, ast.Or) :
                for value in node.values :
                    #self.should_check = True
                    prev_find = self.find_var
                    typs = self.visit(value)
                    self.find_var = prev_find
                    #self.should_check = False
                    result_typ.extend(typs)
                    if typs : 
                        for typ in typs :
                            self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
            else :
                result_typ = ['bool']

            return result_typ

        candidate_index = -1
        for i, value in enumerate(node.values) :
            self.visit(value)

            if self.find_var :
                candidate_index = i
                break


        if self.find_var :
            self.candidate_type['bool'] = self.candidate_type.get('bool', 0) + 1 # For ast.And

            if isinstance(node, ast.Or) :
                for i, value in enumerate(node.values) :
                    if i == candidate_index :
                        continue
                    self.should_check = True
                    prev_find = self.find_var
                    typs = self.visit(value)
                    self.find_var = prev_find
                    self.should_check = False
                    result_typ.extend(typs)
                    if typs : 
                        for typ in typs :
                            self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
            else :
                result_typ = ['bool']
        else :
            if isinstance(node, ast.Or) :
                for value in node.values :
                    #self.should_check = True
                    typs = self.visit(value)
                    #self.should_check = False
                    result_typ.extend(typs)
            else :
                result_typ = ['bool']

        return result_typ

    def visit_UnaryOp(self, node) :
        return self.visit(node.operand)

    def visit_BinOp(self, node) :
        numeric_op = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv)
        bool_op = (ast.BitOr, ast.BitXor, ast.BitAnd)

        if self.find_var : # 상위 statement까지 올라가야 한다
            prev_find = self.find_var
            left_typs = self.visit(node.left)
            self.find_var = prev_find
            if not isinstance(left_typs, list) :
                left_typs = []

            prev_find = self.find_var
            right_typs = self.visit(node.right)
            self.find_var = prev_find
            if not isinstance(right_typs, list) :
                right_typs = []

            if isinstance(node.op, bool_op) :
                left_typs.append('bool')

            return left_typs + right_typs

        once_find = False
        self.visit(node.left)

        if self.find_var :
            once_find = True
            self.should_check = True
            prev_find = self.find_var
            right_typs = self.visit(node.right)
            self.find_var = prev_find
            self.should_check = False

            if right_typs : 
                for typ in right_typs :
                    self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
        else :
            self.should_check = True
            right_typs = self.visit(node.right)
            self.should_check = False

            #return left_typs + right_typs

        self.find_var = False

        self.visit(node.right)


        if self.find_var :
            once_find = True
            #self.find_var = False
            self.should_check = True
            prev_find = self.find_var
            left_typs = self.visit(node.left)
            self.find_var = prev_find
            self.should_check = False

            if left_typs : 
                for typ in left_typs :
                    self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
        else :
            self.should_check = True
            left_typs = self.visit(node.left)
            self.should_check = False

        self.find_var = once_find

        if isinstance(node.op, bool_op) :
            left_typs.append('bool')

        left_typs.extend(right_typs)
        return left_typs

    def visit_Compare(self, node) :
        result_typs = []

        if self.find_var :
            left_typs = self.visit(node.left)
            result_typs.extend(left_typs)

            for i, value in enumerate(node.comparators) :
                self.should_check = True
                val = self.visit(value)
                self.should_check = False

                result_typs.extend(val)

                if isinstance(node.ops[i], (ast.In, ast.NotIn)) :
                    isin = True
                    #iterable_typs = ['str', 'List', 'Set', 'Tuple']
                    #result_typs.extend(iterable_typs)

            return result_typs
        #self.should_check = True
        left_typs = self.visit(node.left)
        #self.should_check = False
        isin = False

        if ast.unparse(node.left) == ast.unparse(self.target_var) :
            if not isinstance(left_typs, list) :
                left_typs = []
                
            #result_typs.extend(left_typs)

            for i, value in enumerate(node.comparators) :
                prev_find = self.find_var
                self.should_check = True
                val = self.visit(value)
                self.find_var = prev_find
                self.should_check = False

                result_typs.extend(val)

                
                
                if isinstance(node.ops[i], (ast.In, ast.NotIn)) :
                    isin = True
                    iterable_typs = ['str', 'List', 'Set', 'Tuple']
                    result_typs.extend(iterable_typs)

            for typ in result_typs :
                self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
        else :
            candidate_index = -1
            for i, value in enumerate(node.comparators) :
                #self.should_check = True
                self.visit(value)
                if self.find_var :
                    candidate_index = i
                    break
                #self.should_check = False

            if self.find_var :
                if not isinstance(left_typs, list) :
                    left_typs = []
                
                result_typs.extend(left_typs)

                for i, value in enumerate(node.comparators) :
                    if i == candidate_index :
                        continue
                    prev_find = self.find_var
                    self.should_check = True
                    val = self.visit(value)
                    self.find_var = prev_find
                    self.should_check = False

                    result_typs.extend(val)

                    
                    
                    if isinstance(node.ops[i], (ast.In, ast.NotIn)) :
                        isin = True
                        iterable_typs = ['str', 'List', 'Set', 'Tuple']
                        result_typs.extend(iterable_typs)

                    for typ in result_typs :
                        self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
                    result_typs.extend(val)

        if isin :
            result_typs = ['bool']
        else :
            result_typs.append('bool')

        return result_typs

    def visit_IfExp(self, node) :
        if self.find_var :
            prev_find = self.find_var
            body_typs = self.visit(node.body)
            self.find_var = prev_find

            if not isinstance(body_typs, list) :
                body_typs = []

            prev_find = self.find_var
            orelse_typs = self.visit(node.orelse)
            self.find_var = prev_find

            if not isinstance(orelse_typs, list) :
                orelse_typs = []

            return body_typs + orelse_typs


        #self.should_check = True
        self.visit(node.body)
        #self.should_check = False
        #if not isinstance(body_typs, list) :
        #    body_typs = []

        if self.find_var :
            self.should_check = True
            prev_find = self.find_var
            orelse_typs = self.visit(node.orelse)
            self.find_var = prev_find
            self.should_check = False
            if orelse_typs : 
                for typ in orelse_typs :
                    self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
        else:
            self.should_check = True
            prev_find = self.find_var
            orelse_typs = self.visit(node.orelse)
            self.find_var = prev_find
            self.should_check = False

        #self.should_check = True
        self.visit(node.orelse)
        #self.should_check = False
        #if not isinstance(orelse_typs, list) :
        #    orelse_typs = []

        if self.find_var :
            self.should_check = True
            prev_find = self.find_var
            body_typs = self.visit(node.body)
            self.find_var = prev_find
            self.should_check = False

            if body_typs : 
                for typ in body_typs :
                    self.candidate_type[typ] = self.candidate_type.get(typ, 0) + 1
        else :
            self.should_check = True
            prev_find = self.find_var
            body_typs = self.visit(node.body)
            self.find_var = prev_find
            self.should_check = False

        prev_find = self.find_var
        self.find_var = False
        self.visit(node.body)
        self.find_var = prev_find
        
        body_typs.extend(orelse_typs)
        return body_typs


    def visit_Name(self, node) :
        var_name = ast.unparse(node)
        if var_name is ast.unparse(self.target_var) :         
            self.find_var = True
            return self.neg_infos.get(ast.unparse(node), [])

        if not self.find_var :
            return []

        for skip_var in self.skip_var :
            if var_name == skip_var :
                return []

        var_type = copy(self.neg_infos.get(ast.unparse(node), []))

        if not var_type :
            var_type = copy(self.infer_type_dict.get(var_name, []))

        if not var_type and self.should_check :
            var_type_inference = VarTypeInference(node, self.neg_infos, self.origin, self.skip_var + [ast.unparse(self.target_var)], self.infer_type_dict)
            if self.arg_check :
                typ_dict = var_type_inference.get_arg_type(self.neg_file_node)
            else :
                typ_dict = var_type_inference.get_var_type(self.neg_file_node)

            if not typ_dict :
                return []

            typ_dict = dict(sorted(typ_dict.items(), key=lambda x : x[1], reverse=True))
            max_value = 0

            target_type_list = []

            for key, value in typ_dict.items() :
                if max_value == 0 :
                    max_value = value

                if max_value > value :
                    break

                target_type_list.append(key)

            typ_list = abstract_type_list(target_type_list)

            self.infer_type_dict[var_name] = typ_list 

            return typ_list

        return var_type

    def visit_Attribute(self, node) :
        var_name = ast.unparse(node)
        if var_name == ast.unparse(self.target_var) :
            self.find_var = True
            return self.neg_infos.get(ast.unparse(node), [])

        if not self.find_var :
            return []

        for skip_var in self.skip_var :
            if var_name == skip_var :
                return []

        var_type = copy(self.neg_infos.get(ast.unparse(node), []))

        if not var_type :
            var_type = copy(self.infer_type_dict.get(var_name, []))

        if not var_type and self.should_check :
            var_type_inference = VarTypeInference(node, self.neg_infos, self.origin, self.skip_var + [ast.unparse(self.target_var)], self.infer_type_dict)
            if self.arg_check :
                typ_dict = var_type_inference.get_arg_type(self.neg_file_node)
            else :
                typ_dict = var_type_inference.get_var_type(self.neg_file_node)
            if not typ_dict :
                return []

            typ_dict = dict(sorted(typ_dict.items(), key=lambda x : x[1], reverse=True))
            max_value = 0

            target_type_list = []

            for key, value in typ_dict.items() :
                if max_value == 0 :
                    max_value = value

                if max_value > value :
                    break

                target_type_list.append(key)

            typ_list = abstract_type_list(target_type_list)

            self.infer_type_dict[var_name] = typ_list 

            return typ_list

        return var_type

    def visit_Constant(self, node) :
        typ = type(node.value).__name__
        if typ == 'NoneType' :
            typ = 'None'
        return [typ]

    def generic_visit(self, node):
        self.should_check = False
        self.find_var = False

        if node == self.origin :
            return 
        
        return super().generic_visit(node)

    def get_var_type(self, node) :
        self.neg_file_node = node
        find_func = FindTargetFunc(self.target_var)
        target_func = find_func.get_func(node)

        self.visit(target_func)

        return self.candidate_type
    
    def get_arg_type(self, node) :
        self.neg_file_node = node
        self.arg_check = True
        self.visit(node)

        return self.candidate_type