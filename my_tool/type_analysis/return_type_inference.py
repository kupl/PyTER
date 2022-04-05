'''
retunr type 추론 하는 곳입니다
'''

import ast 
from .util import FindTargetFunc
from .error_analysis import ErrorAnalysis


class ReturnInference(ast.NodeVisitor) :
    

    def __init__(self, target, neg_args, neg_file_node, pos_func_infos, skip_arg=None) :
        self.return_typ_list = list()
        self.target = target
        self.neg_args = neg_args
        self.neg_file_node = neg_file_node
        self.pos_func_infos = pos_func_infos
        self.skip_arg = skip_arg

    def visit_Return(self, node) :
        
        if node is self.target :
            return
        if hasattr(node, 'value') :
            expr = node.value

            if expr is None :
                return 

            if self.skip_arg and self.skip_arg == ast.unparse(expr) :
                return 

            if isinstance(expr, ast.Constant) :
                if isinstance(expr.value, str) and 'pyfix_template' in expr.value :
                    return

                return_typ = type(expr.value).__name__
                self.return_typ_list.append(return_typ)

            elif isinstance(expr, (ast.Name, ast.Attribute)) :
                return_typs = self.neg_args.get(ast.unparse(expr), None)

                if return_typs :
                    for return_typ in return_typs :
                        self.return_typ_list.append(return_typ)

            elif isinstance(expr, ast.Call) :
                pass

            elif isinstance(expr, (ast.BoolOp, ast.Compare)) :
                self.return_typ_list.append("bool")

            else :
                error_analysis = ErrorAnalysis(self.neg_args, self.neg_file_node, self.pos_func_infos)
                var_score, _ = error_analysis.extract_score(expr)

                for typ_dict in var_score.values() :
                    for typ in typ_dict.keys() :
                        self.return_typ_list.append(typ)


    def get_return_typ_list(self, node) :
        find_func = FindTargetFunc(self.target)
        target_func = find_func.get_func(node)

        if target_func :
            self.visit(target_func)

        return self.return_typ_list