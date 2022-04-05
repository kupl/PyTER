'''
function entry에 타입캐스팅을 넣어주는 패치
'''
import ast 
from template.util import typ_str_modify 

class FunctionEntry(ast.NodeVisitor) :
    def __init__(self) :
        self.info = None
        self.classname_list = None
        self.only_func = False
        self.target_arg = None
        self.target_node = None
        self.all = False
        self.all_arg = dict()

    def visit_ClassDef(self, node) :
        if len(self.classname_list) > 0 and self.classname_list[0] == node.name :
            first = self.classname_list[0]
            self.classname_list = self.classname_list[1:]

            self.generic_visit(node)

            self.classname_list.insert(0, first)

    def visit_AsyncFunctionDef(self, node) :
        if self.all :
            if not self.all_arg : 
                if len(self.classname_list) == 0 and node.name == self.funcname :
                    try :
                        for i, arg in enumerate(node.args.args) :
                            

                            if arg.arg == 'self' :
                                continue
                            
                            self.all_arg[ast.arg(arg=arg.arg)] = i
                        self.target_node = node
                    except :
                        self.all_arg = dict()
                        self.target_node = None
        elif self.target_arg is None and self.target_node is None:
            if len(self.classname_list) == 0 and node.name == self.info['funcname'] and node.lineno <= self.lineno <= node.end_lineno:
                if self.only_func :
                    self.target_node = node
                    return

                args = node.args.args # 기본 argument

                try :
                    if args[0].arg == 'self' :
                        self.target_arg = args[self.info['index']+1].arg
                    else :
                        self.target_arg = args[self.info['index']].arg
                    self.target_node = node.body[0]
                except Exception as e:
                    #print("AsyncFunction Entry Error")
                    #print(e)
                    self.target_arg = None
                    self.target_node = None

        self.generic_visit(node)

    def visit_FunctionDef(self, node) :
        if self.all :
            if not self.all_arg : 
                if len(self.classname_list) == 0 and node.name == self.funcname :
                    try :
                        minus = 0
                        for i, arg in enumerate(node.args.args) :
                            if arg.arg == 'self' :
                                minus = 1
                                continue
                            
                            self.all_arg[ast.arg(arg=arg.arg)] = i - minus
                        
                        self.target_node = node
                    except :
                        self.all_arg = dict()
                        self.target_node = None

        elif self.target_arg is None and self.target_node is None:
            if len(self.classname_list) == 0 and node.name == self.info['funcname'] and node.lineno <= self.lineno <= node.end_lineno:
                if self.only_func :
                    self.target_node = node
                    return
                
                args = node.args.args # 기본 argument

                try :
                    if args[0].arg == 'self' :
                        self.target_arg = args[self.info['index']+1].arg
                    else :
                        self.target_arg = args[self.info['index']].arg
                    self.target_node = node.body[0]
                except Exception as e:
                    #print("Function Entry Error")
                    #print(e)
                    self.target_arg = None
                    self.target_node = None

        self.generic_visit(node)

    def get_function_entry_all(self, node, lineno, class_name, funcname) :
        self.lineno = lineno
        self.only_func = False
        self.all = True
        self.classname_list = class_name.split('.')[:-1]
        self.funcname = funcname

        self.visit(node)

        return self.all_arg, self.target_node

    def get_function_entry_info(self, info, node, lineno, only_func=False) :
        self.info = info
        self.lineno = lineno
        self.only_func = only_func
        self.classname_list = info['classname'].split('.')[:-1]

        self.visit(node)

        return self.target_arg, self.target_node