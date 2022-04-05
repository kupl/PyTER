import ast
import copy
from typing import Iterable
from . import synthesize, extract_info

'''
class NodeIsInstanceMutation(ast.NodeTransformer) :
    def __init__(self, line) :
        self.line = line

        self.func_name = None
        self.mutations = list() # mutation 목록을 list로 준다

    def visit_FunctionDef(self, node) :
        prev = self.func_name
        self.func_name = node.name
        self.generic_visit(node)
        self.func_name = prev

    def visit_Name(self, node) :
        self.generic_visit(node) # 자식 노드 호출 먼저

        if self.line == node.lineno :
            self.mutations.append({"Name" : (node, node.col_offset, self.func_name)})
            
            #var_info = self.func_name['var_info']

            #synthe = synthesizer.Synthesizer(var_info)
            #new_node = synthe.name_synthe(node, self.func_name)
    
    def mutation(self, node) :
        self.visit(node)

        return self.mutations
'''

class IsInstanceMutation() :
    

    def __init__(self, origin, components, var_name, var_typ) :
        self.mutate_list = list()
        self.origin = origin
        self.components = components
        self.var_name = var_name
        self.var_typ = var_typ

    def make_test(self) :
        if_test = None

        if self.var_typ == "None" :
            if_test = ast.Call (
                func=ast.Name (
                    id='isinstance',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Name(id=self.var_name, ctx=ast.Load()),
                    ast.Call(
                        func=ast.Name(
                            id='type',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Name(
                                id=self.var_typ,
                                ctx=ast.Load()
                            )
                        ],
                        keywords=[]
                    )
                ],
                keywords=[]
            )
        
        elif self.var_typ == "method" :
            if_test = ast.Call (
                func=ast.Name (
                    id='callable',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Name(id=self.var_name, ctx=ast.Load())
                ],
                keywords=[]
            )

        elif self.var_typ == "builtin_function_or_method" :
            if_test = ast.Call (
                func=ast.Name (
                    id='isinstance',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Name(id=self.var_name, ctx=ast.Load()),
                    ast.Name(id="types.BuiltinFunctionType", ctx=ast.Load())
                ],
                keywords=[]
            )

        else :
            modify_typ = extract_info.typ_str_modify(self.var_typ)
            if_test = ast.Call (
                func=ast.Name (
                    id='isinstance',
                    ctx=ast.Load()
                ),
                args=[
                    ast.Name(id=self.var_name, ctx=ast.Load()),
                    ast.Name(id=modify_typ, ctx=ast.Load())
                ],
                keywords=[]
            )

        return if_test

    def add_isinstance_stmt(self, stmt_list, i) :
        '''
        i 번째 stmt가 에러가 난 stmt이므로
        i 번째 stmt에 insert를 하면 된다
        일단 lineno 정보 없이 주고 fix_missing 이용
        안되면, lineno 정보 넘기기
        '''
        stmt_hole = ast.Pass()
        setattr(stmt_hole, "hole", True)

        new_node = ast.If(
            test=self.make_test(),
            body=[
                stmt_hole
            ],
            orelse=[
                #ast.Pass(hole=True)
            ],
            mark=True # 찾기 쉽도록 mark 해두기
        )

        stmt_list.insert(i, new_node)

        if self.var_typ == "builtin_function_or_method" :
            import_types_node = ast.Import(
                names=[
                    ast.alias(name='types')
                ]
            )
            stmt_list.insert(i, import_types_node)

        copy_origin = copy.deepcopy(self.origin)
        del stmt_list[i]

        return copy_origin

    def add_isinstance_stmt_else_error(self, stmt_list, i) :
        '''
        i 번째 stmt가 에러가 난 stmt이므로
        i 번째 stmt에 insert를 하면 된다
        일단 lineno 정보 없이 주고 fix_missing 이용
        안되면, lineno 정보 넘기기
        '''
        stmt_hole = ast.Pass()
        setattr(stmt_hole, "hole", True)

        new_node = ast.If(
            test=self.make_test(),
            body=[
                stmt_hole
            ],
            orelse=[
                stmt_list[i]
            ],
            mark=True # 찾기 쉽도록 mark 해두기
        )

        prev_node = stmt_list[i]
        stmt_list[i] = new_node

        if self.var_typ == "builtin_function_or_method" :
            import_types_node = ast.Import(
                names=[
                    ast.alias(name='types')
                ]
            )
            stmt_list.insert(i, import_types_node)

        copy_origin = copy.deepcopy(self.origin)
        stmt_list[i] = prev_node

        return copy_origin

    def add_isinstance_expr(self, node) :
        '''
        i 번째 node가 에러가 난 node이므로
        i 번째 node에 insert를 하면 된다
        일단 lineno 정보 없이 주고 fix_missing 이용
        안되면, lineno 정보 넘기기
        '''
        new_node = ast.IfExp(
            test=self.make_test(),
            body = ast.Constant(value="__expr_hole__"),
            orelse = node.elt,
            mark=True # 찾기 쉽도록 mark 해두기
        )

        prev_node = node.elt
        node.elt = new_node
        copy_origin = copy.deepcopy(self.origin)
        node.elt = prev_node

        return copy_origin

    def find_error_comp_elt(self, node, error_stmt) :
        for child in ast.walk(node) :
            if child is error_stmt :
                for candidate_node in ast.walk(child) :
                    if isinstance(candidate_node, ast.GeneratorExp) :
                        self.mutate_list.append(self.add_isinstance_expr(candidate_node))
                        # 더 이상 수정할 게 없다
                        return
            # For 문 다 돌았으면 여기는 이제 볼 것이 없다

    def insert_isinstance_template(self, node, error_stmt) :    
        '''
        에러가 난 코드를 찾는다
        body 단위로 찾아 (statement 위에 올려야 하니) isinstance를 넣게끔 해야한다
        노드는 수정하여도 object 단위로 넘기는 것이기 때문에 영향을 계속 받는다
        '''    
        # stmt가 더 있으면 탐색
        _fields = node._fields
        for field in _fields :
            attr = getattr(node, field)

            if isinstance(attr, Iterable) :
                for i, child_stmt in enumerate(attr) :
                    if not isinstance(child_stmt, (ast.stmt, ast.mod)) :
                        continue

                    if child_stmt is error_stmt:
                        self.components.extract_components(child_stmt)
                        self.mutate_list.append(self.add_isinstance_stmt(attr, i))
                        self.mutate_list.append(self.add_isinstance_stmt_else_error(attr, i))

                        return True

                    self.insert_isinstance_template(child_stmt, error_stmt)

            elif isinstance(attr, (ast.mod, ast.stmt)) :
                self.insert_isinstance_template(child_stmt, error_stmt)

    def mutate(self, funcname, error_stmt) :
        '''
        어떤 mutate를 할지 결정
        '''
        self.mutate_list = list()

        if funcname == "<genexpr>" :
            self.find_error_comp_elt(self.origin, error_stmt)
        else :
            self.insert_isinstance_template(self.origin, error_stmt)

        return self.mutate_list

class Mutator () :
    '''
    def __init__ (self, file_node, components, var_name, var_typ, ) :
        self.file_node = file_node
        self.components = components
        self.funcname = funcname
        self.lineno = lineno
    '''

    def mutate(self, file_node, components, funcname, var_name, var_typ, error_stmt) :
        node_mutation = IsInstanceMutation(file_node, components, var_name, var_typ)
        mutate_list = node_mutation.mutate(funcname, error_stmt)

        return mutate_list