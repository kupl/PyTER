from ast import NodeTransformer
import ast
import copy
import itertools
from enum import Enum

from . import type_guided_search

class Mode(Enum) :
    FIND = 1
    RESTORE = 2
    SYNTHESIZE = 3

class AstSynthesize(NodeTransformer) :
    expr_synthe_limit = 5

    def __init__ (self, validator, filename, origin, context_aware) :
        self.validator = validator
        self.filename = filename
        self.origin = origin
        self.context_aware = context_aware

        self.stmt_holes = set()
        self.expr_holes = set()

        self.stmt_synthesize = StmtSynthesizer()
        self.expr_synthesize = ExprSynthesizer()

        self.candidate = None
        self.hole = None
        self.mode = None

    def validation(self, node) :
        self.validator.validate(node, self.filename)

    def set_stmt_component(self, components) :
        self.stmt_components = components
    
    def set_expr_component(self, components) :
        self.expr_components = components

    def generic_visit(self, node) :
        super().generic_visit(node)

        stmt_hole_condition = (
            isinstance(node, ast.Pass) and
            hasattr(node, "hole")
        )

        expr_hole_condition = (
            isinstance(node, ast.Constant) and
            node.value == "__expr_hole__"
        )

        if stmt_hole_condition :
            self.stmt_holes.add(node)

        if expr_hole_condition :
            self.expr_holes.add(node)

        return node

    def find_holes(self, node) :
        self.stmt_holes = set()
        self.expr_holes = set()
        self.generic_visit(node)

    def synthesize(self, node, stmt_synthe_num, expr_synthe_num) :
        if expr_synthe_num >= self.expr_synthe_limit :
            return

        self.find_holes(node)
        '''
        print("=== Target node ===")
        print(ast.dump(node, indent=4))
        print(ast.unparse(node))
        print("===================")
        print("Stmt Holes : ", self.stmt_holes)
        print("Expr Holes : ", self.expr_holes)
        '''

        if self.stmt_holes :
            hole = self.stmt_holes.pop()

            # ContextAware
            context_result = self.context_aware.extract_score(hole, [self.origin])

            for context_node in context_result :
                c_node = context_node[0]
                candidate = copy.deepcopy(c_node)
                self.stmt_synthesize.synthesize(node, candidate, hole) 
                self.synthesize(node, stmt_synthe_num+1, expr_synthe_num) # 나머지 hole synthesize
                self.stmt_synthesize.restore(node, candidate, hole) # component -> hole로 교체
                print("Restore!!")
                print(ast.dump(node))
            # ContextAware End 
            print("end")

            for component in self.stmt_components :
                candidate = copy.deepcopy(component)

                self.stmt_synthesize.synthesize(node, candidate, hole)

                ### stmt prune

                self.synthesize(node, stmt_synthe_num+1, expr_synthe_num) # 나머지 hole synthesize
                self.stmt_synthesize.restore(node, candidate, hole) # component -> hole로 교체

        elif self.expr_holes :
            hole = self.expr_holes.pop()
            
            # ContextAware
            context_result = self.context_aware.extract_score(hole, [self.origin])
            # ContextAware End 

            #print("=== Type Guided Search ===")
            type_guided = type_guided_search.TypeGuidedSearch(self.expr_components)
            candidate_components = type_guided.search(hole)
            #print("==========================")

            for component in candidate_components :
                candidate = copy.deepcopy(component)

                self.expr_synthesize.synthesize(node, candidate, hole)

                # expr prune
                if self.expr_synthesize.prune(node) is False :
                    self.synthesize(node, stmt_synthe_num, expr_synthe_num+1) # 나머지 hole synthesize
                #else :
                #    print("Prune!")
                #    input()
                self.expr_synthesize.restore(node, candidate, hole) # component -> hole로 교체

        else :
            #print("Synthe!")
            #input()
            print(ast.unparse(node))
            self.validation(self.origin)

