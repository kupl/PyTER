import ast
import copy
from queue import PriorityQueue
from dataclasses import dataclass, field
import typing
from itertools import count
from pydoc import locate

from synthesizer.extract_info import make_expr_hole

from . import make_hole
from pyfix_type.pyfix_type import ExprType

@dataclass(order=True)
class ComponentPriorityQueue() :
    def __init__(self) :
        self.priority_queue = PriorityQueue()
        self.index = count(0)

    def put(self, item):
        if self.check_exist_ast(item) :
            return
        score = self.get_priority(item)
        self.priority_queue.put((score, next(self.index), item))

    def get(self):
        return self.priority_queue.get()[2]

    def queue(self) :
        queue = list()

        for item in self.priority_queue.queue :
            queue.append(item[2])

        return queue

    def join_typ(self, item, queue) :
        '''
        join typ from item to q
        '''
        for i, q in zip(ast.walk(item), ast.walk(queue)) :
            i_typ = getattr(i, "typ", False)
            q_typ = getattr(q, "typ", False)
            if i_typ and q_typ : # 둘 다 typ이 존재 == 둘 다 expr type
                q_typ.intersection(i_typ) # union이 맞나;;

    def check_exist_ast(self, item) :
        item_source = ast.unparse(item)
        for q in self.queue() :
            if item_source == ast.unparse(q) :
                self.join_typ(item, q)
                return True

        return False

    def get_priority(self, item):
        '''
        Set Priority (Score)
        '''
        STMT = 50
        STMT_HOLE = 30
        EXPR = 30
        EXPR_HOLE = 10

        score = 0

        if isinstance(item, ast.stmt) :
            score += STMT
        elif isinstance(item, ast.expr) :
            score += EXPR

        #print(item)

        for child in ast.walk(item) :
            if isinstance(child, ast.Pass) and hasattr(child, "hole") :
                score += STMT_HOLE
            if isinstance(child, ast.Constant) and child.value == "__expr_hole__" :
                score += EXPR_HOLE

        return score

