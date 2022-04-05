'''
if 문에 들어가는게 Assign이어서,
body statement를 어디까지 집어 넣을지 선택하자
'''

import ast

class CheckVariable(ast.NodeVisitor) :
    
    def __init__(self, target_var) :
        self.use_var = None
        self.set_var = None
        self.target_var = target_var

    def visit_Attribute(self, node) :
        if ast.unparse(node) in self.target_var :
            if isinstance(node.ctx, ast.Load) :
                self.use_var = True
            elif isinstance(node.ctx, ast.Store) :
                self.set_var = False

    def visit_Name(self, node) :
        if ast.unparse(node) in self.target_var :
            if isinstance(node.ctx, ast.Load) :
                self.use_var = True
            elif isinstance(node.ctx, ast.Store) :
                self.set_var = False

    def check_usage(self, node) :
        '''
        True -> 사용했다
        False -> assign 했다
        None -> 모른다
        '''

        self.visit(node)

        return self.use_var, self.set_var

class BodyAnalysis() :
    def get_body_end(self, stmt_list, start) :
        end = start

        if isinstance(stmt_list[i], ast.Assign) :
            value_list = [ast.unparse(v) for v in node.targets]
            check = CheckVariable(value_list)
        elif isinstance(stmt_list[i], ast.AugAssign) :
            check = CheckVariable([ast.unparse(node.target)])
        elif isinstance(stmt_list[i], ast.AnnAssign) :
            check = CheckVariable([ast.unparse(node.target)])
        else :
            return end

        for i in range(start+1, len(stmt_list)) :
            use_var, set_var = check.check_usage(stmt_list[i])

            if use_var is True :
                end = i
            
            if set_var is True :
                return end

        return end