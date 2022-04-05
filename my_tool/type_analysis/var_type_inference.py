import ast
from .util import FindTargetFunc, abstract_type_list, abstract_type, dict_output_type, get_type_list
from . import custom_type_system
from copy import copy

class VarTypeInference(ast.NodeVisitor) :
    def __init__(self, target_var, neg_infos, origin, skip_var=[], infer_type_dict={}, is_arg=False) :
        self.target_var = target_var
        self.neg_infos = copy(neg_infos)
        self.find_var = False
        self.candidate_type = dict()
        self.origin = origin
        self.skip_var = skip_var
        self.infer_type_dict = infer_type_dict
        self.should_check = False
        self.arg_check = False

        self.env = dict()
        self.k = 50

        self.is_arg = is_arg

    def find_variables(self, node) :
        all_cands = []
        if isinstance(node, (ast.Attribute, ast.Subscript, ast.Name)) :
            return [node]
        for child in ast.iter_child_nodes(node) :
            if isinstance(child, ast.BoolOp) :
                for value in child.values :
                    cands = self.find_variables(value)
                    all_cands.extend(cands)

            if isinstance(child, ast.BinOp) :
                cands1 = self.find_variables(child.left)
                cands2 = self.find_variables(child.right)
                all_cands.extend(cands1 + cands2)

            if isinstance(child, ast.UnaryOp) :
                cands = self.find_variables(child.operand)
                all_cands.extend(cands)

            if isinstance(child, ast.IfExp) :
                cands1 = self.find_variables(child.body)
                cands2 = self.find_variables(child.orelse)
                all_cands.extend(cands1 + cands2)

            if isinstance(child, ast.Compare) :
                cands = self.find_variables(child.left)
                all_cands.extend(cands)

                for comparator in child.comparators :
                    cands = self.find_variables(comparator)
                    all_cands.extend(cands)

            if isinstance(child, (ast.Attribute, ast.Subscript, ast.Name)) :
                all_cands.append(child)

        return all_cands

    def add_dict(self, name, typs) :
        typ_dict = self.env.get(name, dict()) 

        for typ, num in typs.items() :
            typ_dict[typ] = min(typ_dict.get(typ, 0) + 1, self.k)

    def add_list(self, name, typs) :
        typ_dict = self.env.get(name, dict()) 

        for typ in set(typs) :
            typ_dict[typ] = min(typ_dict.get(typ, 0) + 1, self.k)

    def visit_For(self, node) :
        if isinstance(node.iter, (ast.Name, ast.Attribute, ast.Subscript)) :
            name = ast.unparse(node.iter)
            iterable_typs = ['str', 'List', 'Set', 'Tuple']

            self.add_list(name, iterable_typs)

        self.generic_visit(node)

    def visit_AugAssign(self, node) :
        value_typs = self.visit(node.value)
        cands = self.find_variables(node.value)

        if isinstance(node.target, (ast.Name, ast.Attribute, ast.Subscript)) :
            name = ast.unparse(node.target)
            name_typ = self.env.get(name, dict())
            if value_typs : 
                self.add_list(name, value_typs)
                self.add_dict(name, name_typ)

            for cand in cands :
                cand_name = ast.unparse(cand)
                name_typ = self.env.get(name, dict())
                self.add_dict(cand_name, name_typ)

    def visit_Assign(self, node) :
        value_typs = self.visit(node.value)
        cands = self.find_variables(node.value)

        if len(node.targets) == 1 and isinstance(node.targets[0], (ast.Name, ast.Attribute, ast.Subscript)) :
            name = ast.unparse(node.targets[0])
            if value_typs : 
                self.add_list(name, value_typs)

            for cand in cands :
                name = ast.unparse(cand)
                name_typ = self.env.get(name, dict())
                self.add_dict(name, name_typ)

    def visit_Call(self, node) :
        self.generic_visit(node)

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
                arg_name = ast.unparse(node.args[0])
                if isinstance(arg_name, (ast.Name, ast.Attribute, ast.Subscript)) :
                    if isinstance(node.args[1], (ast.Name, ast.Attribute)) :
                        typ = ast.unparse(node.args[1])
                        if typ in ['list', 'tuple', 'dict', 'set'] :
                            typ = typ.title()
                        self.add_list(arg_name, [typ])
                    elif isinstance(node.args[1], ast.Tuple) :
                        for elt in node.args[1].elts :
                            if isinstance(elt, (ast.Name, ast.Attribute)) :
                                typ = ast.unparse(node.args[1])
                                if typ in ['list', 'tuple', 'dict', 'set'] :
                                    typ = typ.title()
                                self.add_list(arg_name, [typ])
            



        #self.generic_visit(node)
        #self.find_var = prev_find

        return []
        

    def visit_JoinedStr(self, node) :
        self.generic_visit(node)

        return ["str"]

    def visit_List(self, node) :
        self.generic_visit(node)
        return ['List']

    def visit_ListComp(self, node) :
        self.generic_visit(node)
        return ['List']

    def visit_Tuple(self, node) :
        self.generic_visit(node)
        return ['Tuple']

    def visit_Dict(self, node) :
        self.generic_visit(node)
        return ['Dict']

    def visit_DictComp(self, node) :
        self.generic_visit(node)
        return ['Dict']

    def visit_Set(self, node) :
        self.generic_visit(node)
        return ['Set']

    def visit_SetComp(self, node) :
        self.generic_visit(node)
        return ['Set']

    def visit_Subscript(self, node) :
        self.visit(node.slice)

        value = node.value
        value_typs = self.env.get(ast.unparse(node.value), None)
        cand_typ = []
        if value_typs :
            for value_typ in value_typs.keys() :
                if 'Dict' == abstract_type(value_typ) :
                    output = dict_output_type(value_typ)
                    if output :
                        typ_list = get_type_list(output)
                        cand_typ.extend(typ_list)

        self.visit(node.value)
        cands = self.find_variables(node.value)
        for cand in cands :
            idx = node.slice
            if isinstance(idx, (ast.Name, ast.Attribute, ast.Subscript)) :
                neg_typs = self.env.get(ast.unparse(idx), dict())
                neg_typs = abstract_type_list(list(neg_typs.keys()))

                candidate = set([])
                for neg_typ in neg_typs :
                    if 'int' in neg_typ :
                        candidate.update(custom_type_system.iterable)

                if not candidate :
                    candidate.add('Dict')

                self.add_list(ast.unparse(cand), list(candidate))

            else :
                candidate = custom_type_system.iterable
                self.add_list(ast.unparse(cand), list(candidate))

        return cand_typ

    def visit_BoolOp(self, node) :
        cands_list = []
        typs_list = []
        result_typs = []
        for i, value in enumerate(node.values) :
            typs = self.visit(value)
            if not typs :
                typs = []
            typs_list.append(typs)
            result_typs.extend(typs)

            cands = self.find_variables(value)
            cands_list.append(cands)

        for i, cands in enumerate(cands_list) :
            all_typs = []
            for j, typs in enumerate(typs_list) :
                if i == j :
                    continue
                all_typs.extend(typs)

            for cand in cands :
                self.add_list(ast.unparse(cand), all_typs)


        if isinstance(node, ast.Or) :
            return result_typs
        else :
            return ['bool']

    def visit_UnaryOp(self, node) :
        return self.visit(node.operand)

    def visit_BinOp(self, node) :
        numeric_op = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv)
        real_op = (ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv)
        bool_op = (ast.BitOr, ast.BitXor, ast.BitAnd)

        left_typs = self.visit(node.left)
        if not left_typs :
            left_typs = []

        right_typs = self.visit(node.right)
        if not right_typs :
            right_typs = []


        left_cands = self.find_variables(node.left)
        right_cands = self.find_variables(node.right)

        is_iterable_cal = False

        for cand in left_cands :
            if right_typs in [['List'], ['Tuple']] and isinstance(node.op, ast.Mult):
                is_iterable_cal = right_typs

            name = ast.unparse(cand)
            #if isinstance(node.op, bool_op) :
            #    self.add_list(name, ['bool'])
            if isinstance(node.op, real_op) :
                self.add_list(name, ['int'])
            self.add_list(name, right_typs)

        for cand in right_cands :
            if left_typs in [['List'], ['Tuple']] and isinstance(node.op, ast.Mult):
                is_iterable_cal = left_typs

            name = ast.unparse(cand)
            #if isinstance(node.op, bool_op) :
            #    self.add_list(name, ['bool'])
            if isinstance(node.op, real_op) :
                self.add_list(name, ['int'])
            self.add_list(name, left_typs)
            
        if is_iterable_cal :
            return is_iterable_cal

        #if isinstance(node.op, bool_op) :
        #    left_typs.append('bool')
        return left_typs + right_typs

    def visit_Compare(self, node) :
        result_typs = []
        isin = False

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
        if not left_typs :
            left_typs = []
        left_cands = self.find_variables(node.left)

        cands_list = [left_cands]
        typs_list = [left_typs]
        result_typs = []
        for i, value in enumerate(node.comparators) :
            typs = self.visit(value)
            if not typs :
                typs = []
            if isinstance(node.ops[i], (ast.In, ast.NotIn)) :
                isin = True
                iterable_typs = ['str', 'List', 'Set', 'Tuple']
                typs.extend(iterable_typs)
            typs_list.append(typs)
            result_typs.extend(typs)

            cands = self.find_variables(value)
            cands_list.append(cands)

            

        for i, cands in enumerate(cands_list) :
            all_typs = []
            for j, typs in enumerate(typs_list) :
                if i == j :
                    continue
                all_typs.extend(typs)

            for cand in cands :
                self.add_list(ast.unparse(cand), all_typs)

        #if isin :
        #    result_typs = ['bool']
        #else :
        #    result_typs.append('bool')

        return result_typs

    def visit_IfExp(self, node) :
        left_typs = self.visit(node.body)
        if not left_typs :
            left_typs = []

        right_typs = self.visit(node.orelse)
        if not right_typs :
            right_typs = []


        left_cands = self.find_variables(node.body)
        right_cands = self.find_variables(node.orelse)

        for cand in left_cands :
            name = ast.unparse(cand)
            self.add_list(name, right_typs)

        for cand in right_cands :
            name = ast.unparse(cand)
            self.add_list(name, left_typs)
            
        return left_typs + right_typs


    def visit_Name(self, node) :
        typ_dict = self.env.get(ast.unparse(node), dict())
        typ_list = []

        for typ, num in typ_dict.items() :
            typs = [typ] * num
            typ_list.extend(typs)

        typ_list = abstract_type_list(typ_list)

        return typ_list

    def visit_Attribute(self, node) :
        typ_dict = self.env.get(ast.unparse(node), dict())
        typ_list = []

        for typ, num in typ_dict.items() :
            typs = [typ] * num
            typ_list.extend(typs)

        typ_list = abstract_type_list(typ_list)

        return typ_list

    def visit_Constant(self, node) :
        typ = type(node.value).__name__
        if typ == 'NoneType' :
            typ = 'None'
        return [typ]


    def get_var_type(self, node) :
        self.neg_file_node = node
        find_func = FindTargetFunc(self.target_var)
        target_func = find_func.get_func(node)

        for name, typs in self.neg_infos.items() :
            if name == ast.unparse(self.target_var) :
                self.env[name] = dict()
                continue
            typ_dict = dict()
            typs = abstract_type_list(typs)
            for typ in typs :
                typ_dict[typ] = 1
            self.env[name] = typ_dict

        empty_count = 0
        max_count = 0

        prev_typ_dict = dict()
        for var, typ_dict in self.env.items() :
            prev_typ_dict[var] = set(typ_dict.keys())

        #print(ast.unparse(self.target_var))
        while True :
            if empty_count > 3 or max_count > 10 :
                break
            self.visit(target_func)

            typ_dict = self.env.get(ast.unparse(self.target_var), dict())

            if not typ_dict :
                empty_count += 1
            else :
                empty_count = 0

            
            cur_typ_dict = dict()
            for var, type_dict in self.env.items() :
                cur_typ_dict[var] = set(type_dict.keys())

            is_break = False
            if prev_typ_dict == cur_typ_dict :
                result_typs = dict()
                
                typ_sort = sorted(typ_dict.items(), key=lambda x: x[1], reverse=True)
                for typ, num in typ_sort :
                    result_typs[typ] = num

                return result_typs

            prev_typ_dict = cur_typ_dict
            max_count += 1
        
        return dict()
    
    def get_arg_type(self, node) :
        self.neg_file_node = node
        self.arg_check = True

        for name, typs in self.neg_infos.items() :
            if name == ast.unparse(self.target_var) :
                self.env[name] = dict()
                continue
            typ_dict = dict()
            for typ in typs :
                typ_dict[typ] = 1
            self.env[name] = typ_dict

        empty_count = 0
        max_count = 0

        prev_typ_dict = dict()
        for var, typ_dict in self.env.items() :
            prev_typ_dict[var] = set(typ_dict.keys())

        while True :
            if empty_count > 3 or max_count > 10 :
                break
            self.visit(node)

            typ_dict = self.env.get(ast.unparse(self.target_var), dict())

            if not typ_dict :
                empty_count += 1
            else :
                empty_count = 0

            cur_typ_dict = dict()
            for var, type_dict in self.env.items() :
                cur_typ_dict[var] = set(type_dict.keys())

            is_break = False
            if prev_typ_dict == cur_typ_dict :
                result_typs = dict()
                
                typ_sort = sorted(typ_dict.items(), key=lambda x: x[1], reverse=True)
                for typ, num in typ_sort :
                    result_typs[typ] = num

                return result_typs

            prev_typ_dict = cur_typ_dict
            max_count += 1
        
        return dict()