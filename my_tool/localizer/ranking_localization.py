'''
최종 로컬라이제이션 정보 얻어오기
'''
from .sbfl import Sbfl 
from pprint import pprint

def get_candidate_line(filename, funcname, line, neg_localize) :
    '''
    역재생을 하여
    candidate line을 찾는 함숩니다
    '''

    candidate_line = []

    reverse_localize = list(reversed(neg_localize))
    trace_line = 0

    for text in reverse_localize :
        split_text = text.split()

        neg_filename = split_text[0]
        neg_funcname = split_text[1]
        neg_line = split_text[2]

        if trace_line > 0 :
            if filename == neg_filename and \
                funcname == neg_funcname and \
                trace_line > int(neg_line) :
                trace_line = int(neg_line)
                candidate_line.append((neg_filename, neg_funcname, neg_line))

        elif filename == neg_filename and \
            funcname == neg_funcname and \
            line == int(neg_line) :
            trace_line = line
            candidate_line.append((neg_filename, neg_funcname, neg_line))

    return candidate_line

def append_type_difference_to_sbfl(sbfl_info, type_difference_info) :
    for key, localize_list in sbfl_info.items() :
        new_localize_list = []
        for localize in localize_list :
            info_dict = dict()
            info_dict['info'] = type_difference_info
            info_dict['localize'] = localize

            new_localize_list.append(info_dict)

        sbfl_info[key] = new_localize_list

    return sbfl_info

def merge_localize(first, second) :
    for key, value in second.items() :
        if key in first :
            first[key].extend(value)
        else :
            first[key] = value

    return first

def get_ranking_localize(neg_localize, pos_localize, type_difference) :
    '''
    일반적으로
    argument를 분석해서 넘어왔을 때
    쓰는 localize
    '''
    dict_neg_localize = dict()
    for n in neg_localize :
        dict_neg_localize[n] = dict_neg_localize.get(n, 0) + 1

    ranking_localize = list()
    sbfl = Sbfl()

    prev_equal = None
    prev_diff = None

    sbfl_dict = dict()
    for t in type_difference :
        candidate_line = get_candidate_line(t['filename'], t['funcname'], t['line'], neg_localize)
        sbfl_info = sbfl.fault_localization(dict_neg_localize, pos_localize, candidate_line)
        #pprint(sbfl_info)
        sbfl_info = append_type_difference_to_sbfl(sbfl_info, t)
        
        if prev_equal is None and prev_diff is None :
            prev_equal = t['equal']
            prev_diff = t['diff_total']
            sbfl_dict = sbfl_info
            
        elif prev_equal == t['equal'] and prev_diff == t['diff_total'] :
            merge_localize(sbfl_dict, sbfl_info)
        
        else :
            prev_equal = t['equal']
            prev_diff = t['diff_total']
            ranking_localize.append(sbfl_dict)
            sbfl_dict = sbfl_info

    ranking_localize.append(sbfl_dict)

    return ranking_localize
