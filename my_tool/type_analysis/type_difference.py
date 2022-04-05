'''
type difference를 scoring 할것입니다
스코어링 조건

같은 타입 작은 순 -> 다른 타입 많은 순

'''
from functools import cmp_to_key
from iteration_utilities import unique_everseen
from pprint import pprint
from .util import abstract_type, split_input_type, split_input_origin_type, split_input_output, extract_func_type_comments




class FuncTypeDifference() :
    def __init__(self, neg_infos, neg_func, pos_func) :
        self.neg_infos = neg_infos
        self.neg_func = neg_func
        self.pos_func = pos_func



    '''
    Input 관련
    '''
    def get_input_origin_type(self, filename, classname, func_list) :
        new_comments = list()
        type_comments = extract_func_type_comments(filename, classname, func_list)

        for type_comment in type_comments :
            new_comment = dict()

            input_type = type_comment['type']
            input_type, _ = split_input_output(input_type)
            new_comment['type'] = split_input_origin_type(input_type)
            new_comment['samples'] = type_comment['samples']

            new_comments.append(new_comment)

        return new_comments

    def get_input_type(self, filename, classname, func_list) :
        new_comments = list()
        type_comments = extract_func_type_comments(filename, classname, func_list)

        for type_comment in type_comments :
            new_comment = dict()

            input_type = type_comment['type']
            input_type, _ = split_input_output(input_type)
            new_comment['type'] = split_input_type(input_type)
            new_comment['samples'] = type_comment['samples']

            new_comments.append(new_comment)

        return new_comments
        return []

    def sort_input_type_comment(self, first, second) :
        if first['equal'] > second['equal'] :
            return 1
        elif first['equal'] == second['equal'] :
            if first['diff_total'] > second['diff_total'] :
                return -1
            return 1
        return -1

    def scoring_input_type_comments(self) :
        '''
        result [
            {
                filename : str
                funcname : str
                index : int (몇번째 인자인지)
                diff : {
                    typ1 : int
                    typ2 : int
                }
                diff_total
                equal : int 
                typ : type
            }
        ]
        '''
        input_type_comments_list = list()

        for neg_info in self.neg_infos :
            filename = neg_info['info']['filename']
            funcname = neg_info['info']['funcname']
            classname = neg_info['info']['classname']
            neg_type_comments = self.get_input_type(filename, classname, self.neg_func)
            pos_type_comments = self.get_input_type(filename, classname, self.pos_func)

            for neg_type_comment in neg_type_comments :
                neg_input_type = neg_type_comment['type']

                diff = dict()
                diff_total = [0] * len(neg_input_type)
                equal = [0] * len(neg_input_type)

                for pos_type_comment in pos_type_comments :
                    pos_input_type = pos_type_comment['type']
                    

                    for i, (neg, pos) in enumerate(zip(neg_input_type, pos_input_type)) :
                        if neg == pos :
                            equal[i] += 1

                        else :
                            diff[i] = diff.get(i, dict())
                            diff[i][pos] = diff[i].get(pos, 0) + 1

                            diff_total[i] += 1
                
                for index, value in diff.items() :  
                    is_duplicate = False
                    for input_type_comments in input_type_comments_list :
                        # 여러 타입을 체킹해야하는지 보는것
                        if (filename == input_type_comments['filename'] and
                            funcname == input_type_comments['funcname'] and
                            index == input_type_comments['index'] and
                            diff_total[index] > 0 and equal[index] == 0) :
                            input_type_comments['typ'].append(neg_input_type[index])
                            is_duplicate = True
                            break

                    if is_duplicate :
                        continue
                    neg_info_dict = dict()         
                    neg_info_dict['filename'] = filename
                    neg_info_dict['funcname'] = funcname   
                    neg_info_dict['classname'] = classname       
                    neg_info_dict['index'] = index

                    
                    neg_info_dict['diff'] = value
                    neg_info_dict['diff_total'] = diff_total[index]
                    neg_info_dict['equal'] = equal[index]
                    neg_info_dict['typ'] = [neg_input_type[index]]

                    input_type_comments_list.append(neg_info_dict)


        input_type_comments_list = list(unique_everseen(input_type_comments_list))

        key_function = cmp_to_key(self.sort_input_type_comment)
        input_type_comments_list = sorted(input_type_comments_list, key=key_function)
        #input_type_comments_list = sorted(input_type_comments_list, key=lambda x: x['diff_total'] / ((x['equal']+1)**2), reverse=True)

        return input_type_comments_list          


                    


