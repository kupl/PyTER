import ast
import itertools

def abstract_type(typ) :
    '''
    타입들을 추상화
    '''
    structure_list = ['List', 'Dict', 'Set', 'Tuple', 'Union', 'Optional']
    
    for s in structure_list :
        if typ.find(s) == 0 :
            return s
            
    if '::' in typ : # parent class 떼어내기
        typ_split = typ.split("::")
        return abstract_type(typ_split[0]) + "::" + abstract_type(typ_split[1])

    if typ == 'NoneType' :
        return 'None'

    return typ

def get_type_list(typ) :
    abs_typ = abstract_type(typ)

    if abs_typ == 'Optional' :
        remain_typ = typ[len('Optional')+1:-1]

        return get_type_list(remain_typ)

    if abs_typ == 'Union' :
        remain_typ = typ[len('Union')+1:-1]

        union_typs = remain_typ.split('/')

        cand_typ = []
        for union_typ in union_typs :
            cand_typ.extend(get_type_list(union_typ))

        return cand_typ
    
    return [abs_typ]

def abstract_type_list(typ_list) :
    return [abstract_type(typ) for typ in typ_list]

def abstract_dtype(dtype) :
    '''
    if 'int' in dtype :
        return 'integer'
    
    if 'float' in dtype :
        return 'floating'

    if 'complex' in dtype :
        return 'complexfloating'
    '''
    if '[ns]' in dtype :
        return dtype[:dtype.find('[ns]')]
    

    return dtype
    


def abstract_output_types(filename, classname, func_infos) :
    new_comments = list()
    type_comments = extract_func_type_comments(filename, classname, func_infos)

    for type_comment in type_comments :
        output_type = type_comment['type']
        input_type, output_type = split_input_output(output_type)

        new_comments.append(abstract_type(output_type))

    return new_comments

def abstract_input_types(filename, classname, func_infos) :
    new_comments = list()
    type_comments = extract_func_type_comments(filename, classname, func_infos)

    for type_comment in type_comments :
        input_type = type_comment['type']
        input_type, _ = split_input_output(input_type)
        

        new_comments.append(split_input_type(input_type))

    return new_comments

def split_input_origin_type(input_type) :
    split = input_type.split(',')
    new_type_comment = []

    for typ in split :
        #abs_type = abstract_type(typ)
        abs_type = typ.strip()
        new_type_comment.append(abs_type)

    return new_type_comment

def split_input_type(input_type) :
    split = input_type.split(',')
    new_type_comment = []

    for typ in split :
        abs_type = abstract_type(typ)
        abs_type = abs_type.strip()
        new_type_comment.append(abs_type)

    return new_type_comment

def split_input_output(type_comment) :
    split = type_comment.split('->')

    return split[0][1:-2], split[1][1:]

def extract_func_type_comments(filename, classname, func_infos) :
    for func_info in func_infos :
        path = func_info['path']
        func_name = func_info['func_name']

        if path in filename and func_name == classname :
            return func_info['type_comments']

    return []

def parse_dict_depth(typ, depth=1) :
    paren = 0
    for i, c in enumerate(typ) :
        if c == '[' :
            paren += 1
        
        if c == ']' :
            paren -= 1

        if c == '=' and depth == paren :
            return i

def dict_output_type(typ) :
    if abstract_type(typ) != 'Dict' :
        print("dict_output_type Error!!")
        return

    if typ == 'Dict' :
        return None

    parse_idx = parse_dict_depth(typ)

    output_type = typ[parse_idx+3:-1]

    return output_type

def is_numpy_type(typ) :
    return 'numpy' in typ

def is_ndarray_type(typ) :
    return 'ndarray' in typ

def is_class_type(typ) :
    typ = abstract_type(typ)
    return '.' in typ and (not is_numpy_type(typ))

def find_dtype(ndarray) :
    left = ndarray.find('<<')
    right = ndarray.find('>>')

    dtype = ndarray[(left+2):right]
    #print(dtype)
    return dtype



def dict_product(dicts):
    """
    >>> list(dict_product(dict(number=[1,2], character='ab')))
    [{'character': 'a', 'number': 1},
     {'character': 'a', 'number': 2},
     {'character': 'b', 'number': 1},
     {'character': 'b', 'number': 2}]
    """
    return (dict(zip(dicts, x)) for x in itertools.product(*dicts.values()))

class FindTargetFunc(ast.NodeVisitor) :
    def __init__(self, target) :
        self.target = target
        self.function_node = None

    def visit_AsyncFunctionDef(self, node) :
        prev = self.function_node
        self.function_node = node
        self.generic_visit(node)
        self.function_node = prev

    def visit_FunctionDef(self, node) :
        prev = self.function_node
        self.function_node = node
        self.generic_visit(node)
        self.function_node = prev

    def generic_visit(self, node) :
        if node is self.target :
            raise Exception

        super().generic_visit(node)

    def get_func(self, node) :
        try :
            self.visit(node)
        except :
            pass
        return self.function_node

class FindVarType(ast.NodeVisitor) :
    
    
    def __init__(self, target, type_info) :
        self.target_type = None
        self.target = target
        self.type_info = type_info

    def visit_Name(self, node) :
        if ast.unparse(node) == self.target :
            self.target_type = self.type_info.get(self.target, None)

    def visit_Attribute(self, node) :
        if ast.unparse(node) == self.target :
            self.target_type = self.type_info.get(self.target, None)

    def visit_Subscript(self, node) :
        if ast.unparse(node) == self.target :
            typ = self.type_info.get(ast.unparse(node.value), None)
            print(typ)
            print(dict_output_type(typ))
            self.target_type = self.type_info.get(ast.unparse(node.value), None)

    def get_target_type(self, node) :
        self.visit(node)

        return self.target_type