import ast
import copy

def make_expr_hole() :
    return ast.Constant(value="__expr_hole__")

class MakeExprHole(ast.NodeTransformer) :
    def __init__(self, origin) :
        self.origin = origin
        self.candidates = list()

    def add_candidates(self) :
        self.candidates.append(copy.deepcopy(self.origin))

    def get_candidates(self) :
        self.collect_candidates()
        return self.candidates

    '''
    stmt
    '''

    def visit_Return(self, node) :
        self.generic_visit(node)
        
        if hasattr(node, "value") :
            prev = node.value
            node.value = make_expr_hole()
            self.add_candidates()
            node.value = prev

        return node

    '''
    expr
    '''

    def visit_Call(self, node) :
        self.generic_visit(node)

        for idx in range(0, len(node.args)) :
            prev = node.args[idx]
            node.args[idx] = make_expr_hole()
            self.add_candidates()
            node.args[idx] = prev

        return node

    def visit_Attribute(self, node) :
        self.generic_visit(node)

        prev = node.value
        node.value = make_expr_hole()
        self.add_candidates()
        node.value = prev

        return node

    def collect_candidates(self) :
        self.visit(self.origin)       

    '''
    def generic_visit(self, node) :
        super().generic_visit(node)

        condition = (isinstance(node, self.target))

        if condition :
            if self.target is ast.expr :
                return ast.Constant(value="__expr_hole__")
    '''