class TypeDifference() :
    def __init__(self, neg_infos, pos_infos) :
        self.neg_infos = neg_infos # dict of (argname : type)
        self.pos_infos = pos_infos # list of sampling

    def sort_args(self, first, second) :
        if first['equal'] > second['equal'] :
            return 1
        elif first['equal'] == second['equal'] :
            if first['diff_total'] > second['diff_total'] :
                return -1
            return 1
        
        return -1

    def scoring_args(self, neg_args, pos_info, scoring_neg_info, scoring_result) :
        '''
        가장 타입이 다른 변수들을 차례대로
        스코어링 할 겁니다

        *Todo
        타입이 다르다는 것을 어떻게 체크할 것인가?
        완전히 다르면?
        조금은 같아도 ㄱㅊ?

        diff : {
            typ1 : int
            typ2 : int
        }
        
        diff_total : int
        equal : int

        '''
        for neg_arg, neg_types in neg_args.items() :
            scoring_args = dict() 
            scoring_args['name'] = neg_arg
            scoring_args['diff'] = dict()
            scoring_args['diff_total'] = 0
            scoring_args['equal'] = 0

            for pos_sample in pos_info :
                pos_type = pos_sample['info'].get(neg_arg, False)

                if pos_type :
                    pos_type = abstract_type(pos_type)
                    for neg_type in neg_types :
                        neg_type = abstract_type(neg_type)
                        if neg_type != pos_type :
                            if not (pos_type in scoring_args['diff']) : # 처음 본 타입이라면
                                scoring_args['diff'][pos_type] = 0
                            scoring_args['diff'][pos_type] += pos_sample['samples']
                        else : # 같은 타입이면
                            scoring_args['equal'] += pos_sample['samples']

            if scoring_args['diff'] : # 정보가 있다면
                scoring_args['diff_total'] = sum(scoring_args['diff'].values())
            else :
                scoring_args['diff_total'] = 0

            scoring_args.update(scoring_neg_info)

            #scoring_tmp = dict()
            #scoring_tmp['args'] = scoring_args
            #scoring_tmp.update(scoring_neg_info)

            scoring_result.append(scoring_args)

        return scoring_result

    
    def scoring_by_function_line(self) :
        '''
        function, line 별 scoring 매깁니다

        
        result [
            {
                filename : str
                funcname : str
                name : str (인자 이름)
                diff : {
                    typ1 : int
                    typ2 : int
                }
                diff_total
                equal : int 
                typ : type
            }
        ]
    
        '''
        scoring_result = list()
        

        for neg_info in self.neg_infos :
            scoring_neg_info = dict()

            filename = neg_info['info']['filename']
            funcname = neg_info['info']['funcname']
            line = neg_info['info']['line']
            neg_args = neg_info['args']
            test = neg_info['idx']

            try :
                pos_info = self.pos_infos[filename][str(line)]
            except :
                pos_info = []

            scoring_neg_info['filename'] = filename
            scoring_neg_info['funcname'] = funcname
            scoring_neg_info['line'] = line
            scoring_neg_info['test'] = test

            scoring_result = self.scoring_args(neg_args, pos_info, scoring_neg_info, scoring_result)

        scoring_result = list(unique_everseen(scoring_result))

        key_function = cmp_to_key(self.sort_args)
        scoring_result = sorted(scoring_result, key=key_function)
        #scoring_result = sorted(scoring_result, key=lambda x : x['diff_total'] / ((x['equal']+1) ** 2))

        return scoring_result
