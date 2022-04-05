'''
Template에 난 hole을 채워주는 synthesizer입니다
'''
import ast
from template.util import Template, FindTemplate
from type_analysis.return_type_inference import ReturnInference
from type_analysis.util import abstract_output_types, is_numpy_type, is_ndarray_type, find_dtype
from synthesizer.util import compare_ast
from mutator.constant_mutate import ConstantMutate

from .util import FindRaise
from copy import deepcopy

class ReturnExtractor(ast.NodeVisitor) :
    def __init__(self, funcname) :
        self.return_expr_list = list()
        self.extract_flag = False
        self.funcname = funcname

    def visit_FunctionDef(self, node) :
        if self.funcname == node.name :
            self.extract_flag = True

        super().generic_visit(node)

        self.extract_flag = False

    def visit_Return(self, node) :
        if self.extract_flag and hasattr(node, 'value') :
            self.return_expr_list.append(node.value)   

    def get_return_expr_list(self, node) :
        self.return_expr_list = list()

        self.visit(node)

        return self.return_expr_list

class TemplateCompeleter(ast.NodeVisitor) :
    '''
    Template 빈 공간 채워주는 노드를 만드는 친구~
    '''
    

    def __init__(self, node, target, filename, funcname, classname, neg_args, pos_func_infos, context_aware, context_score, neg_additional, final, func_patch=False) :
        self.node = node
        self.target = target
        self.filename = filename
        self.funcname = funcname
        self.classname = classname
        self.neg_args = neg_args
        self.pos_func_infos = pos_func_infos
        self.context_aware = context_aware
        self.context_score = context_score
        self.neg_additional = neg_additional
        self.final = final
        self.func_patch = func_patch

        self.complete_list = []

    def extract_return_type(self, skip_arg=None) :
        return_list = list()
        output_types = []
        abs_return_types = abstract_output_types(self.filename, self.classname, self.pos_func_infos)

        infer = ReturnInference(self.target, self.neg_args, self.node, self.pos_func_infos, skip_arg)
        infer_list = infer.get_return_typ_list(self.node)

        output_types.extend(infer_list)

        for output_type in output_types :
            if output_type == 'int' :
                return_list.append(self.make_constant(0))

            if output_type == 'bool' :
                return_list.append(self.make_constant(False))
                return_list.append(self.make_constant(True))

            if output_type == 'str' :
                return_list.append(self.make_constant(""))

            if output_type == 'bytes' :
                return_list.append(self.make_constant(b""))    

            if output_type == 'None' :
                return_list.append(self.make_constant(None))

        extractor = ReturnExtractor(self.funcname)
        return_expr_list = extractor.get_return_expr_list(self.node)

        return_expr_list = deepcopy(return_expr_list)

        return_expr_list.extend(return_list)

        if self.func_patch :
            #print(self.func_patch)
            for return_type in abs_return_types :
                if return_type == 'int' :
                    return_expr_list.append(self.make_constant(0))

                if return_type == 'bool' :
                    return_expr_list.append(self.make_constant(False))
                    return_expr_list.append(self.make_constant(True))

                if return_type == 'str' :
                    return_expr_list.append(self.make_constant(""))

                if return_type == 'bytes' :
                    return_expr_list.append(self.make_constant(b""))    

                if return_type == 'None' :
                    return_expr_list.append(self.make_constant(None))

        return return_expr_list
        #return_list.extend(deepcopy(return_expr_list))
        #return return_list


    def visit_Constant(self, node) :
        if getattr(node, "is_template", False) :
            if node.template_type == Template.Return :
                self.synthesize_return(node.self)
            if node.template_type == Template.TypeCasting :
                self.synthesize_typecasting(node.from_typ, node.to_typ, node.args, node)
            if node.template_type == Template.NoneElse :
                self.synthesize_noneelse(node.else_stmt, node.none_arg)
            if node.template_type in [Template.AddException, Template.NotPos] :
                self.synthesize_basic(target=self.target, arg=node.self)
            if node.template_type in [Template.If, Template.IfElse] :
                self.synthesize_basic(arg=node.self)

    def make_constant(self, value) :
        return ast.Constant(value=value)

    def make_typecasting_call(self, to_typ, args) :
        return ast.Call(
            func=ast.Name(id=to_typ, ctx=ast.Load()),
            args=[args],
            keywords=[]
        )

    def make_typecasting_list(self, args) :
        return ast.List(
            elts=[
                args
            ],
            ctx=ast.Load()
        )

    def make_typecasting_tuple(self, args) :
        return ast.Tuple(
            elts=[
                args
            ],
            ctx=ast.Load()
        )

    def make_typecasting_set(self, args) :
        return ast.Set(
            elts=[
                args
            ]
        )

    def make_typecasting_bytes_to_str(self, args) :
        return ast.Call(
            func=ast.Name(id='str', ctx=ast.Load()),
            args=[
                args,
                ast.Constant(value="utf-8")
            ],
            keywords=[]
        )

    def make_typecasting_numpy(self, to_typ, args) :
        multiple = False
        if 'multiple' in to_typ :
            multiple = True

        dtype = find_dtype(to_typ)

        if multiple :
            arg = ast.Attribute(
                value=ast.Name(id='numpy', ctx=ast.Load()),
                attr=dtype,
                ctx=ast.Load()
            )
        else :
            arg = ast.Constant(
                value=dtype
            )

        return ast.Call(
            func=ast.Attribute(
                value=args,
                attr='astype',
                ctx=ast.Load()
            ),
            args=[
                arg
            ],
            keywords=[]
        )

    def synthesize_basic(self, target=None, arg=None) :
        context_score = self.context_score

        if context_score is None and self.context_aware is not None :
            context_score = self.context_aware.extract_score(target, [self.node])

        if context_score is not None :
            candidates = list(map(lambda x : x[0], context_score))
            candidates = list(dict.fromkeys(candidates))
        else :
            candidates = []

        return_result = list()

        
        return_list = self.extract_return_type()

        #if arg :
        #    return_self = ast.Name(id=arg, ctx=ast.Load())
        #    return_list.append(return_self)

        #for return_expr in return_list :
        #    return_result.append(ast.Return(value=return_expr)) 

        #'''
        for candidate in candidates :
            if isinstance(candidate, ast.Return) :
                return_list = self.extract_return_type()

                if arg :
                    return_self = ast.Name(id=arg, ctx=ast.Load())
                    return_list.append(return_self)

                break

        for return_expr in return_list :
            return_result.append(ast.Return(value=return_expr)) 
        #'''

        return_result = list(dict.fromkeys(return_result))

        if self.context_score is None :
            self.complete_list.extend(return_result)
            return self.complete_list

        candidates = list(dict.fromkeys(candidates))

        if self.final is False :
            self.complete_list.extend(candidates)  
            return self.complete_list

        raise_info = self.neg_additional['raise']
        raise_list = list()
        #print(raise_info)
        if raise_info and raise_info[0] : # raise가 필요한게 있다면...
            for i, raise_id in enumerate(raise_info[0]) :
                if raise_info[1] and raise_info[1][i] != '':
                    raise_stmt = ast.Raise(
                        exc=ast.Call(
                            func=ast.Name(id=raise_id, ctx=ast.Load()),
                            args=[ast.Constant(value=raise_info[1][i])],
                            keywords=[]
                        )
                    )
                else :
                    raise_stmt = ast.Raise(
                        exc=ast.Name(id=raise_id, ctx=ast.Load())
                    )
                raise_list.append(raise_stmt)
                find_raise = FindRaise(self.target, raise_id)
                raise_list.extend(find_raise.get_raise_list(self.node))

        
        #context_score = self.context_aware.extract_score(target, [self.node])

        

        #if not raise_info or not raise_info[0] :
        #    self.complete_list.extend(candidates)
        #    return self.complete_list

        raise_list = list(dict.fromkeys(raise_list))
        raise_result = deepcopy(raise_list)

        for candidate in raise_list :
            mutator = ConstantMutate(candidate, self.neg_additional['constant'])
            mutate_list = mutator.get_mutate_list()

            raise_result.extend(mutate_list)

        
        
        for candidate in candidates :
            if isinstance(candidate, ast.Raise) :
                mutator = ConstantMutate(candidate, self.neg_additional['constant'])
                mutate_list = mutator.get_mutate_list()

                raise_result.extend(mutate_list)

        self.complete_list.extend(raise_result)    

        #self.complete_list.append(ast.Name(id=arg, ctx=ast.Load()))

        return self.complete_list

    def synthesize_return(self, arg) :
        '''
        Todo :
        function return type을 받아와서 기본 값 리턴하기
        같은 함수 return statement 이용
        '''
        context_score = self.context_score
        if context_score is None and self.context_aware is not None :
            context_score = self.context_aware.extract_score(self.target, [self.node])

        if context_score is not None :
            candidates = list(map(lambda x : x[0], context_score))
            candidates = list(dict.fromkeys(candidates))
        else :
            candidates = []

        return_list = self.extract_return_type(arg)

        for candidate in candidates :
            if isinstance(candidate, ast.Return) :
                return_self = ast.Name(id=arg, ctx=ast.Load())
                return_list.append(return_self)

                break

        for return_expr in return_list :
            self.complete_list.append(return_expr)

        return self.complete_list
    
    def synthesize_typecasting(self, from_typ, to_typ, args, node) :
        '''
        Todo :
        이거도 잘 해야대는데 ㅋ
        '''

        #print(to_typ) # 여서 numpy.ndarray<datetime64 로 뒤에 > 이게 잘림 
        if args == 'constant' :
            mutator = ConstantMutate(node, self.neg_additional['constant'])
            mutate_list = mutator.get_mutate_list()

            self.complete_list.extend(mutate_list)

        elif to_typ == "List" :
            self.complete_list.append(self.make_typecasting_list(args))
        elif to_typ == "Tuple" :
            self.complete_list.append(self.make_typecasting_tuple(args))
        elif to_typ == "Set" :
            self.complete_list.append(self.make_typecasting_set(args))
        elif is_numpy_type(to_typ) : # numpy type casting
            self.complete_list.append(self.make_typecasting_numpy(to_typ, args))
        elif from_typ == 'bytes' and to_typ == 'str' : # bytes -> str type casting
                self.complete_list.append(self.make_typecasting_bytes_to_str(args))
        else :
            if to_typ.find('.') == -1 :
                to_typ = to_typ.lower()
            self.complete_list.append(self.make_typecasting_call(to_typ, args))

    def synthesize_noneelse(self, else_stmt, node_arg) :
        expr_list = list()
        
        for node in ast.walk(else_stmt) :
            if isinstance(node, ast.expr) :
                flag = False
                for in_node in ast.walk(node) :
                    if ast.unparse(in_node) == node_arg : # None이었던 변수를 안쓰게끔
                        flag = True
                        break
                
                if flag :
                    continue

                expr_list.append(node)

        self.complete_list.extend(expr_list)

    def get_complete_list(self, node) :
        self.complete_list = []
        self.visit(node)

        return self.complete_list

