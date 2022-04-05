import itertools
import ast
import typing
from pyfix_type.pyfix_type import ExprType

class TypeCorrect(Exception) :
    pass

class TypeGuidedSearch() :
    def __init__(self, expr_components) :
        self.expr_components = expr_components

    def check_equal_typ(self, hole_typ, comp_typ) :
        if hole_typ == comp_typ :
            raise TypeCorrect

    def search(self, hole) :
        result = []

        hole_typs = getattr(hole, "typ", ExprType(typing.Any))

        for component in self.expr_components :
            component_typs = getattr(component, "typ") 

            typ_match = hole_typs.match(component_typs)
            if typ_match is True :
                result.append(component)

        return result