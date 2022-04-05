from localizer.sbfl import Sbfl
from pprint import pprint
from ast import unparse

class PyFixPrint() :
    type_diff = []
    func_diff = []
    error_anal = []
    func_anal = []
    def __init__(self) :
        pass

    def print_func_anal(self) :
        print("[[ START FUNC ANAL ]]")
        for (arg, info, score) in self.func_anal :
            (neg_typ, pos_typs, filename, funcname) = info
            (diff_s, equal_s) = score

            name = unparse(arg)

            print('Function : %30s Name : %15s Diff : %6s Equal : %6s Types : %40s' % (funcname, name, round(diff_s,4), round(equal_s,4), pos_typs))
        print("[[ END FUNC ANAL ]]")

    def print_error_anal(self) :
        print("[[ START ERROR ANAL ]]")
        skip = False
        for (_, funcname, var, _, diff_s, equal_s) in self.error_anal :
            if not skip and (diff_s == 0 or equal_s > 0) :
                skip = True
                self.print_func_anal()
            names = []
            types = []
            for var_name, typ in var.items() :
                names.append(unparse(var_name))
                types.extend(list(typ.keys()))
            print('Function : %30s Name : %15s Diff : %6s Equal : %6s Types : %40s' % (funcname, names, round(diff_s,4), round(equal_s,4), types))

        if not skip :
            skip = True
            self.print_func_anal()
        
        print("[[ END ERROR ANAL ]]")

    def print_func_diff(self) :
        print("[[ START FUNC DIFF ]]")
        skip = False
        for diff in self.func_diff :
            filename = diff['filename']
            funcname = diff['funcname']
            index = diff['index']
            line = "1st"
            diff_s = diff['diff_total']
            equal_s = diff['equal']

            if not skip and (diff_s == 0 or equal_s) > 0 :
                skip = True
                self.print_error_anal()
                break 

            print('Function : %30s Line : %4s Name : %15s Diff : %6s Equal : %6s' % (funcname, line, index, round(diff_s,4), round(equal_s,4)))

        if not skip :
            self.print_error_anal()

        print("[[ END FUNC DIFF ]]")

    def print_type_diff(self) :
        skip = False
        print("[[ START TYPE DIFF ]]")
        for type_diff in self.type_diff :
            for s, diff_list in type_diff.items() :
                for diff_info in diff_list : 
                    diff = diff_info['info']
                    loc = diff_info['localize']
                    filename = diff['filename']
                    funcname = diff['funcname']
                    name = diff['name']
                    line = loc[2]
                    diff_s = diff['diff_total']
                    equal_s = diff['equal']

                    if not skip and (diff_s == 0 or equal_s) > 0 :
                        skip = True
                        self.print_func_diff()
                    
                    print('Function : %30s Line : %4s Score : %6s Name : %15s Diff : %4s Equal : %4s' % (funcname, line, round(s, 6), name, diff_s, equal_s))

        if not skip :
            self.print_func_diff()
        
        print("[[ END TYPE DIFF ]]")

    def print_all(self) :
        self.print_type_diff()

def get_neg_line(neg_infos, localize) :
    candidate_line = []

    for text in localize :
        split_text = text.split()

        neg_filename = split_text[0]
        neg_funcname = split_text[1]
        neg_line = split_text[2]

        for neg_info in neg_infos :
            filename = neg_info['info']['filename']
            funcname = neg_info['info']['funcname']

            if filename == neg_filename and \
                funcname == neg_funcname :
                candidate_line.append(text)

    return candidate_line

def get_pos_line(neg_infos, localize) :
    candidate_line = dict()

    for text, n in localize.items() :
        split_text = text.split()

        neg_filename = split_text[0]
        neg_funcname = split_text[1]
        neg_line = split_text[2]

        for neg_info in neg_infos :
            filename = neg_info['info']['filename']
            funcname = neg_info['info']['funcname']

            if filename == neg_filename and \
                funcname == neg_funcname :
                candidate_line[text] = n

    return candidate_line

def print_sbfl(neg_localize, pos_localize, neg_infos) :
    print("[[ SBFL ]]")
    neg_cand = get_neg_line(neg_infos, neg_localize)
    
    pos_cand = get_pos_line(neg_infos, pos_localize)
    sbfl = Sbfl()

    dict_neg_localize = dict()
    for n in neg_cand :
        dict_neg_localize[n] = dict_neg_localize.get(n, 0) + 1


    sbfl_list = sbfl.calculate_score(dict_neg_localize, pos_cand, neg_infos)
    count = 1
    for score, values in sbfl_list.items() :
        for value in values :
            (filename, funcname, line) = value
            print('Function : %30s Line : %4s Score : %6s Count : %3s' % (funcname, line, round(score,4), count))
            count += 1