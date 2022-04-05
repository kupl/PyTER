import ast
from copy import copy
from type_analysis.util import FindTargetFunc

class ContextAware() :
    def __init__(self, source_nodes, files) :
        self.source_genealogy_list = list()

        for source_node in source_nodes :
            #print(source_node)
            table = ContextGenealogy().get_score(files, source_node)
            #print(table)
            def depth_ast(root):
                return 1 + max((depth_ast(child)
                            for child in ast.iter_child_nodes(root)),
                        default = 0)
            self.source_genealogy_list.append((source_node, depth_ast(source_node), table))


        

    def extract_score(self, target_node, files) :
        result = list()
        
        target_genealogy = ContextGenealogy().get_score(files, target_node)

        if not target_genealogy :
            #print("context aware empty")
            return result
        target_score = sum(target_genealogy.values())

        for (source_node, depth, source_table) in self.source_genealogy_list :
            #print("?")
            between_score = 0
            for typ, score in target_genealogy.items() :
                between_score = min(score, source_table.get(typ, 0))

            result.append((source_node, between_score / target_score, depth))

        # sorting
        result.sort(key=lambda x : (x[1], -x[2]), reverse=True)
        return result

class ContextGenealogy(ast.NodeVisitor) :
    def __init__(self) :
        self.node_list = []
        self.parent_node = []
        self.target = None

    def generic_visit(self, node) :
        if self.parent_node : # 존재하면
            return

        if node is self.target :
            self.parent_node = self.node_list
            return 

        if isinstance(node, ast.Store) :
            return

        prev = copy(self.node_list)

        if isinstance(node, ast.FunctionDef) :
            self.node_list = []

        self.node_list.append(type(node))
        super().generic_visit(node)
        self.node_list = prev

    def get_score(self, files, node_list) :
        if not isinstance(node_list, list) :
            node_list = [node_list]

        genealogy_table = dict()

        for node in node_list :
            self.target = node
            for file in files :
                self.node_list = []
                self.parent_node = []
                self.visit(file)    

                for n in self.parent_node :
                    genealogy_table[n] = genealogy_table.get(n, 0) + 1

        return genealogy_table


#code = '''
#if True :
#    a = 3
#a = 2
'''
node = ast.parse(code)
ca = ContextGenealogy()

ca.visit(node)
'''