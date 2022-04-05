'''
기본 타입
[None, int, float, bool, str, bytes, list, set, tuple, dict, method, class]

numpy 타입
표 참고하세연 ㅋ

object = 복합 
'''

from .util import abstract_type, is_ndarray_type, is_numpy_type, find_dtype
from itertools import product

NUMERIC_LIST = set(['int', 'short', 'long', 'float', 'half', 'single', 'complex', 'number'])
iterable = set(['str', 'bytes', 'List', 'Set', 'Tuple', 'Dict', 'numpy'])

numpy_type_dict = {
    "genric" : {
        "bool" : {},
        "object" : {},
        "number" : {
            "integer" : {
                "signedinteger" : {
                    "byte" : {},
                    "short" : {},
                    "intc" : {},
                    "int" : {},
                    "longlong" : {}
                },

                "unsignedinteger" : {
                    "ubyte" : {},
                    "ushort" : {},
                    "uintc" : {},
                    "uint" : {},
                    "ulonglong" : {}
                }
            },

            "inexact" : {
                "floating" : {
                    "half" : {},
                    "single" : {},
                    "float" : {},
                    "longfloat" : {},
                },

                "complexfloating" : {
                    "csingle" : {},
                    "complex" : {},
                    "clongfloat" : {},
                }
            }
        },

        "flexible" : {
            "character" : {
                "str" : {},
                "unicode" : {}
            },

            "void" : {}
        },

        "datetime64" : {}
    }
}

def abstract_multiple_type(types) :
    abstract_types = set([abstract_type(t) for t in types])

    is_all_numpy = [is_numpy_type(typ) for typ in types]

    if False not in is_all_numpy :
        dtype = get_upper_numpy_type(types)
        if dtype is None :
            return None 
            
        if False not in [is_ndarray_type(typ) for typ in types] :
            return 'numpy.ndarray.multiple<<' + dtype + '>>'
        else :
            return 'numpy.multiple<<' + dtype + '>>'

    if abstract_types.issubset(NUMERIC_LIST) :
        return 'numeric'

    if abstract_types.issubset(iterable) :
        return 'iterable'

    return None

def get_numpy_dtype_list(type_dict, dtype) :
    result = list()
    for typ, lowers in type_dict.items() :
        if typ in dtype :
            return [typ]
        
        elif lowers :
            result = get_numpy_dtype_list(lowers, dtype)
            if result :
                return result + [typ]

    return None

def get_upper_numpy_type(types) : 
    dtype_list = [get_numpy_dtype_list(numpy_type_dict, find_dtype(typ)) for typ in types] 
    if None in dtype_list :
        return None

    for typ_list in product(*dtype_list) :
        typ_set = set(typ_list)
        if len(typ_set) == 1 :
            return list(typ_set)[0]

    return None


def is_subset_type(target, other) :
    target_type = abstract_type(target)
    other_type = abstract_type(other)

    if is_ndarray_type(other) :
        other_type = find_dtype(other)

    if is_ndarray_type(target) :
        target_type = find_dtype(target)

    # target이 other의 subset인가?
    if other_type == 'object' and target_type != 'object' :
        return True

    # subclass도 봅시다
    return False
