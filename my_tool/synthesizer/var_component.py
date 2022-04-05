import ast
from queue import PriorityQueue
from itertools import count
'''
var info : choose candidate var and expected typ!
'''

class VarComponent() :
    score_table = dict({
        "None" : 0,
        "int" : 1,
        "bool" : 1,
        "str" : 2
    })

    default_value = 10

    def __init__(self) :
        self.priority_queue = PriorityQueue()
        self.index = count(0)

    def __str__(self) :
        result = ""
        for item in self.priority_queue.queue :
            result = result + ("%s :: score : %s\n" % (item[2].__str__(), str(item[0])))

        return result

    def put(self, var_name, current_typ, expected_typ="Unknown", score=0) :
        var_info = VarInfo(var_name, current_typ, expected_typ)
        #score = self.get_priority(var_info) - score
        self.priority_queue.put((-score, next(self.index), var_info))

    def get(self) :
        return self.priority_queue.get()[2]

    def queue(self) :
        queue = list()

        for item in self.priority_queue.queue :
            queue.append(item[2])

        return queue

    def get_priority(self, var_info) :
        return self.score_table.get(var_info.get_current_typ(), self.default_value)

class VarInfo() :
    def __init__(self, var_name, current_typ, expected_typ) :
        self.var_name = var_name
        self.var_ast = self.var_to_ast(var_name)
        self.current_typ = current_typ
        self.expected_typ = expected_typ

    def __str__(self) :
        return "%s -> %s (Expected : %s)" % (self.var_name, self.current_typ, self.expected_typ)

    def var_to_ast(self, var_name) :
        '''
        var_name이 attr일수도 있어서 이거 고려해야됨
        '''

        var_attrs = var_name.split('.')

        def make_var_to_ast(attrs) :
            if len(attrs) == 1 :
                var_ast = ast.Name(id=attrs[0], ctx=ast.Load())
            else :
                attr = attrs[-1]
                other_attrs = attrs[:-1]

                var_ast = ast.Attribute(
                    value=make_var_to_ast(other_attrs),
                    attr=attr,
                    ctx=ast.Load()
                )

            return var_ast

        return make_var_to_ast(var_attrs)
            
    def get_name(self) :
        return self.var_name

    def get_var_ast(self) :
        return self.var_ast

    def get_current_typ(self) :
        return self.current_typ

    def get_expected_typ(self) :
        return self.expected_typ

    