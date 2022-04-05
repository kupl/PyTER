'''
Define my type
'''

from enum import Enum, unique
import typing

@unique
class Typing(Enum) :
    NONE = "none"
    INT = "int"
    FLOAT = "float"
    STR = "str"
    BOOL = "bool"
    ITERABLE = "iterable"
    SLICE = "slice"
    LIST = "list"
    TUPLE = "tuple"
    METHOD = "method"

class ExprType() :
    iterable = set([str, bytes, list, dict, tuple, set, slice, range, typing.Iterable])

    def __init__(self, typ) :
        self.typ = typing.Union[typ]

    def __str__(self) :
        return str(self.typ)

    def include(self, typ) :
        typ_set = set(typing.get_args(self.typ)) or set([self.typ])

        return (typ in typ_set)

    def union(self, other) :
        typ_set = set(typing.get_args(self.typ)) or set([self.typ])
        other_set = set(typing.get_args(other.typ)) or set([other.typ])

        if typing.Any in typ_set or typing.Any in other_set :
            self.typ = typing.Union[typing.Any]
        else :
            self.typ = typing.Union[tuple(typ_set.union(other_set))]

    def intersection(self, other) :
        typ_set = set(typing.get_args(self.typ)) or set([self.typ])
        other_set = set(typing.get_args(other.typ)) or set([other.typ])

        if typing.Any in other_set :
            pass
        elif typing.Any in typ_set :
            self.typ = other_set 
        else :
            self.typ = typing.Union[tuple(typ_set.intersection(other_set))]

    def check_iterable_type(self) :
        '''
        type에 iterable 타입이 있는지 체크
        '''
        for typ in (typing.get_args(self.typ) or [self.typ]) :
            if typ in ExprType.iterable :
                return True

        return False

    def match(self, other) :
        '''
        (ExprType -> bool)
        self.typ 매치 되는 타입이 other에 있는지 확인한다
        '''
        for typ in (typing.get_args(self.typ) or [self.typ]) :
            if typ is typing.Any :
                if other.typ is slice : # slice type이면 기각
                    continue

                return True

            if typ is typing.Iterable and other.check_iterable_type() :
                return True
            
            if other.include(typ) :
                return True

        return False

