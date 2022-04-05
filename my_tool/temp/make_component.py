import ast

class MakeComponent(ast.NodeVisitor) :
    def __init__(self) :
        self.stmt_component = list()
        self.expr_component = list()

    def generic_visit(self, node) :
        super().generic_visit(node)

        if isinstance(node, ast.stmt) :
            fields = node._fields

            for field in fields :
                if isinstance(field)