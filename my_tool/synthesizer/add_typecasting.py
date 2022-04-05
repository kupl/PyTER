'''
바로 typecasting 넣어주는 파일
'''
import ast
from copy import deepcopy
from type_analysis.util import abstract_type

class AddTypeCasting(ast.NodeTransformer) :
    def __init__(self) :
        self.target = None
        self.to_typ = None 
        self.after = None
        self.origin_node = None

    def make_typecasting_iter_to_int(self, node) :
        # iter -> int ==> len 함수 이용
        return ast.Call(
            func=ast.Name(id='len', ctx=ast.Load()),
            args=[
                deepcopy(node)
            ],
            keywords=[],
            mark=True
        )

    def none_type_casting(self, to_type) :
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

        
        return ast.Call(
            func=ast.Name(id=to_type, ctx=ast.Load()),
            args=[],
            keywords=[]
        )

    def typecasting(self, node) :
        self.origin_node = node

        if self.from_typ in ["List", "Tuple", "Set", "Dict"] and self.to_typ == "int" :
            self.after = self.make_typecasting_iter_to_int(node)
        elif self.from_typ == 'None' :
            self.after = ast.IfExp(
                test=ast.Compare(left=node, ops=[ast.Is()], comparators=[ast.Constant(value=None)]),
                body=self.none_type_casting(self.to_typ),
                orelse=deepcopy(node),
                mark=True
            )
        elif self.from_typ == 'method' : # method를 안써야할 수도 있으므로
            if isinstance(node, ast.Call) :
                self.after = deepcopy(node.func)
                self.after.mark = True
        elif self.to_typ == 'method' :
            if isinstance(node, ast.Call) :
                # method여야 하는데 다른타입으로 쓰이고있다?
                # 오히려 method가 아닐수 있음
                self.after = deepcopy(node.func)
                self.after.mark = True
        else :
            self.after = ast.Call(
                func=ast.Name(id=self.to_typ.lower(), ctx=ast.Load()),
                args=[
                    deepcopy(node)
                ],
                keywords=[],
                mark=True
            ) 
        
        return self.after

    def generic_visit(self, node) :
        if node is self.after :
            return self.origin_node
            
        if node is self.target :
            self.after = self.typecasting(node)
            return self.after or node

        return super().generic_visit(node)

    def get_typecasting_list(self, var_score, neg_args, node) :
        typecasting_list = list()
        for target, typ_info in var_score.items() :
            self.target = target

            target_str = ast.unparse(target)
            if target_str in neg_args :
                # typecasting이어서 어쩔수가 없다...
                self.from_typ = abstract_type(neg_args[target_str][0])
            else :
                self.from_typ = ""

            for typ in typ_info.keys() :
                self.to_typ = typ
                self.after = None
                self.origin_node = None

                self.visit(node)
                
                if self.after is None :
                    continue 

                
                typecasting_list.append(deepcopy(node))

                self.visit(node) # 원상복구

        return typecasting_list