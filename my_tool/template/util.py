from enum import Enum
from type_analysis.util import abstract_type

import ast
import copy

class Template(Enum) :
    TypeCasting = 1
    NoneCheck = 2
    AddException = 3
    ModifyException = 4
    Return = 5
    Skip = 6
    IfNoneCheck = 7
    InLoopContinue = 8
    InLoopBreak = 9
    SubClass = 10
    If = 11
    IfElse = 12
    NoneElse = 13
    NotPos = 14
    NotPosTypeCasting = 15
    OpMutate = 16

class TemplateMethod(Enum) :
    Add = [
        Template.TypeCasting,
        Template.InLoopContinue,
        Template.InLoopBreak,
        Template.SubClass,
        Template.Return,
        Template.If
    ]
    Replace = [
        Template.NoneCheck,
        Template.Skip,
        Template.IfElse,
        Template.OpMutate
    ]
    Modify = [
        Template.IfNoneCheck,
        Template.NoneElse
    ]
    Multiple = [
        Template.AddException,
        Template.NotPos,
        Template.NotPosTypeCasting
    ]

def get_template_method(template) :
    for method in TemplateMethod :
        if template in method.value :
            return method

BASIC = [Template.If, Template.IfElse]
NONE_PATCH = [Template.NoneElse, Template.NoneCheck]
TRY_PATCH = [Template.AddException]
TYPE_CASTING = [Template.TypeCasting]
DEFAULT = [Template.Return, Template.Skip]
INLOOP = [Template.InLoopContinue, Template.InLoopBreak]

def typ_str_modify(typ_str) :
    '''
    정제되지 않은 typ_str을 적절히 변형시켜주자
    ex) List[str, str] -> list ...
    '''
    typ = abstract_type(typ_str)


    # 기본내장 함수 => 소문자로
    if typ in ['List', 'Set', 'Tuple', 'Dict'] :
        typ = typ.lower()

    # ndarray => 따로 처리해야하는거 추가 해야댐 ToDo
    if typ.find('<<') != -1 :
        typ = typ[:typ.find('<<')]

    return typ

def abc_to_typ(typ) :
    if typ == "collections.abc.Mapping" :
        return "Dict"

    return typ

class IsInLoop(ast.NodeVisitor) :
    def __init__(self) :
        self.lineno = None
        self.in_loop = False
        self.is_in_loop = False

    def visit_For(self, node) :
        if node.lineno <= self.lineno <= node.end_lineno :
            self.is_in_loop = True
        #self.in_loop = True
        #self.generic_visit(node)
        #self.in_loop = False

    
    def visit_AsyncFor(self, node) :
        if node.lineno <= self.lineno <= node.end_lineno :
            self.is_in_loop = True
        #self.in_loop = True
        #self.generic_visit(node)
        #self.in_loop = False

    
    def visit_While(self, node) :
        if node.lineno <= self.lineno <= node.end_lineno :
            self.is_in_loop = True
        #self.in_loop = True
        #self.generic_visit(node)
        #self.in_loop = False

    
    def generic_visit(self, node) :
        if self.is_in_loop :
            return 

        #if node is self.error_stmt and self.in_loop :
        #    self.is_in_loop = True

        super().generic_visit(node)

    def isin_loop(self, lineno, node) :
        self.lineno = lineno
        self.visit(node)

        return self.is_in_loop

class FindNoneElseTarget(ast.NodeVisitor) :
    def __init__(self, target_var) :
        self.target = None
        self.target_var = target_var

    def visit_Subscript(self, node) :
        if self.target is None and ast.unparse(node.value) == self.target_var :
            self.target = node

        super().generic_visit(node)

    def visit_Attribute(self, node) :
        if self.target is None and ast.unparse(node) == self.target_var :
            self.target = node

        super().generic_visit(node)

    def get_target(self, node) :
        self.visit(node)

        return self.target

class ChangeNode(ast.NodeTransformer) :
    
    def __init__(self, target, to) :
        self.revert = False
        self.target = target
        self.to = to

    def generic_visit(self, node) :
        super().generic_visit(node)

        if not self.revert and node is self.target :
            return self.to
        elif self.revert and node is self.to :
            return self.target

        return node 

    def get_node(self, node) :
        self.revert=False
        node = self.visit(node)

        return node

    def revert_node(self, node) :
        self.revert=True
        node = self.visit(node)

        return node

class FindTemplate(ast.NodeVisitor) :
    def __init__(self) :
        self.target = list()
    def generic_visit(self, node) :
        if hasattr(node, 'mark') and node.mark :
            self.target.append(node)        

        super().generic_visit(node)

    def get_target(self, node) :
        self.target = list()
        self.visit(node)

        return self.target

class FindSuspiciousNode(ast.NodeVisitor) :
    def __init__(self, target) :
        self.target = target
        self.if_list = list()
        self.stmt_list = list()
        self.target_if_stmt = None
        self.is_target = False

    def visit_If(self, node) :
        super().generic_visit(node)

        if self.is_target :
            self.if_list.append(node)
            return

        for body in node.body :
            if body == self.target :
                self.is_target = True
                self.target_if_stmt = node

                if len(node.orelse) == 1 and isinstance(node.orelse, ast.If) :
                    self.if_list.append(node.orelse)
                    self.visit_If(node.orelse[0])
                else :
                    self.stmt_list.append(node.orelse)

        for body in node.orelse :
            if body == self.target :
                self.target_if_stmt = node
                self.is_target = True
                self.if_list.append(node)

    def generic_visit(self, node) :
        if isinstance(node, ast.stmt) :
            if hasattr(node, 'body') :
                for i, body in enumerate(node.body) :
                    self.visit(body)

                    if self.is_target :
                        self.stmt_list.append(node.body[(i+1):])
                        self.is_target = False

            if hasattr(node, 'orelse') :
                for i, body in enumerate(node.orelse) :
                    self.visit(body)

                    if self.is_target :
                        self.stmt_list.append(node.orelse[(i+1):])
                        self.is_target = False

            if hasattr(node, 'finalbody') :
                for i, body in enumerate(node.finalbody) :
                    self.visit(body)

                    if self.is_target :
                        self.stmt_list.append(node.finalbody[(i+1):])
                        self.is_target = False
        else :
            super().generic_visit(node)

    def get_node_list(self, node) :
        self.visit(node)

        return self.stmt_list, self.if_list, self.target_if_stmt

class FindIsInstance(ast.NodeVisitor) :
    def __init__(self, arg, typ) :
        self.arg = arg
        self.typ = typ
        self.target_node = []

    def visit_If(self, node) :
        try :
            if node.test.func.id == 'isinstance' :
                if node.test.args[0].id == self.arg :
                    if node.test.args[1].id == self.typ :
                        self.target_node.append(node)
        except :
            pass

        self.generic_visit(node)

    def get_isinstance(self, node) :
        self.visit(node)

        return self.target_node