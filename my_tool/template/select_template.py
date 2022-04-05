'''
localize 된 정보를 기반으로
template을 선택하는
selector 입니다
'''

from type_analysis.type_difference import abstract_type
from type_analysis.custom_type_system import abstract_multiple_type, is_subset_type
from . import util
from copy import copy
from .util import Template, NONE_PATCH, TRY_PATCH, TYPE_CASTING, DEFAULT, INLOOP
from pprint import pprint

class Selector() :
    def __init__(self, neg_args, pos_samples, is_error_if_stmt, is_in_loop) :
        self.neg_args = neg_args # dict of (argname : type)
        self.pos_samples = pos_samples # list of sampling
        self.is_error_if_stmt = is_error_if_stmt # 에러가 if statement인가? => 이 정보랑 + 변수가 None => None check 먼저
        self.is_in_loop = is_in_loop # 뤂 안에 있으면 continue break 도 추가

    def scoring_args(self, diff) :
        '''
        가장 타입이 다른 변수들을 차례대로
        스코어링 할 겁니다

        *Todo
        타입이 다르다는 것을 어떻게 체크할 것인가?
        완전히 다르면?
        조금은 같아도 ㄱㅊ?
        '''

        scoring_args = dict() # {args : {typ1 : sample, typ2 : sample ...}} 

        for neg_arg, neg_types in self.neg_args.items() :
            #print("Neg : ",neg_type)

            scoring_args[neg_arg] = dict()
            scoring_args[neg_arg]['total'] = 0
            if diff :
                for typ, value in diff.items() :
                    #print("Pos : ",pos_type)
                    pos_type = abstract_type(typ)
                    for neg_type in neg_types :
                        neg_type = abstract_type(neg_type)
                        if neg_type != pos_type :
                            if not (pos_type in scoring_args[neg_arg]) : # 처음 본 타입이라면
                                scoring_args[neg_arg][pos_type] = 0
                            scoring_args[neg_arg][pos_type] += value

            else :
                for pos_sample in self.pos_samples :
                    pos_type = pos_sample['info'].get(neg_arg, False)

                    if pos_type :
                        #print("Pos : ",pos_type)
                        pos_type = abstract_type(pos_type)
                        for neg_type in neg_types :
                            neg_type = abstract_type(neg_type)
                            if neg_type != pos_type :
                                if not (pos_type in scoring_args[neg_arg]) : # 처음 본 타입이라면
                                    scoring_args[neg_arg][pos_type] = 0
                                scoring_args[neg_arg][pos_type] += pos_sample['samples']

            scoring_args[neg_arg]['total'] = sum(scoring_args[neg_arg].values())

        scoring_args = dict(sorted(scoring_args.items(), key=lambda x : x[1]['total'], reverse=True))

        for value in scoring_args.values() :
            del value['total']

        return scoring_args

    def select_except_strategy(self, arg_type) :
        return copy(DEFAULT)

    def scoring_template(self, diff=None) :
        '''
        scoring_args 기반으로
        type-casting,
        예외처리,
        ??
        를 고르는 것입니다
        '''
        scoring_template = list()
        args = self.scoring_args(diff)

        for arg, type_info in args.items() :
            result_templates = list()
            arg_types = self.neg_args[arg]

            # 묶음 패치
            # NotPos는 Negative 타입이 너무 다양하게 있던지,
            # neg >= pos 일 때 적용됩니다
            if type_info :
                import itertools
                subset_check = True
                for neg, pos in itertools.product(arg_types, type_info.keys()) :
                    subset_check = subset_check and is_subset_type(pos, neg)

                if subset_check :
                    result_templates.append((None, Template.NotPos))

                multiple_type = abstract_multiple_type(list(type_info.keys()))
                if multiple_type == 'numeric' :
                    pass
                elif multiple_type == 'iterable' :
                    pass
                elif multiple_type is None :
                    pass
                else :
                    # numpy upper type
                    result_templates.append((multiple_type, Template.NotPos))
                    result_templates.append((multiple_type, Template.NotPosTypeCasting))
                

            # negative 타입의 공통점을 찾아봅시다
            if len(arg_types) > 1 :
                multiple_type = abstract_multiple_type(arg_types)

                if multiple_type is None : # NotPos, try-except 넣기
                    if type_info :
                        result_templates.append((None, Template.NotPos))
                    result_templates.append((None, Template.AddException))
                elif multiple_type == 'numeric' :
                    pass
                elif multiple_type == 'iterable' :
                    pass
                else :
                    pass
                    #print("in select_template : ", multiple_type) 

            # 개별 패치
            arg_template = dict()
            for arg_type in arg_types :
                type_template = list()
                if self.is_error_if_stmt and arg_type == "None" :
                    type_template.append(Template.IfNoneCheck)
                    #scoring_template.append(((arg, type_info), [Template.IfNoneCheck]))

                

                if "::" in arg_type :
                    pass
                    #type_template.append(Template.SubClass)
                    #scoring_template.append(((arg, type_info), [Template.SubClass])) 

                tmp_template = list()

                len_keys = len(type_info.keys())
                if len_keys >= 2 : # 다양한 타입이 있다면...
                    tmp_template.extend(self.select_except_strategy(arg_type))
                elif len_keys == 1 :
                    #type_template.extend(TYPE_CASTING)
                    tmp_template.append(Template.TypeCasting)
                else :
                    tmp_template.extend(DEFAULT)

                if self.is_in_loop :
                    tmp_template.extend(INLOOP)
                    #scoring_template.append(((arg, type_info), INLOOP))

                if arg_type == "None" :
                    if len_keys == 1 :
                        tmp_template.extend(NONE_PATCH)
                    else :
                        tmp_template = NONE_PATCH + tmp_template

                tmp_template.append(Template.Return)

                

                #scoring_template.append(((arg, type_info), NONE_PATCH))

                arg_template[arg_type] = type_template + tmp_template

            template_list = list()

            for arg_typ, templates in arg_template.items() :
                typ_list = list()
                for template in templates :
                    typ_list.append((arg_typ, template))

                template_list.append(typ_list)

            import itertools
            for element in itertools.product(*template_list) :
                result_templates.append(element)

            scoring_template.append((arg, type_info, result_templates))

        return scoring_template


        