class TemplateInserter(ast.NodeTransformer) :
    def __init__(self) :
        self.template = None
        self.target = None

    def visit_Constant(self, node) :
        if node is self.target :
            return self.template
        if self.template is None and getattr(node, "is_template", False) :
            self.template = node
            return self.insert_node

        

        return node

    def generic_visit(self, node) :
        if node is self.target :
            return self.template
        
        return super().generic_visit(node)
        
        #return node

    def modify_node(self, insert_node, node) :
        self.insert_node = insert_node
        self.template = None
        self.target = None
        node = self.generic_visit(node)

        return self.template, node

    def revert_node(self, template, target, node) :
        self.template = template
        self.target = target
        node = self.generic_visit(node)

        return node



class TemplateSynthesizer(ast.NodeTransformer) :
    def __init__(self, validator, filename, funcname, classname, neg_args, pos_func_infos, context_aware, context_score, neg_additional, test, total_test_num, final, func_patch=False) :
        self.validator = validator
        self.filename = filename
        self.funcname = funcname
        self.classname = classname
        self.neg_args = neg_args
        self.pos_func_infos = pos_func_infos
        self.context_aware = context_aware
        self.context_score = context_score
        self.neg_additional = neg_additional
        self.test = test
        self.total_test_num = total_test_num
        self.final = final
        self.func_patch = func_patch

    def validation(self, node, target) :
        self.validator.validate(node, self.filename, target, self.test, self.total_test_num)

    def template_synthesize(self, node) :
        find_template = FindTemplate()
        targets = find_template.get_target(node)

        '''
        print("Targets")
        for target in targets :
            target = ast.fix_missing_locations(target)
            print(ast.unparse(target))
            #print(ast.dump(target, indent=4))
        input()
        '''
        

        result = list()
        for target in targets :
            completer = TemplateCompeleter(node, target, self.filename, self.funcname, self.classname, self.neg_args, self.pos_func_infos, self.context_aware, self.context_score, self.neg_additional, self.final, self.func_patch)
            complete_list = completer.get_complete_list(target)

            no_add = False

            for child in ast.walk(target) :
                if isinstance(child, ast.Constant) and child.value == '<pyfix_template>' :
                    no_add = True

            if not no_add :
                complete_list = [target] + complete_list

            '''
            for c in complete_list :
                print(c)
                print(ast.unparse(ast.fix_missing_locations(c)))

            input()    
            '''

            def remove_duplicates(lst):
                lst = list(filter(lambda x: not (isinstance(x, ast.Constant) and x.value == '<pyfix_template>'), lst))
                seen = set()
                res = []
                for x in lst:
                    not_add = False
                    for y in seen :
                        if compare_ast(x, y) :
                            not_add = True
                            break

                    if not_add :
                        continue
                    res.append(x)
                    seen.add(x)
                return res

            complete_list = remove_duplicates(complete_list)
            #print(complete_list)
            #input()
            result.append(complete_list)
        inserter = TemplateInserter()

        #print("result : ",result)
        #input()

        

        is_all_skip = True
        skip_list = list()
        for i, r in enumerate(result) :
            if r :
                is_all_skip = False
            else :
                r.append('empty')

        #print(is_all_skip)

        if is_all_skip :
            #print("IfNoneCheck Synthesize")
            targets = find_template.get_target(node)
            #print(target)
            #target = target[0] # 패치결과가 없는거는 single? 전혀아님
            self.validation(node, targets)
            return

        import itertools
        for completes in itertools.product(*result) :
            if None in completes :
                continue 
            #print(completes)
            templates = list()

            complete_num = 0
            for i, complete in enumerate(completes) :
                if complete == 'empty' :
                    continue
                    
                template, target = inserter.modify_node(complete, targets[i])

                templates.append(template)
                targets[i] = target
                complete_num += 1

            import copy
            final_node = ast.fix_missing_locations(copy.deepcopy(node))
            targets = find_template.get_target(final_node)

            #input()

            #print("do validate")
            self.validation(final_node, targets)

            # 돌려놓기
            for i, template in enumerate(templates) :
                if template is None :
                    continue
                target = inserter.revert_node(template, completes[i], node)
            targets = find_template.get_target(node)


        