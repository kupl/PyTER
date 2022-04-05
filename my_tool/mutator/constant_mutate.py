import ast
from copy import deepcopy

class ConstantMutate(ast.NodeVisitor) :
    
    def __init__(self, node, constant_dict, to_typ=None) :
        self.mutate_list = list()
        self.node = node
        self.constant_dict = constant_dict
        self.to_typ = to_typ

    def visit_Constant(self, node) :
        type_name = self.to_typ if self.to_typ else type(node.value).__name__
        constant_list = self.constant_dict.get(type_name, [])

        for constant in constant_list :
            prev = node.value
            node.value = constant
            self.mutate_list.append(deepcopy(self.node))
            node.value = prev

    def get_mutate_list(self) :
        self.visit(self.node)

        return self.mutate_list