class Component(ast.NodeVisitor) :
    def __init__ (self) :
        self.expr_components = ComponentPriorityQueue()
        self.stmt_components = ComponentPriorityQueue()

        self.add_default_components()

        self.only_stmt = False
        self.only_expr = False

    '''
    stmt
    '''
    def __str__(self) :
        result = "=== Stmt ===\n"

        stmt_queue = self.get_stmt_components()
        for stmt in stmt_queue :
            result = result + ast.dump(stmt) + "\n"

        result = result + "=== Expr ===\n"

        expr_queue = self.get_expr_components()
        for expr in expr_queue :
            result = result + ast.dump(expr) + " type : " + str(getattr(expr, "typ", "")) + "\n"

        return result

    def generic_visit(self, node) :
        if self.only_stmt :
            if not isinstance(node, ast.stmt) :
                return False

        if self.only_expr :
            if not isinstance(node, ast.expr) :
                return False

        return True

    def visit_Return(self, node) :
        if self.generic_visit(node) :
            if hasattr(node, "value") :
                new_hole = make_hole.make_expr_hole()
                setattr(new_hole, 'typ', ExprType(typing.Any))
                self.stmt_components.put(ast.Return(value=new_hole))

        super().generic_visit(node)

        return node

    def visit_Assign(self, node) :
        if self.generic_visit(node) :
            copy_assign = copy.copy(node)
            new_hole = make_hole.make_expr_hole()
            setattr(new_hole, 'typ', ExprType(typing.Any))
            copy_assign.value = new_hole

            self.stmt_components.put(copy_assign)

        super().generic_visit(node)

        return node

    def visit_Raise(self, node) :
        if self.generic_visit(node) :
            if getattr(node, 'exc', None) is not None :
                copy_raise_exc = copy.deepcopy(node)
                new_exc_hole = make_hole.make_expr_hole()
                setattr(new_exc_hole, 'typ', ExprType(typing.Any))
                copy_raise_exc.exc = new_exc_hole
                self.stmt_components.put(copy_raise_exc)

            if getattr(node, 'cause', None) is not None :
                copy_raise_cause = copy.deepcopy(node)
                new_cause_hole = make_hole.make_expr_hole()
                setattr(new_cause_hole, 'typ', ExprType(typing.Any))
                copy_raise_cause.cause = new_cause_hole
                self.stmt_components.put(copy_raise_cause)

            if getattr(node, 'exc', None) is not None and getattr(node, 'cause', None) is not None :
                copy_raise = copy.deepcopy(node)

                new_exc_hole = make_hole.make_expr_hole()
                setattr(new_exc_hole, 'typ', ExprType(typing.Any))
                copy_raise.exc = new_exc_hole

                new_cause_hole = make_hole.make_expr_hole()
                setattr(new_cause_hole, 'typ', ExprType(typing.Any))
                copy_raise.cause = new_cause_hole
                
                self.stmt_components.put(copy_raise)

        super().generic_visit(node)

        return node

    '''
    expr
    '''

    def visit_Call(self, node) :
        if self.generic_visit(node) :
            # Call type 추론해서 넣어야 하는데 ㅁㄴㅇㄻㄴㅇㄻ
            copy_call = copy.deepcopy(node)
            copy_call.args=[]
            setattr(copy_call, "typ", ExprType(typing.Any))
            self.expr_components.put(copy_call)

            # 인자를 빵꾸 뚫은거도 넣어야 하는데 ㅁㄴㅇㄻㄴㄻㄴㄹ

        super().generic_visit(node)
        return node

    def visit_Constant(self, node) :
        if self.generic_visit(node) :
            copy_node = copy.copy(node)
            setattr(copy_node, "typ", ExprType(typing.Any))
            self.expr_components.put(copy_node)
        
        super().generic_visit(node)
        return node

    def visit_Attribute(self, node) :
        if self.generic_visit(node) :
            copy_node = copy.deepcopy(node)
            setattr(copy_node, "typ", ExprType(typing.Any))
            self.expr_components.put(copy_node) # 변수 따라 설정할수 있는데..
        super().generic_visit(node)
        return node

    def visit_Subscript(self, node) :
        if self.generic_visit(node) :
            copy_node = copy.deepcopy(node)
            setattr(copy_node, "typ", ExprType(typing.Any))
            self.expr_components.put(copy_node)

            copy_node_value = copy.deepcopy(copy_node)
            new_hole_value = make_hole.make_expr_hole()
            setattr(new_hole_value, "typ", ExprType(typing.Iterable))
            copy_node_value.value = new_hole_value
            self.expr_components.put(copy.deepcopy(copy_node_value))

            copy_node_slice = copy.deepcopy(copy_node)
            new_hole_slice = make_hole.make_expr_hole()
            setattr(new_hole_slice, "typ", ExprType(slice))
            copy_node_slice.slice = new_hole_slice
            self.expr_components.put(copy.deepcopy(copy_node_slice))

            copy_node_all = copy.deepcopy(copy_node)
            copy_node_all.value = new_hole_value
            copy_node_all.slice = new_hole_slice
            self.expr_components.put(copy.deepcopy(copy_node_all))

        super().generic_visit(node)
        return node

    def visit_Name(self, node) :
        if self.generic_visit(node) :
            copy_node = copy.copy(node)
            setattr(copy_node, "typ", ExprType(typing.Any))
            self.expr_components.put(copy_node)

        super().generic_visit(node)
        return node 

    def visit_Slice(self, node) :
        if self.generic_visit(node) :

            setattr(node, "typ", ExprType(slice))

            has_lower = False
            if getattr(node, "lower", None) is not None :
                copy_node = copy.deepcopy(node)
                copy_node.lower = make_hole.make_expr_hole()
                setattr(copy_node.lower, "typ", ExprType(int))
                self.expr_components.put(copy_node)
                has_lower = True

            if getattr(node, "upper", None) is not None :
                copy_node = copy.deepcopy(node)
                copy_node.upper = make_hole.make_expr_hole()
                setattr(copy_node.upper, "typ", ExprType(int))
                self.expr_components.put(copy_node)

                if has_lower :
                    copy_node.lower = make_hole.make_expr_hole()
                    setattr(copy_node.lower, "typ", ExprType(int))
                    self.expr_components.put(copy.deepcopy(copy_node))

            delattr(node, "typ")

        super().generic_visit(node)

        return node
    '''
    extract_componets
    '''

    def extract_components(self, node) :
        self.only_stmt = False
        self.only_expr = False
        self.visit(node)

    def extract_stmt_components(self, node) :
        self.only_stmt = True
        self.visit(node)
        self.only_stmt = False

    def extract_expr_components(self, node) :
        self.only_expr = True
        self.visit(node)
        self.only_expr = False

    '''
    Add Default Component 
    '''
    def add_default_function(self) :
        default_funcs = [('len')]

        for func in default_funcs :
            if func == 'len' :
                args_hole = make_hole.make_expr_hole()
                setattr(args_hole, "typ", ExprType(typing.Iterable))

                self.expr_components.put(
                    ast.Call(
                        func=ast.Name(
                            id=func,
                            ctx=ast.Load()
                        ),
                        args = [
                            args_hole
                        ],
                        keywords=[],
                        typ=ExprType(int)
                    )
                )

    def add_default_type_convert(self) :
        default_types = [int, bool, str, float, list, tuple]

        for typ in default_types :
            new_hole = make_hole.make_expr_hole()
            self.expr_components.put(
                ast.Call(
                    func=ast.Name(
                        id=typ.__name__,
                        ctx=ast.Load()
                    ),
                    args = [
                        make_hole.make_expr_hole()
                    ],
                    keywords=[],
                    typ=ExprType(typ)
                )
            )

    def add_default_components(self) :
        self.stmt_components.put(ast.Pass())
        self.stmt_components.put(ast.Pass(hole=True))
        self.expr_components.put(ast.Name(id='True', ctx=ast.Load(), typ=ExprType(bool)))
        self.expr_components.put(ast.Name(id='False', ctx=ast.Load(), typ=ExprType(bool)))

        #self.add_default_type_convert()
        self.add_default_function()

    def add_var(self, var, typ=typing.Any) :
        # str -> Name ast
        self.expr_components.put(ast.Name(id=var, ctx=ast.Load(), typ=ExprType(locate(typ))))

    def add_typ(self, typ) :
        # str -> Call ast
        if typ == "None" :
            self.expr_components.put(
                ast.Name(
                    id=typ,
                    ctx=ast.Load(),
                    typ=ExprType(type(None))
                )
            )
        else :
            self.expr_components.put(
                ast.Call(
                    func=ast.Name(
                        id=typ,
                        ctx=ast.Load()
                    ),
                    args = [
                        make_hole.make_expr_hole()
                    ],
                    keywords=[],
                    typ=ExprType(locate(typ))
                )
            )

    '''
    Function
    '''
    def add_expr_component(self, component) :
        self.expr_components.put(component)

    def add_stmt_component(self, component) :
        self.stmt_components.put(component)

    def get_expr_components(self) :
        return self.expr_components.queue()

    def get_stmt_components(self) :
        return self.stmt_components.queue()
