import ast

from copy import deepcopy
from .util import is_class_type
from template.util import ChangeNode

class ChangeVariable() :
    def __init__(self, neg_args) :
        self.neg_args = neg_args

    def find_candidate_node_set(self, target_node, target_typ, to_typ) :
        candidate_var_set = set([])
        for arg_name, typ_list in self.neg_args.items() :
            if target_typ in typ_list :
                candidate_var_set.add(arg_name)

        candidate_node_set = set([])
        for candidate_var in candidate_var_set :
            start_name = candidate_var + '.'

            for arg_name, typ_list in self.neg_args.items() :
                if arg_name.startswith(start_name) and to_typ in typ_list :
                    def make_attribute(attr_list) :
                        attr = attr_list[0]
                        others = attr_list[1:]

                        if others :
                            return ast.Attribute(
                                value=make_attribute(others),
                                attr=attr,
                                ctx=ast.Load()
                            )
                        else :
                            return ast.Attribute(
                                value=deepcopy(target_node),
                                attr=attr,
                                ctx=ast.Load()
                            )

                    attr_node = make_attribute(arg_name.split('.')[1:])

                    candidate_node_set.add(attr_node)

        return candidate_node_set

    def change_variable(self, origin, target_node, target_typ_list, to_typ) :
        ast_list = list()
        for target_typ in target_typ_list :
            if is_class_type(target_typ) :
                candidate_node_set = self.find_candidate_node_set(target_node, target_typ, to_typ)

                if candidate_node_set : # 바꿔친 후 validation 해보기
                    for candidate_node in candidate_node_set :
                        candidate_node.mark = True
                        change = ChangeNode(target_node, candidate_node)
                        change.get_node(origin)

                        ast_list.append(deepcopy(origin))

                        change.revert_node(origin)

        return ast_list