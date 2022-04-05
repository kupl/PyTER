'''
새로 정의하는지 아니면 쓰는지 분석해봅시다
'''

import ast

class UsageAnalysis(ast.NodeVisitor) :
    
    def __init__(self, target) :
        self.should_fix = None
        self.find_stmt = False
        self.target = target

    def generic_visit(self, node) :
        super().generic_visit(node)

        if isinstance(node, ast.stmt) and self.should_fix is not None and self.find_stmt is False:
            self.find_stmt = node

        elif self.should_fix is None and not isinstance(node, ast.Call) and ast.unparse(node) == self.target :
            if isinstance(node, (ast.arg, ast.alias)) :
                self.should_fix = True
            elif isinstance(node.ctx, ast.Load) :
                self.should_fix = True
            elif isinstance(node.ctx, ast.Store) :
                self.should_fix = False

    def get_stmt(self, node) :
        self.visit(node)

        return self.should_fix, self.find_stmt