class StmtSynthesizer(NodeTransformer) :
    '''
    stmt_hole 은 어떻게 만들어야해 ㅋㅋ
    stmt* 타입 밖에 없음 -> list 에 추가하는 형식이어야함
    일단 Pass node 에 hole attribute가 있으면 hole 인걸로...
    '''

    def __init__(self) :
        self.candidate = None
        self.hole = None
        self.mode = None

    def insert_stmt(self, stmt_list) :
        if isinstance(self.candidate, ast.Pass) and hasattr(self.candidate, "hole") : # Sequence
            stmt_list.append(self.candidate)

        else :
            stmt_list[-1] = self.candidate 

    def visit_For(self, node) :
        if self.mode == Mode.SYNTHESIZE :
            if self.hole in node.body :
                self.insert_stmt(node.body)

            if self.hole in node.orelse :
                self.insert_stmt(node.orelse)

        return self.generic_visit(node)

    def visit_AsyncFor(self, node) :
        if self.mode == Mode.SYNTHESIZE :
            if self.hole in node.body :
                self.insert_stmt(node.body)

            if self.hole in node.orelse :
                self.insert_stmt(node.orelse)

        return self.generic_visit(node)

    def visit_If(self, node) :
        if self.mode == Mode.SYNTHESIZE :
            if self.hole in node.body :
                self.insert_stmt(node.body)

            if self.hole in node.orelse :
                self.insert_stmt(node.orelse)

        return self.generic_visit(node)


    def generic_visit(self, node) :
        super().generic_visit(node)

        restore_to_hole_conditions = (
            self.mode == Mode.RESTORE and
            node is self.candidate
        )

        if restore_to_hole_conditions :
            #print("Howdy")
            return self.hole

        
        return node

    def restore(self, node, candidate, hole) :
        self.mode = Mode.RESTORE
        self.candidate = candidate
        self.hole = hole
        self.visit(node)

    def synthesize(self, node, candidate, hole) :
        self.mode = Mode.SYNTHESIZE
        self.candidate = candidate
        self.hole = hole
        self.visit(node)

class ExprSynthesizer(NodeTransformer) :
    '''
    expr_hole 은 반드시 Constant Node
    '''
    def __init__(self) :
        self.candidate = None
        self.hole = None
        self.mode = None


    def generic_visit(self, node) :
        super().generic_visit(node)

        restore_to_hole_conditions = (
            self.mode == Mode.RESTORE and
            node is self.candidate
        )

        synthesize_conditions = (
            self.mode == Mode.SYNTHESIZE and
            node is self.hole
        )
        
        if restore_to_hole_conditions :
            return self.hole

        elif synthesize_conditions :
            return self.candidate

        return node

    def restore(self, node, candidate, hole) :
        self.mode = Mode.RESTORE
        self.candidate = candidate
        self.hole = hole
        self.visit(node)

    def prune(self, node) :
        call_depth = 0 # call 안에 call이 3번 연속 들어가면 prune
        call_subscript = 0 # subscript 3번 연속 못하게

        def work_prune(node) :
            nonlocal call_depth
            nonlocal call_subscript
            # check ast type
            if isinstance(node, ast.Call) : call_depth = call_depth + 1
            if isinstance(node, ast.Subscript) : call_subscript = call_subscript + 1
            # check it shoud be pruned
            if call_depth >= 3 or call_subscript >= 3:
                return True

            # iter child
            for child in ast.iter_child_nodes(node) :
                is_pruning = work_prune(child)
                if is_pruning : return True

            if isinstance(node, ast.Call) : call_depth = call_depth - 1
            if isinstance(node, ast.Subscript) : call_subscript = call_subscript - 1

            return False

        return work_prune(node)


    def synthesize(self, node, candidate, hole) :
        self.mode = Mode.SYNTHESIZE
        self.candidate = candidate
        self.hole = hole
        self.visit(node)

