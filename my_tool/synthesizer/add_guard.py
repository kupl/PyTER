'''
바로 typecasting 넣어주는 파일
'''
import ast
from copy import deepcopy
from template.util import ChangeNode
from type_analysis.util import abstract_type

class AddGuard(ast.NodeTransformer) :
    def __init__(self, origin) :
        self.origin = origin

    def get_guard_list(self, var_score, neg_args, node, neg=False) :
        guard_list = list()
        for target, typ_info in var_score.items() :
            for typ in typ_info.keys() :
                iterable_types = ['List', 'Tuple', 'Set', 'Dict']

                new_node = deepcopy(node)

                if isinstance(typ, tuple) : 
                    value = ast.BoolOp(
                        op=ast.And(),
                        values=[
                            ast.Call(
                                func=ast.Name(id='isinstance', ctx=ast.Load()),
                                args=[
                                    deepcopy(target),
                                    ast.Name(id=t.lower() if t in iterable_types else t, ctx=ast.Load())
                                ],
                                keywords=[]
                            ) for t in typ
                        ]
                    )
                else :
                    if typ in iterable_types :
                        typ = typ.lower()

                    value = ast.Call(
                        func=ast.Name(id='isinstance', ctx=ast.Load()),
                        args=[
                            deepcopy(target),
                            ast.Name(id=typ, ctx=ast.Load())
                        ],
                        keywords=[]
                    )

                
                if neg :
                    if typ == 'None' :
                        value = deepcopy(target)

                    else :
                        value = ast.UnaryOp(op=ast.Not(), operand=value)


                new_node.test = ast.BoolOp(
                    op=ast.And(),
                    values=[
                        value,
                        new_node.test
                    ],
                    mark=True
                )

                change = ChangeNode(node, new_node)
                change.get_node(self.origin)
                copy_origin = deepcopy(self.origin)
                guard_list.append(copy_origin)
                change.revert_node(self.origin)

                

        return guard_list