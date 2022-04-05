import ast
from type_analysis.util import FindTargetFunc

def compare_ast(node1, node2):
    if type(node1) != type(node2):
        return False
    elif isinstance(node1, ast.AST):
        for kind, var in vars(node1).items():
            if kind not in ('lineno', 'col_offset', 'ctx'):
                var2 = vars(node2).get(kind)
                if not compare_ast(var, var2):
                    return False
        return True
    elif isinstance(node1, list):
        if len(node1) != len(node2):
            return False
        for i in range(len(node1)):
            if not compare_ast(node1[i], node2[i]):
                return False
        return True
    else:
        return node1 == node2


class FindRaise(ast.NodeVisitor) :
    
    def __init__(self, target, target_raise) :
        self.raise_list = list()
        self.target = target
        self.target_raise = target_raise

    def visit_Raise(self, node) :
        if hasattr(node, 'exc') :
            if isinstance(node.exc, ast.Call) :
                if node.exc.func.id == self.target_raise :
                    self.raise_list.append(node)
            elif isinstance(node.exc, ast.Name) :
                if node.exc.id == self.target_raise :
                    self.raise_list.append(node)

    def get_raise_list(self, node) :
        find_func = FindTargetFunc(self.target)
        target_func = find_func.get_func(node)

        self.visit(target_func)
        return self.raise_list
