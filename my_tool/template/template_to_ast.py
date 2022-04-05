'''
template을 실제 ast node로 변환하는 파일입니다.

Constant(value="<template_return>")
Constant(value="<template_typecasting_[from_typ]_[to_typ]>)



'''
from .util import Template, TemplateMethod, NONE_PATCH, get_template_method
import ast
import copy
from synthesizer.add_exception import AddException
from typing import Iterable
from type_analysis.util import abstract_type, abstract_dtype, is_numpy_type, is_ndarray_type, find_dtype, FindVarType
from .util import typ_str_modify, abc_to_typ, FindNoneElseTarget, ChangeNode
from .body_analysis import BodyAnalysis
from .usage_analysis import UsageAnalysis

from type_analysis.error_analysis import ErrorAnalysis 


from itertools import product

class MakeTemplate() :
    

    def __init__(self, origin, arg, arg_typs, arg_typ_info, arg_template, neg_args, pos_func_infos) :
        '''
        arg_typ : argument가 negative에서 보인 typ
        arg_typ_info : argument가 positive에서 보인 typ scoring 한거
        '''

        self.origin = origin
        self.arg = arg
        self.arg_typs = arg_typs
        self.arg_typ_info = arg_typ_info
        self.arg_template = arg_template
        self.neg_args = neg_args
        self.pos_func_infos = pos_func_infos
    
        self.ast_list = list()
        self.should_add_import = False

    def none_type_casting(self, to_type) :
        to_type = abstract_type(to_type)

        if to_type == "int" :
            return ast.Constant(value=0)

        if to_type == "bool" :
            return ast.Constant(value=False)

        if to_type == "str" :
            return ast.Constant(value="")

        if to_type == "bytes" :
            return ast.Constant(value=b"")

        if to_type == "List" :
            return ast.List(elts=[], ctx=ast.Load())

        if to_type == "Tuple" :
            return ast.Call(
                func=ast.Name(id='tuple', ctx=ast.Load()),
                args=[],
                keywords=[]
            )

        if to_type == "Dict" :
            return ast.Dict(keys=[], values=[], ctx=ast.Load())

        if to_type == "Set" :
            return ast.Call(
                func=ast.Name(id='set', ctx=ast.Load()),
                args=[],
                keywords=[]
            )

        
        #print("None Type Casting Other Type")
        #print("Type : ", to_type)
        
        return ast.Call(
            func=ast.Name(id=to_type, ctx=ast.Load()),
            args=[],
            keywords=[]
        )

    '''
    Template to AST
    '''

    def arg_to_ast(self, arg) :
        dot_place = arg.rfind('.')
        if dot_place != -1 : # attribute임
            attr = arg[dot_place+1:]

            return ast.Attribute(
                value=self.arg_to_ast(arg[:dot_place]),
                attr=attr,
                ctx=ast.Load()
            )
        else : # name임
            return ast.Name(
                id=arg,
                ctx=ast.Load()
            )

    def return_to_ast(self, arg) :
        return_ast = ast.Return(
            value = ast.Constant(value='<pyfix_template>', is_template=True, template_type=Template.Return, self=arg)
        )

        return return_ast

    def type_casting_to_ast(self, arg, from_typ, to_typ) :
        arg_ast = self.arg_to_ast(arg)

        # target은 ctx가 store여야함
        target_arg_ast = copy.deepcopy(arg_ast)
        target_arg_ast.ctx = ast.Store()

        if from_typ == "None" :
            type_casting_func = self.none_type_casting(to_typ)
        else :
            to_typ = abc_to_typ(to_typ)
            type_casting_func = ast.Constant(value='<pyfix_template>', args=arg_ast,
                    is_template=True, template_type=Template.TypeCasting, from_typ=from_typ, to_typ=to_typ)

        type_casting_ast = ast.Assign(
            targets=[target_arg_ast],
            value=type_casting_func
        )   

        return type_casting_ast

    def if_none_check_to_ast(self, arg, if_stmt) :
        if_stmt.test = ast.BoolOp(op=ast.And(), values=[self.arg_to_ast(arg), if_stmt.test])

        return if_stmt


    '''
    Make AST
    '''

    def make_test(self, arg_typ) :
        if_test = None

        if arg_typ == "None" :
            if_test = ast.Call (
                func=ast.Name (
                    id='isinstance',
                    ctx=ast.Load()
                ),
                args=[
                    self.arg_to_ast(self.arg),
                    ast.Call(
                        func=ast.Name(
                            id='type',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Name(
                                id=arg_typ,
                                ctx=ast.Load()
                            )
                        ],
                        keywords=[]
                    )
                ],
                keywords=[]
            )
        
        #elif arg_typ == "method" :
        #    if_test = ast.Call (
        #        func=ast.Name (
        #            id='callable',
        #            ctx=ast.Load()
        #        ),
        #        args=[
        #            self.arg_to_ast(self.arg),
        #        ],
        #        keywords=[]
        #    )

        elif arg_typ == "builtin_function_or_method" :
            if_test = ast.Call (
                func=ast.Name (
                    id='isinstance',
                    ctx=ast.Load()
                ),
                args=[
                    self.arg_to_ast(self.arg),
                    ast.Name(id="types.BuiltinFunctionType", ctx=ast.Load())
                ],
                keywords=[]
            )
        
        
        #elif "::" in arg_typ: # issubclass
        #    split_type = arg_typ.split("::")
        #    if_test = ast.Call (
        #        func=ast.Name(
        #            id='issubclass',
        #            ctx=ast.Load()
        #        ),
        #        args=[
        #            ast.Attribute(
        #                value=self.arg_to_ast(self.arg),
        #                attr='__class__',
        #                ctx=ast.Load()
        #            ),
        #            ast.Name(id=split_type[1], ctx=ast.Load())
        #        ],
        #        keywords=[]
        #    )

        elif is_ndarray_type(arg_typ) :
            dtype = find_dtype(arg_typ)

            if "multiple" in arg_typ :
                dtype_test = ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='numpy', ctx=ast.Load()),
                            attr='issubdtype',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Attribute(
                                value=self.arg_to_ast(self.arg),
                                attr='dtype',
                                ctx=ast.Load()
                            ),
                            ast.Attribute(
                                value=ast.Name(id="numpy", ctx=ast.Load()),
                                attr=abstract_dtype(dtype),
                                ctx=ast.Load()
                            )
                        ],
                        keywords=[]
                    )
            else :
                dtype_test = ast.Compare(
                        left=ast.Attribute(
                            value=ast.Attribute(
                                value=self.arg_to_ast(self.arg),
                                attr='dtype',
                                ctx=ast.Load()
                            ),
                            attr='type',
                            ctx=ast.Load()
                        ),
                        ops=[
                            ast.Is()
                        ],
                        comparators=[
                            ast.Attribute(
                                value=ast.Name(id="numpy", ctx=ast.Load()),
                                attr=abstract_dtype(dtype),
                                ctx=ast.Load()
                            )
                        ]
                    )
            
            if_test = ast.BoolOp(
                op=ast.And(),
                values=[
                    ast.Call(
                        func=ast.Name (
                            id='isinstance',
                            ctx=ast.Load()
                        ),
                        args=[
                            self.arg_to_ast(self.arg),
                            ast.Attribute(
                                value=ast.Name(id="numpy", ctx=ast.Load()),
                                attr='ndarray',
                                ctx=ast.Load()
                            )
                        ],
                        keywords=[]
                    ),
                    dtype_test
                ]
            )

        elif is_numpy_type(arg_typ) :
            dtype = find_dtype(arg_typ)

            if "multiple" in arg_typ :
                dtype_test = ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id='numpy', ctx=ast.Load()),
                            attr='issubdtype',
                            ctx=ast.Load()
                        ),
                        args=[
                            ast.Attribute(
                                value=self.arg_to_ast(self.arg),
                                attr='dtype',
                                ctx=ast.Load()
                            ),
                            ast.Attribute(
                                value=ast.Name(id="numpy", ctx=ast.Load()),
                                attr=abstract_dtype(dtype),
                                ctx=ast.Load()
                            )
                        ],
                        keywords=[]
                    )
            else :
                dtype_test = ast.Compare(
                        left=ast.Attribute(
                            value=ast.Attribute(
                                value=self.arg_to_ast(self.arg),
                                attr='dtype',
                                ctx=ast.Load()
                            ),
                            attr='type',
                            ctx=ast.Load()
                        ),
                        ops=[
                            ast.Is()
                        ],
                        comparators=[
                            ast.Attribute(
                                value=ast.Name(id="numpy", ctx=ast.Load()),
                                attr=abstract_dtype(dtype),
                                ctx=ast.Load()
                            )
                        ]
                    )
            
            if_test = dtype_test

        else :
            modify_typ = typ_str_modify(arg_typ)

            if_test = ast.Call (
                func=ast.Name (
                    id='isinstance',
                    ctx=ast.Load()
                ),
                args=[
                    self.arg_to_ast(self.arg),
                    ast.Name(id=modify_typ, ctx=ast.Load())
                ],
                keywords=[]
            )

        return if_test

    def add_template_info(self, template, method, template_info_list) :
        template_info = dict()
        template_info['template'] = copy.deepcopy(template)
        template_info['method'] = method
        template_info_list.append(template_info)

    def add_template(self, arg_typ, template, stmt_list, i) :
        template_info_list = list()

        # Subclass
        
        #if template == Template.SubClass :
        #    return template_info_list

        '''
        split_typ = arg_typ.split("::")
        if len(split_typ) < 2 :
            return template_info_list
            
        body = self.type_casting_to_ast(self.arg, split_typ[0], split_typ[1])

        new_node = ast.If(
            test=self.make_test(arg_typ),
            body=[
                body
            ],
            orelse=[],
            mark=True
        )

        self.add_template_info(new_node, TemplateMethod.Add, template_info_list)
        '''

        if template == Template.InLoopContinue :
            test = self.make_test(arg_typ)
            new_node = ast.If(
                test=test,
                body=[
                    ast.Continue()
                ],
                orelse =[],
                mark = True
            )

            self.add_template_info(new_node, TemplateMethod.Add, template_info_list)

        if template == Template.InLoopBreak :
            test = self.make_test(arg_typ)
            new_node = ast.If(
                test=test,
                body=[
                    ast.Continue()
                ],
                orelse =[],
                mark = True
            )

            self.add_template_info(new_node, TemplateMethod.Add, template_info_list)

        if template == Template.TypeCasting :
            if not self.arg_typ_info : # casting type이 비어있으면
                return template_info_list

            for to_typ in self.arg_typ_info.keys() :
                body = self.type_casting_to_ast(self.arg, arg_typ, to_typ)

                new_node = ast.If(
                    test=self.make_test(arg_typ),
                    body=[
                        body
                    ],
                    orelse=[
                        #ast.Pass(hole=True)
                    ],
                    mark=True # 찾기 쉽도록 mark 해두기
                )

                self.add_template_info(new_node, TemplateMethod.Add, template_info_list)

        if template == Template.Return :
            body = self.return_to_ast(self.arg)

            new_node = ast.If(
                test=self.make_test(arg_typ),
                body=[
                    body
                ],
                orelse=[
                    #ast.Pass(hole=True)
                ],
                mark=True # 찾기 쉽도록 mark 해두기
            )

            self.add_template_info(new_node, TemplateMethod.Add, template_info_list)

        # Baisc Template
        if template == Template.If :
            new_node = ast.If(
                test=self.make_test(arg_typ),
                body=[
                    ast.Constant(value='<pyfix_template>', is_template=True, template_type=Template.If, self=self.arg)
                ],
                orelse=[
                    #ast.Pass(hole=True)
                ],
                mark=True # 찾기 쉽도록 mark 해두기
            )

            self.add_template_info(new_node, TemplateMethod.Add, template_info_list)

        return template_info_list

    def replace_template(self, arg_typ, template, stmt_list, i) :
        template_info_list = list()

        # 단순 None Check Template (if 문 생성)
        if template == Template.NoneCheck :
            #body = BodyAnalysis(stmt_list[i])
            #body_end = body.get_body_end(stmt_list, i)

            new_node = ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=self.make_test(arg_typ)
                ),
                body=[
                    stmt_list[i]
                ],
                orelse=[
                    #ast.Pass(hole=True)
                ],
                mark=True # 찾기 쉽도록 mark 해두기
            )

            self.add_template_info(new_node, TemplateMethod.Replace, template_info_list)

                # not을 삽입하여 skip하는 템플릿
        if template == Template.Skip :
            new_node = ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=self.make_test(arg_typ)
                ),
                body=[
                    stmt_list[i]
                ],
                orelse=[
                    #ast.Pass(hole=True)
                ],
                mark=True # 찾기 쉽도록 mark 해두기
            )

            self.add_template_info(new_node, TemplateMethod.Replace, template_info_list)



        if template == Template.IfElse :
            new_node = ast.If(
                test=self.make_test(arg_typ),
                body=[
                    ast.Constant(value='<pyfix_template>', is_template=True, template_type=Template.IfElse, self=self.arg)
                ],
                orelse=[
                    stmt_list[i]
                ],
                mark=True # 찾기 쉽도록 mark 해두기
            )

            self.add_template_info(new_node, TemplateMethod.Replace, template_info_list)


        if template == Template.OpMutate :
            (op_node, ops) = self.arg_typ_info # 얘만 좀 특별
            
            prev_op = op_node.op
            for op in ops :
                op_node.op = op()
                mutate_node = copy.deepcopy(stmt_list[i])
                op_node.op = prev_op

                new_node = new_node = ast.If(
                    test=self.make_test(arg_typ),
                    body=[
                        mutate_node
                    ],
                    orelse=[
                        stmt_list[i]
                    ],
                    mark=True # 찾기 쉽도록 mark 해두기
                )

                self.add_template_info(new_node, TemplateMethod.Replace, template_info_list)

        return template_info_list

    def modify_template(self, arg_typ, template, stmt_list, i) :
        template_info_list = list()

        # 단순 None Check Template (if 문에 껴넣기)
        if template == Template.IfNoneCheck : 
            prev = stmt_list[i]
            if_stmt_copy = copy.deepcopy(stmt_list[i])
            stmt_list[i] = self.if_none_check_to_ast(self.arg, if_stmt_copy)
            setattr(stmt_list[i], 'mark', True)

            self.add_template_info(stmt_list[i], TemplateMethod.Modify, template_info_list)

            # else문 체크해줘야해
            # 왜? none인걸 쓸수도 있으니...
            usage = UsageAnalysis(self.arg)

            for j, stmt in enumerate(stmt_list[i].orelse) :
                should_fix, target_stmt = usage.get_stmt(stmt)
                if should_fix is True :
                    #print(ast.dump(stmt))
                    error_analysis = ErrorAnalysis(self.neg_args, self.origin, self.pos_func_infos)
                    var_score, _ = error_analysis.extract_score(target_stmt)

                    for node, type_info in var_score.items() :
                        if not ast.unparse(node) == self.arg :
                            continue

                        templates = NONE_PATCH

                        for template in templates :
                            #print("else_template", template)
                            #print(self.arg)
                            #input()

                            #make_template = MakeTemplate(stmt_list[i].orelse, self.arg, 'None', type_info, [('None', template)], self.neg_args, self.pos_func_infos)
                            make_template = MakeTemplate(stmt_list[i].orelse, self.arg, 'None', type_info, [('None', template)], self.neg_args, self.pos_func_infos)
                            else_ast_list = make_template.single_template(stmt_list[i].orelse, j)

                            #print(else_ast_list)
                            for else_node in else_ast_list :
                                prev = stmt_list[i].orelse
                                stmt_list[i].orelse = else_node

                                #else_node = ast.fix_missing_locations(else_node)
                                
                                self.add_template_info(stmt_list[i], TemplateMethod.Modify, template_info_list)

                                stmt_list[i].orelse = prev
                    break
                elif should_fix is False :
                    break 

            stmt_list[i] = prev


        if template == Template.NoneElse :
            #origin_stmt = stmt_list[i]
            copy_stmt = stmt_list[i]

            find = FindNoneElseTarget(self.arg)
            target = find.get_target(copy_stmt)

            if target is None : # none else 할게 없음
                return template_info_list

            stmt_list[i] = copy_stmt

            new_node = ast.IfExp(
                    test=self.make_test(arg_typ),
                    body=ast.Constant(value='<pyfix_template>', is_template=True, template_type=Template.NoneElse, else_stmt=target, none_arg=self.arg),
                    orelse=copy.deepcopy(target),
                    mark=True # 찾기 쉽도록 mark 해두기
                )

            change = ChangeNode(target, new_node)
                
            change.get_node(copy_stmt)
            new_stmt = copy.deepcopy(copy_stmt)
            self.add_template_info(new_stmt, TemplateMethod.Modify, template_info_list)
            change.revert_node(copy_stmt)

            if self.arg_typ_info :
                for to_typ in self.arg_typ_info.keys() :
                    to_typ = abc_to_typ(to_typ)
                    to_typ = abc_to_typ(list(self.arg_typ_info.keys())[0])

                    # to_typ이 있으면 그거 활용
                    new_node = ast.IfExp(
                        test=self.make_test(arg_typ),
                        body=self.none_type_casting(to_typ),
                        orelse=copy.deepcopy(target),
                        mark=True # 찾기 쉽도록 mark 해두기
                    )

                    change = ChangeNode(target, new_node)
                    
                    change.get_node(copy_stmt)
                    new_stmt = copy.deepcopy(copy_stmt)
                    self.add_template_info(new_stmt, TemplateMethod.Modify, template_info_list)
                    change.revert_node(copy_stmt)
                

        return template_info_list

    
    def multiple_template(self, stmt_list, i) :
        ast_list = list()

        (typ, template) = self.arg_template

        if template == Template.AddException :
            new_node = ast.Try(
                body=[stmt_list[i]],
                handlers=[
                    ast.ExceptHandler(
                        type=ast.Name(id='TypeError', ctx=ast.Load()),
                        body=[
                            ast.Constant(value='<pyfix_template>', is_template=True, template_type=Template.AddException, self=self.arg)
                        ]
                    )
                ],
                orelse=[],
                finalbody=[],
                mark=True
            )
            
            stmt_origin = stmt_list[i]
            stmt_list[i] = new_node

            copy_origin = copy.deepcopy(self.origin)
            ast_list.append(copy_origin)

            stmt_list[i] = stmt_origin

        if template == Template.NotPos :
            test_list = list()
            import_type_nodes = list()
            
            if typ : # 목표 타입이 있으면...
                test = self.make_test(abc_to_typ(typ))
                test_list.append(test)

                add_import = False
                if "::" in typ :
                    typ = typ.split("::")[1] # subclass 체크하는건 testclass 일때만...

                modify_typ = typ_str_modify(typ)

                if modify_typ == "builtin_function_or_method" :
                    import_type_node = ast.Import(
                        names=[
                            ast.alias(name='types')
                        ]
                    )
                    add_import = True

                elif modify_typ.find('.') != -1 : # class node
                    name = modify_typ[:modify_typ.find('.')]

                    import_type_node = ast.Import(
                        names=[
                            ast.alias(name=name)
                        ]
                    )
                    add_import = True
                
                elif is_ndarray_type(modify_typ) :
                    import_type_node = ast.Import(
                        names=[
                            ast.alias(name='numpy')
                        ]
                    )
                    add_import = True

                if add_import :
                    import_type_nodes.append(import_type_node)

            else :
                for arg_typ in self.arg_typ_info.keys() :
                    test = self.make_test(abc_to_typ(arg_typ))
                    test_list.append(test)

                    add_import = False
                    if "::" in arg_typ :
                        arg_typ = arg_typ.split("::")[1] # subclass 체크하는건 testclass 일때만...

                    modify_arg_typ = typ_str_modify(arg_typ)

                    if modify_arg_typ == "builtin_function_or_method" :
                        import_type_node = ast.Import(
                            names=[
                                ast.alias(name='types')
                            ]
                        )
                        add_import = True

                    elif modify_arg_typ.find('.') != -1 : # class node
                        name = modify_arg_typ[:modify_arg_typ.find('.')]

                        import_type_node = ast.Import(
                            names=[
                                ast.alias(name=name)
                            ]
                        )
                        add_import = True
                    
                    elif is_ndarray_type(modify_arg_typ) :
                        import_type_node = ast.Import(
                            names=[
                                ast.alias(name='numpy')
                            ]
                        )
                        add_import = True

                    if add_import :
                        import_type_nodes.append(import_type_node)

            new_node = ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=ast.BoolOp(
                        op=ast.Or(),
                        values=test_list
                    )
                ),
                body=[
                    ast.Constant(value='<pyfix_template>', is_template=True, template_type=Template.NotPos, self=self.arg)
                ],
                orelse =[],
                mark = True
            )

            stmt_list.insert(i, new_node)
            import_type_nodes = list(dict.fromkeys(import_type_nodes))
            for import_type_node in import_type_nodes :
                stmt_list.insert(i, import_type_node)

            copy_origin = copy.deepcopy(self.origin)
            ast_list.append(copy_origin)

            for k in range(0, len(import_type_nodes)) :
                del stmt_list[i]

            del stmt_list[i]

        if template == Template.NotPosTypeCasting :
            test_list = list()
            import_type_nodes = list()

            test = self.make_test(abc_to_typ(typ))
            test_list.append(test)

            add_import = False
            if "::" in typ :
                typ = typ.split("::")[1] # subclass 체크하는건 testclass 일때만...

            modify_typ = typ_str_modify(typ)

            if modify_typ == "builtin_function_or_method" :
                import_type_node = ast.Import(
                    names=[
                        ast.alias(name='types')
                    ]
                )
                add_import = True

            elif modify_typ.find('.') != -1 : # class node
                name = modify_typ[:modify_typ.find('.')]

                import_type_node = ast.Import(
                    names=[
                        ast.alias(name=name)
                    ]
                )
                add_import = True
            
            elif is_ndarray_type(modify_typ) :
                import_type_node = ast.Import(
                    names=[
                        ast.alias(name='numpy')
                    ]
                )
                add_import = True

            if add_import :
                import_type_nodes.append(import_type_node)

            body = self.type_casting_to_ast(self.arg, None, typ)

            new_node = ast.If(
                test=ast.UnaryOp(
                    op=ast.Not(),
                    operand=ast.BoolOp(
                        op=ast.Or(),
                        values=test_list
                    )
                ),
                body=[
                    body
                ],
                orelse =[],
                mark = True
            )

            stmt_list.insert(i, new_node)
            import_type_nodes = list(dict.fromkeys(import_type_nodes))
            for import_type_node in import_type_nodes :
                stmt_list.insert(i, import_type_node)

            copy_origin = copy.deepcopy(self.origin)
            ast_list.append(copy_origin)

            for k in range(0, len(import_type_nodes)) :
                del stmt_list[i]

            del stmt_list[i]



        return ast_list

    def single_template(self, stmt_list, i) :
        ast_list = list()

        import_type_nodes = list()

        add_template = list()
        replace_template = list()
        modify_template = list()

        for (arg_typ, template) in self.arg_template :
            method = get_template_method(template)
            if method == TemplateMethod.Add :
                add_template.append((arg_typ, template))
            elif method == TemplateMethod.Replace :
                replace_template.append((arg_typ, template))
            elif method == TemplateMethod.Modify :
                modify_template.append((arg_typ, template))

            # import문 추가
            add_import = False
            if "::" in arg_typ :
                arg_typ = arg_typ.split("::")[1] # subclass 체크하는건 testclass 일때만...

            arg_typ = typ_str_modify(arg_typ)

            if arg_typ == "builtin_function_or_method" :
                import_type_node = ast.Import(
                    names=[
                        ast.alias(name='types')
                    ]
                )
                add_import = True

            elif arg_typ.find('.') != -1 : # class node
                name = arg_typ[:arg_typ.find('.')]

                import_type_node = ast.Import(
                    names=[
                        ast.alias(name=name)
                    ]
                )
                add_import = True
            
            elif is_ndarray_type(arg_typ) :
                import_type_node = ast.Import(
                    names=[
                        ast.alias(name='numpy')
                    ]
                )
                add_import = True

            if add_import :
                import_type_nodes.append(import_type_node)

        '''
        Modify Template 먼저 진행
        stmt가 수정 되기 때문
        '''


        if modify_template :
            def get_modify_candidates(modify_template) :
                (arg_typ, template) = modify_template[0]
                others = modify_template[1:]

                new_template_list = list()
                if others :
                    other_template_list = get_modify_candidates(modify_template[1:])
                    
                    prev = stmt_list[i]
                    for other_template in other_template_list :
                        stmt_list[i] = other_template['template']

                        candidate_templates = self.modify_template(arg_typ, template, stmt_list, i)
                        new_template_list.extend(candidate_templates)

                    stmt_list[i] = prev
                else :
                    candidate_templates = self.modify_template(arg_typ, template, stmt_list, i)
                    new_template_list.extend(candidate_templates)

                return new_template_list

            modify_ast_list = get_modify_candidates(modify_template)
        else :
            modify_ast_list = [{'template' : stmt_list[i]}] # 꼼수
        
        prev = stmt_list[i]

        for modify_ast in modify_ast_list :
            stmt_list[i] = modify_ast['template']

            '''
            Replace 얻어오기
            '''
            replace_result = list()
            for (arg_typ, template) in replace_template :
                candidate_templates = list()
                candidate_templates = self.replace_template(arg_typ, template, stmt_list, i)
                replace_result.append(candidate_templates)  

            '''
            Add 얻어오기
            '''
            add_result = list()
            for (arg_typ, template) in add_template :
                candidate_templates = list()
                candidate_templates = self.add_template(arg_typ, template, stmt_list, i)
                add_result.append(candidate_templates)
            
            total_result = replace_result + add_result

            '''
            최종 합성
            '''
            for total in product(*total_result) :
                # total = (replace1, replacd2, add1 ...)
                replace_node = None
                replace_last = None

                add_node = None
                add_last = None

                for idx, t in enumerate(total) :
                    t = t['template']
                    if idx < len(replace_result) : # replace method
                        if replace_node :
                            replace_last.orelse = [t]
                        else :
                            replace_node = t

                        replace_last = t
                    else : # add method
                        if add_node :
                            add_last.orelse = [t]
                        else :
                            add_node = t

                        add_last = t

                if replace_node is not None :
                    stmt_list[i] = replace_node

                if add_node is not None :
                    stmt_list.insert(i, add_node)
                    
                #input()
                import_type_nodes = list(dict.fromkeys(import_type_nodes))
                for import_type_node in import_type_nodes :
                    stmt_list.insert(i, import_type_node)

                copy_origin = copy.deepcopy(self.origin)
                ast_list.append(copy_origin)

                for k in range(0, len(import_type_nodes)) :
                    del stmt_list[i]

                if add_node is not None :
                    del stmt_list[i]

                if replace_node is not None :
                    stmt_list[i] = prev

        

        stmt_list[i] = prev
        return ast_list

    def make_ast_list(self, stmt_list, i) :
        ast_list = list()

        if len(self.arg_template) >= 2 and isinstance(self.arg_template[1], Template) and get_template_method(self.arg_template[1]) == TemplateMethod.Multiple : # 이건 multiple patch
            ast_list.extend(self.multiple_template(stmt_list, i))
        else :
            
            ast_list.extend(self.single_template(stmt_list, i))

        return ast_list

    def make_ast_generator(self, node) :
        for (arg_typ, template) in self.arg_template :
            if template == Template.Skip or template == Template.If :
                if isinstance(node.generators[0], ast.comprehension) :
                    test = self.make_test(arg_typ)
                    new_node = ast.UnaryOp(
                            op=ast.Not(),
                            operand=test,
                            mark=True
                        )

                    node.generators[0].ifs.append(new_node)

                    self.ast_list.append(copy.deepcopy(self.origin))

                    node.generators[0].ifs.pop()
                    del new_node

            elif template == Template.IfElse :
                test = self.make_test(arg_typ)
                new_node = ast.IfExp(
                    test=test,
                    body=ast.Constant(value='<pyfix_template>', is_template=True, template_type=Template.IfElse, self=self.arg),
                    orelse=copy.deepcopy(node.elt),
                    mark=True
                )

                prev_node = node.elt
                node.elt = new_node

                self.ast_list.append(copy.deepcopy(self.origin))

                node.elt = prev_node



        return self.ast_list

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
                        self.ast_list = self.make_ast_generator(candidate_node)

                        # 더 이상 수정할 게 없다
                        return self.ast_list
            # For 문 다 돌았으면 여기는 이제 볼 것이 없다

        return self.ast_list

    def find_template_place(self, node, error_stmt) :    
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
                        #print(ast.dump(child_stmt))
                        #self.components.extract_components(child_stmt)

            
                        self.ast_list = self.make_ast_list(attr, i)
                        #self.mutate_list.append(self.add_isinstance_stmt_else_error(attr, i)) else 는 일단 빼봐

                        return self.ast_list

                    self.find_template_place(child_stmt, error_stmt)

            elif isinstance(attr, (ast.mod, ast.stmt)) :
                self.find_template_place(child_stmt, error_stmt)


        return self.ast_list



    #def to_ast(self, template) :

    def check_which_template(self, funcname, error_stmt) :
        '''
        funcname에 따라 template이 조금 달라짐
        <genexpr> 은 iterate안에서 일어나는거
        '''
        if funcname == "<genexpr>" :
            return self.find_error_comp_elt(self.origin, error_stmt)
        else :
            return self.find_template_place(self.origin, error_stmt)

    def get_ast_list(self, funcname, error_stmt) :
        self.ast_list = list()
        
        final_list = self.check_which_template(funcname, error_stmt)

        return final_list
        

