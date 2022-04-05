'''
에러 코드 중
try-exception 안에 있어서
exception에 TypeError를 추가하면 되는지 확인해보는 template입니다
'''

import ast
from copy import copy, deepcopy

class AddException(ast.NodeTransformer) :
    

    def __init__(self, node, target) :
        self.in_try_statement = False
        self.add_exception = False
        self.complete_list = list()
        self.node = node
        self.target = target
    
    def visit_Try(self, node) :
        self.in_try_statement = True

        for child in node.body : 
            self.generic_visit(child)

        if self.add_exception : # TypeError Exception을 새로 추가하자
            add_handler_list = list()
            has_typeerror_handler = False
            
            for handler in node.handlers :
                if isinstance(handler.type, ast.Tuple) :
                    for elt in handler.type.elts :
                        if elt.id == 'TypeError' :
                            has_typeerror_handler = True
                            break

                elif handler.type.id == 'TypeError' :
                    has_typeerror_handler = True
                    break
                copy_handler = copy(handler)
                copy_handler.mark = True
                copy_handler.type = ast.Name(id='TypeError', ctx=ast.Load())
                add_handler_list.append(copy_handler)

            if not has_typeerror_handler : # TypeError Exception이 없었으면 추가한 노드를 만들자
                for handler in add_handler_list :
                    node.handlers.append(handler)
                    self.complete_list.append(deepcopy(self.node))
                    
                    del node.handlers[-1]

            raise Exception # 탈출을 위한 excpetion
                    
            


        self.in_try_statement = False

        super().generic_visit(node)

        return node
 

    def generic_visit(self, node) :

        if self.in_try_statement and node is self.target :
            self.add_exception = True

        super().generic_visit(node)

        return node

    def get_exception_list(self, node) :
        self.in_try_statement = False
        self.add_exception = False
        self.complete_list = list()

        try :
            self.visit(node)
        except :
            pass

        return self.complete_list