import ast

from synthesizer import synthesize, extract_info
from synthesizer.add_exception import AddException
from synthesizer.add_typecasting import AddTypeCasting
from synthesizer.add_guard import AddGuard
from synthesizer.get_function_entry_info import FunctionEntry
from synthesizer.template_synthesizer import TemplateSynthesizer


from type_analysis.error_analysis import ErrorAnalysis
from localizer import sbfl
from copy import copy, deepcopy
from context.context import ContextAware

from template.select_template import Selector
from template.template_to_ast import MakeTemplate
from template.util import Template, TemplateMethod, BASIC, TYPE_CASTING, IsInLoop, FindTemplate, FindSuspiciousNode, NONE_PATCH, FindIsInstance

from type_analysis.type_difference import TypeDifference, FuncTypeDifference
from type_analysis.type_chain import TypeChain
from type_analysis.msg_analysis import FindFuncFromType, ChangeArgument, PositionalUsage, AddKeywordArgument
from type_analysis.change_variable import ChangeVariable
from type_analysis.call_chain import CallChain
from type_analysis.util import FindTargetFunc, abstract_type_list, abstract_type
from type_analysis.var_type_inference import VarTypeInference

from localizer.ranking_localization import get_ranking_localize

from modify_code import FindUpperStmt

from pprint import pprint
import signal

from template.usage_analysis import UsageAnalysis

from print_localize import PyFixPrint, print_sbfl



class Work() :
    def __init__ (self, files_src, validate, files, neg_localize, pos_localize, pos_info, pos_func_infos, neg_infos, neg_func_infos, neg_msg, neg_additional, remain_test, total_test_num) :
        self.files_src = files_src
        self.validate = validate
        self.files = files
        self.neg_localize = neg_localize
        self.pos_localize = pos_localize
        self.pos_info = pos_info
        self.pos_func_infos = pos_func_infos
        #self.pos_localize = {}
        #self.pos_info = {}
        #self.pos_func_infos = {}
        self.neg_infos = neg_infos
        self.neg_func_infos = neg_func_infos
        self.neg_func_infos_origin = deepcopy(neg_func_infos)
        self.neg_msg = neg_msg
        self.neg_additional = neg_additional
        self.remain_test = remain_test
        self.total_test_num = total_test_num
        self.done_patch_only_once = False
        self.patch_file_dict = dict()

        self.neg_funcs = dict()

        self.stmt_hole_list = []

        self.print_loc = PyFixPrint()

    def get_neg_filename_funcname(self, neg_info) :
        return (neg_info['info']['filename'], neg_info['info']['funcname'])

    def msg_patch(self, synthe) :
        unexpected_keyword = 'got an unexpected keyword argument'
        required_positional = 'missing 1 required positional argument:'
        multiple_value = 'got multiple values for argument'

        msg_analyze = list()
        test = set()
        
        for msg_idx, neg_msg in enumerate(self.neg_msg) :
            if not msg_idx in self.remain_test :
                continue

            msg = neg_msg['msg']

            if unexpected_keyword in msg :
                msg_split = msg.split(unexpected_keyword)
                funcname = msg_split[0].strip().strip("()")
                funcname = funcname.split()[-1]
                argument = msg_split[1].strip().strip("'")

                test.add(msg_idx)
                msg_analyze.append(('keyword', funcname, argument))

            elif required_positional in msg :
                msg_split = msg.split(required_positional)
                funcname = msg_split[0].strip().strip("()")
                funcname = funcname.split()[-1]
                argument = msg_split[1].strip().strip("'")

                test.add(msg_idx)
                msg_analyze.append(('position', funcname, argument))

            elif multiple_value in msg :
                msg_split = msg.split(multiple_value)
                funcname = msg_split[0].strip().strip("()")
                funcname = funcname.split()[-1]
                argument = msg_split[1].strip().strip("'")

                test.add(msg_idx)
                msg_analyze.append(('multiple', funcname, argument))

        prev_remain_test = self.remain_test
        
        # 역으로 올라 가야함
        reverse_neg_infos = reversed(self.neg_infos)

        for i, neg_info in enumerate(self.neg_infos) :
            test = set(neg_info['idx'])
            if not test.issubset(self.remain_test) :
                continue 
            self.remain_test = self.remain_test - set(neg_info['idx'])

            #neg_info = self.neg_infos[0]
            neg_lineno = neg_info['info']['line']
            neg_filename = neg_info['info']['filename']
            neg_funcname = neg_info['info']['funcname']
            neg_args = neg_info['args']

            if 'test' in neg_filename and 'test' in neg_funcname : # test method만 있으면...
                # method or class 찾기
                for patch, funcname, argument in msg_analyze :
                    find_func = FindFuncFromType(funcname, neg_args, self.neg_func_infos)
                    
                    if funcname == '__init__' :
                        class_list = find_func.find_class()
                        class_init_list = [name+'__init__' for name in class_list]

                        for class_init in class_init_list :
                            for neg_func in self.neg_func_infos :
                                if class_init == neg_func['func_name'] :
                                    function_entry = FunctionEntry()
                                    info = {'classname' : class_init, 'funcname' : class_init.split('.')[-1]}

                                    try :
                                        file_node = deepcopy(self.files[neg_func['path']])
                                    except:
                                        with open(neg_func['path'], 'r', encoding='utf-8-sig') as f :
                                            file_node = ast.parse(f.read())
                                            self.files[neg_func['path']] = file_node

                                    _, entry_function = function_entry.get_function_entry_info(info, file_node, neg_func['line'], only_func=True)
                                    
                                    change = ChangeArgument(funcname, argument, file_node)
                                    ast_list = change.get_ast(entry_function)

                                    for node in ast_list :
                                        find_template = FindTemplate()
                                        targets = find_template.get_target(node)

                                        self.validate.validate(node, neg_func['path'], targets, test, self.total_test_num)
                    else :
                        method = find_func.find_method()

                        for neg_func in self.neg_func_infos :
                            if method == neg_func['func_name'] :
                                function_entry = FunctionEntry()
                                info = {'classname' : method, 'funcname' : method.split('.')[-1]}

                                try :
                                    file_node = deepcopy(self.files[neg_func['path']])
                                except :
                                    with open(neg_func['path'], 'r', encoding='utf-8-sig') as f :
                                        file_node = ast.parse(f.read())
                                        self.files[neg_func['path']] = file_node

                                _, entry_function = function_entry.get_function_entry_info(info, file_node, neg_func['line'], only_func=True)
                                
                                change = ChangeArgument(funcname, argument, file_node)
                                ast_list = change.get_ast(entry_function)

                                for node in ast_list :
                                    find_template = FindTemplate()
                                    targets = find_template.get_target(node)

                                    self.validate.validate(node, neg_func['path'], targets, test, self.total_test_num)
                
            else :
                try :
                    neg_file_node = deepcopy(self.files[neg_filename])
                except Exception as e :
                    return
                patch_usage = list()
                patch_list = dict()
                copy_dict = dict()
                for patch, funcname, argument in msg_analyze :
                    if (patch, funcname, argument) in patch_usage :
                        continue

                    if patch == 'keyword' :
                        # 대상 argument를 positional로 바꿔줘야함
                        reverse_neg_infos = reversed(self.neg_infos)
                        keyword_usage_func_infos= list()

                        for neg_info in reverse_neg_infos :
                            # 이 arguemnt를 쓴 적이 있는 파일을 대상으로 분석하기
                            neg_lineno = neg_info['info']['line']
                            neg_funcname = neg_info['info']['funcname']
                            neg_filename = neg_info['info']['filename']
                            neg_classname = neg_info['info']['classname']

                            if not copy_dict.get(neg_filename, False) :
                                try :
                                    copy_node = deepcopy(self.files[neg_filename])
                                    copy_dict[neg_filename] = copy_node
                                except :
                                    continue
                            
                            neg_file_node = self.files[neg_filename]

                            function_entry = FunctionEntry()
                            info = {'classname' : neg_classname, 'funcname' : neg_funcname}
                            _, entry_function = function_entry.get_function_entry_info(info, neg_file_node, neg_lineno, only_func=True)
                            
                            usage = PositionalUsage(argument)
                            keyword_list = usage.get_keyword_list(entry_function)

                            if keyword_list :
                                keyword_usage_func = dict()
                                keyword_usage_func['origin'] = neg_file_node
                                keyword_usage_func['filename'] = neg_filename
                                keyword_usage_func['node'] = entry_function
                                keyword_usage_func['keywords'] = keyword_list
                                keyword_usage_func['argument'] = argument

                                keyword_usage_func_infos.append(keyword_usage_func)
                        
                        keyword_patch_list = patch_list.get(patch, list())
                        keyword_patch_list.append(keyword_usage_func_infos)
                        patch_list[patch] = keyword_patch_list
                        # argument를 쓴 함수들을 순차적으로 keyword argument를 등록해서 이어주면 됨 

                    elif patch == 'position' :
                        if not copy_dict.get(neg_filename, False) :
                            copy_node = deepcopy(self.files[neg_filename])
                            copy_dict[neg_filename] = copy_node

                        error_stmt = extract_info.find_error_stmt(neg_file_node, neg_lineno)

                        patch_set = patch_list.get(patch, set([]))
                        patch_set.add((neg_file_node, neg_filename, error_stmt, funcname, argument))
                        patch_list[patch] = patch_set

                    elif patch == 'multiple' :
                        if not copy_dict.get(neg_filename, False) :
                            copy_node = deepcopy(self.files[neg_filename])
                            copy_dict[neg_filename] = copy_node

                        error_stmt = extract_info.find_error_stmt(neg_file_node, neg_lineno)

                        patch_set = patch_list.get(patch, set([]))
                        patch_set.add((neg_file_node, neg_filename, error_stmt, funcname, argument))
                        patch_list[patch] = patch_set
                
                add_keyword = AddKeywordArgument(patch_list) # general로 바꿔야함
                ast_list = add_keyword.get_ast_list()

                for node in ast_list :
                    all_targets = list()
                    for target, _ in node :
                        find_template = FindTemplate()
                        targets = find_template.get_target(target)
                        all_targets.extend(targets)

                    self.validate.multiple_file_validate(node, all_targets, test, self.total_test_num)

                for filename, node in copy_dict.items() :
                    self.files[filename] = node

        self.remain_test = prev_remain_test        
            #exit()

        # localize 역으로 가면서 return이 neg_type인거 찾기

    def extract_func_var_type(self) :
        file_dict = dict()
        for neg_info in self.neg_infos :
            neg_filename = neg_info['info']['filename']
            neg_funcname = neg_info['info']['funcname']
            neg_classname = neg_info['info']['classname']
            neg_lineno = neg_info['info']['line']
            neg_args = neg_info['args']

            test = set(neg_info['idx'])

            if not test.issubset(self.remain_test) :
                continue 
            #prev_remain_test = self.remain_test
            #self.remain_test = self.remain_test - test

            try :
                neg_file_node = deepcopy(self.files[neg_filename])
            except Exception as e :
                print(neg_filename, "not exists")
                continue
           

            entry = FunctionEntry()
            all_arg, target_node = entry.get_function_entry_all(neg_file_node, neg_lineno, neg_classname, neg_funcname)


            func_type_extract = FuncTypeDifference(self.neg_func_infos_origin, None, None)
            func_types = func_type_extract.get_input_origin_type(neg_filename, neg_classname, self.neg_func_infos)

            arg_dict = dict()
            for arg, index in all_arg.items() :
                typ_list = set([])
                for func_type in func_types :
                    sample_num = func_type['samples']
                    try :
                        arg_typ = func_type['type'][index]
                    except Exception as e:
                        continue

                    typ_list.add(arg_typ)
                
                arg_dict[(arg)] = typ_list

            file_dict[(neg_filename, neg_funcname)] = arg_dict

        self.neg_funcs = file_dict

    def func_spec_inference(self, synthe) :
        final_list = []
        for neg_info in self.neg_infos :
            neg_filename = neg_info['info']['filename']
            neg_funcname = neg_info['info']['funcname']
            neg_classname = neg_info['info']['classname']
            neg_lineno = neg_info['info']['line']
            neg_args = neg_info['args']

            test = set(neg_info['idx'])

            if not test.issubset(self.remain_test) :
                continue 
            #prev_remain_test = self.remain_test
            #self.remain_test = self.remain_test - test

            try :
                neg_file_node = deepcopy(self.files[neg_filename])
            except Exception as e :
                print(neg_filename, "not exists")
                continue

            entry = FunctionEntry()
            all_arg, target_node = entry.get_function_entry_all(neg_file_node, neg_lineno, neg_classname, neg_funcname)

            func_type_extract = FuncTypeDifference(self.neg_func_infos, None, None)
            func_types = func_type_extract.get_input_type(neg_filename, neg_classname, self.neg_func_infos)

            result_dict = dict()

            candidate_args = deepcopy(neg_args)

            for (filename, funcname), item in self.neg_funcs.items() :
                if filename == neg_filename and funcname == neg_funcname :
                    for arg, typs in item.items() :
                        arg_name = ast.unparse(arg)
                        if arg_name in candidate_args :
                            continue
                        candidate_args[arg_name] = list(typs)

            for arg, index in all_arg.items() :
                var_type_inference = VarTypeInference(arg, candidate_args, "", is_arg=True)
                arg_typ_dict = var_type_inference.get_arg_type(target_node)

                sorted_dict = sorted(arg_typ_dict.items(), key = lambda item: item[1], reverse = True)

                

                max_score = 0
                candidate_type = []
                sum_score = 0
                for typ, score in sorted_dict :
                    sum_score += score
                    if score > max_score :
                        max_score = score
                    
                    if score < max_score :
                        continue
                    
                    candidate_type.append(typ)

                for func_type in func_types :
                    sample_num = func_type['samples']
                    try :
                        arg_typ = func_type['type'][index]
                    except Exception as e:
                        continue

                    abs_typ = abstract_type(arg_typ)
                    abs_cand_typs = abstract_type_list(candidate_type)
                    abs_cand_typs = sorted(abs_cand_typs)
                    abs_cand_typs = tuple(abs_cand_typs)

                    value = max_score / max(sum_score, 1)

                    eq_s = 0
                    diff_s = 0
                    for abs_cand_typ in abs_cand_typs :
                        if abs_cand_typ == abs_typ :
                            eq_s += 1
                        else :
                            diff_s += 1

                    arg_dict = result_dict.get(arg, dict())
                    (diff_so, eq_so) = arg_dict.get((abs_typ, abs_cand_typs, neg_filename, neg_funcname), (0,0))
                    arg_dict[(abs_typ, abs_cand_typs, neg_filename, neg_funcname)] = (diff_so + (value * diff_s * sample_num), eq_so + (value * eq_s * sample_num))
                    result_dict[arg] = arg_dict

            sorted_dict = sorted(result_dict.items(), key = lambda item: (-list(item[1].values())[0][1], list(item[1].values())[0][0]), reverse = True)
            #sorted_dict = sorted(result_dict.items(), key = lambda item: list(item[1].values())[0][0] / ((1 + list(item[1].values())[0][1]) ** 2), reverse = True)

            final_list.extend(sorted_dict)

        real_final_list = list()

        for (arg, info_dict) in final_list :
            for key, value in info_dict.items() :
                real_final_list.append((arg, key, value))

        #final_list = sorted(final_list, key=lambda item: (-list(item[1].values())[0][1], list(item[1].values())[0][0]), reverse=True)

        final_list = sorted(real_final_list, key=lambda item: (-item[2][1], item[2][0]), reverse=True)
        #final_list = sorted(real_final_list, key=lambda item: item[2][0] / ((1+item[2][1]) ** 2), reverse=True)

        #pprint(final_list)
        #input()

        #self.print_loc.func_anal = final_list
        #return

        for (key, info, _) in final_list :
            target_arg = ast.unparse(key)

            (neg_typ, pos_typs, filename, funcname) = info
            #for (neg_typ, pos_typs, filename, funcname) in info.keys() :
            for neg_info in self.neg_infos :
                neg_filename = neg_info['info']['filename']
                neg_funcname = neg_info['info']['funcname']

                if not (neg_filename == filename and neg_funcname == funcname) :
                    continue 

                neg_classname = neg_info['info']['classname']
                neg_lineno = neg_info['info']['line']
                neg_args = neg_info['args']

                test = set(neg_info['idx'])
                if not test.issubset(self.remain_test) :
                    continue 
                prev_remain_test = self.remain_test
                self.remain_test = self.remain_test - test

                neg_file_node = deepcopy(self.files[neg_filename])

                entry = FunctionEntry()
                _, target_node = entry.get_function_entry_all(neg_file_node, neg_lineno, neg_classname, neg_funcname)

                target_node = target_node.body[0]

                template = []
                if len(pos_typs) != 1 :
                    template = [Template.Return]
                template.extend(TYPE_CASTING)

                import itertools
                templates = list()
                candidate_template = template

                if "::" in neg_typ :
                    tmp_typ = neg_typ.split("::")[-1]

                    if 'collections.abc' in tmp_typ : # 상위의 타입
                        # 하위 타입이랑 비슷하게 처리할 거임 그걸 찾아야함
                        find_func = FindTargetFunc(target_node)
                        target_func = find_func.get_func(neg_file_node)

                        target_func.body.insert(0, ast.ImportFrom(
                            module='collections', 
                            names=[ast.alias(name='abc')], 
                            level=0
                        ))

                        type_set = [('Mapping', ['dict']), ('Iterable', ['list', 'tuple']), ('Set', ['set'])]

                        for (upper_typ, lower_typs) in type_set :
                            if upper_typ in tmp_typ :
                                for lower_typ in lower_typs :
                                    find_isinstance = FindIsInstance(target_arg, lower_typ)
                                    isinstance_list = find_isinstance.get_isinstance(target_func)

                                    for isinstance_stmt in isinstance_list :
                                        test_origin = isinstance_stmt.test
                                        isinstance_stmt.test = ast.BoolOp(
                                            op=ast.Or(),
                                            values=[
                                                test_origin,
                                                ast.Call(
                                                    func=ast.Name(id='isinstance', ctx=ast.Load()),
                                                    args=[
                                                        ast.Name(id=target_arg, ctx=ast.Load()),
                                                        ast.Name(id='abc.' + upper_typ, ctx=ast.Load())
                                                    ],
                                                    keywords=[]
                                                )
                                            ],
                                            mark=True
                                        )

                                        targets = isinstance_stmt.test
                                        self.validate.validate(neg_file_node, neg_filename, targets, test, self.total_test_num)
                                        isinstance_stmt.test = test_origin
                        
                        del target_func.body[0]




                templates.append([(neg_typ, template) for template in candidate_template])
                #templates.extend(list(itertools.product([neg_typ], candidate_template)))
    
                find_func = FindTargetFunc(target_node)
                target_func = find_func.get_func(neg_file_node)

                typecheck_candidates = extract_info.extract_isinstance_stmt_info(target_func)
                context_aware = ContextAware(typecheck_candidates, [neg_file_node])
                pos_typs_dict = dict()

                for pos_typ in pos_typs :
                    pos_typs_dict[pos_typ] = 1

                for template in itertools.product(*templates) :
                    make_template = MakeTemplate(neg_file_node, target_arg, neg_typ, pos_typs_dict, template, neg_args, self.pos_func_infos)
                    ast_list = make_template.get_ast_list(neg_funcname, target_node)

                    for node in ast_list :
                        synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_info['args'], self.pos_func_infos, None, context_aware, None, None, test, self.total_test_num, func_patch=True)

                self.remain_test = prev_remain_test

            


    def spec_inference(self, synthe, ranking_localize) :
        self.extract_func_var_type()
        #self.func_spec_inference(synthe)
        #print("[[[ Patch Only Once ]]]")

        # error_analysis
        patch_candidate = []

        for neg_info in self.neg_infos :
            neg_filename = neg_info['info']['filename']
            neg_funcname = neg_info['info']['funcname']
            neg_lineno = neg_info['info']['line']

            try :
                neg_file_node = self.files[neg_filename]
            except Exception as e :
                print(neg_filename, "not exists")
                continue

            test = set(neg_info['idx'])

            if not test.issubset(self.remain_test) :
                continue 

            neg_args = neg_info['args']

            candidate_args = deepcopy(neg_args)

            for (filename, funcname), item in self.neg_funcs.items() :
                if filename == neg_filename and funcname == neg_funcname :
                    for arg, typs in item.items() :
                        arg_name = ast.unparse(arg)
                        if arg_name in candidate_args :
                            continue
                        candidate_args[arg_name] = list(typs)

            error_stmt = extract_info.find_error_stmt(neg_file_node, neg_lineno)

            error_analysis = ErrorAnalysis(candidate_args, neg_file_node, self.pos_func_infos)
            var_score, operator_mutate = error_analysis.extract_score(error_stmt)


            if var_score or operator_mutate :
                if not var_score :
                    var_score['empty'] = {'empty' : -1} 

                for target, diff in var_score.items() :
                    if not diff :
                        continue
                    elif target == 'empty' : 
                        #continue
                        patch_candidate.append((neg_filename, neg_funcname, {}, operator_mutate, -1, 1))
                    elif not target == 'empty' :
                        max_value =  list(diff.values())[0]
                        total_sum = sum(list(diff.values()))
                        cur_score = 0
                        score_dict = dict()

                        type_list = neg_args.get(ast.unparse(target), [])
                        type_list = abstract_type_list(type_list)


                        for key, value in diff.items() :
                            if value < max_value :
                                break 
                            
                            cur_score = value * len(test) * (1 if len(type_list) == 0 else len(type_list))
                            #cur_score = value * len(test) * (1 if len(type_list) == 0 else len(type_list))
                            score_dict[key] = cur_score + 1

                        equal_score=0
                        diff_score=0
                        for typ in type_list :
                            for infer, score in score_dict.items() :
                                if typ == infer :
                                    equal_score += score
                                else :
                                    diff_score += score

                        #patch_candidate.append((neg_filename, neg_funcname, {target : score_dict}, operator_mutate, diff_score, equal_score))
                        patch_candidate.append((neg_filename, neg_funcname, {target : score_dict}, operator_mutate, diff_score, equal_score))
                    #total_score = sum(diff.values())

                    #for k, v in diff.items() :
                    #    score_dict = dict()

                    #    if not target == 'empty' :
                    #        score_dict[target] = {k : v }
                    #    patch_candidate.append((neg_filename, neg_funcname, score_dict, operator_mutate, v ))

        
        patch_candidate = sorted(patch_candidate, key=lambda x : (-x[5], x[4], x[3] == set([])), reverse=True)
        #patch_candidate = sorted(patch_candidate, key=lambda x : (x[4] / ((1+x[5]) ** 2), x[3] == set([])), reverse=True)
        is_run_func_spec = False

        #for (_, _, d, _, _, _) in patch_candidate :
        #    for key, value in d.items() :
        #        print(ast.unparse(key))
        #        print(value)
        #input()

        self.print_loc.error_anal = patch_candidate

        for (neg_filename, neg_funcname, var_score, operator_mutate, diff, equal) in patch_candidate :
            if diff == 0 or equal > 0 :
                self.func_spec_inference(synthe)
                is_run_func_spec = True

            #continue
            # Find SBFL
            sbfl_list = []
            localize_name = None

            for rank_by_type in ranking_localize :
                for localize_list in rank_by_type.values() :
                    line_list = []
                    for localize in localize_list :
                        (filename, funcname, localize_line) = localize['localize']

                        if not (neg_filename == filename and neg_funcname == funcname) :
                            continue 

                        if localize_name is None :
                            localize_name = localize['info']['name']
                        line_list.append(int(localize_line))

                    if line_list :
                        sbfl_list = line_list
                        break
                
                if sbfl_list :
                    break

            for neg_info in self.neg_infos :
                filename = neg_info['info']['filename']
                funcname = neg_info['info']['funcname']

                if not (neg_filename == filename and neg_funcname == funcname) :
                    continue

                neg_lineno = neg_info['info']['line']
                neg_classname = neg_info['info']['classname']
                neg_args = neg_info['args']
                neg_file_node = deepcopy(self.files[neg_filename])

                test = set(neg_info['idx'])
                if not test.issubset(self.remain_test) :
                    continue 
                prev_remain_test = self.remain_test
                self.remain_test = self.remain_test - test



                        
                '''
                print("[[[ Error Analysis ]]]")
                for var, typ in var_score.items() :
                    print(ast.unparse(var), typ)
                input()
                '''
                for localize_line in sbfl_list :
                    neg_file_node = deepcopy(self.files[neg_filename])
                    error_stmt = extract_info.find_error_stmt(neg_file_node, localize_line)

                    from type_analysis.util import FindTargetFunc
                    find_func = FindTargetFunc(error_stmt)
                    target_func = find_func.get_func(neg_file_node)

                    typecheck_candidates = extract_info.extract_isinstance_stmt_info(target_func)
                    #print(neg_file_node)
                    context_aware = ContextAware(typecheck_candidates, [neg_file_node])


                    suspicious = FindSuspiciousNode(error_stmt)
                    stmt_list_list, if_list, error_if_stmt = suspicious.get_node_list(neg_file_node)

                    is_should_fix = None

                    for stmt_list in stmt_list_list :
                        usage = UsageAnalysis(localize_name)
                        #usage = UsageAnalysis(localize['info']['name'], neg_lineno)
                        for stmt in stmt_list :
                            should_fix, target_stmt = usage.get_stmt(stmt)
                            if should_fix is not None :
                                is_should_fix = should_fix
                                break

                        if is_should_fix is not None :
                            break

                    usage = UsageAnalysis(localize_name)
                    for if_stmt in if_list :
                        if is_should_fix : 
                            break

                        if if_stmt == error_if_stmt :
                            if error_stmt in if_stmt.body:
                                if len(if_stmt.orelse) == 1 and isinstance(if_stmt.orelse[0], ast.If) :
                                    continue

                                new_stmt = ast.If(
                                    test=if_stmt.test,
                                    body=ast.Pass(),
                                    orelse=if_stmt.orelse
                                )
                                should_fix, target_stmt = usage.get_stmt(new_stmt)

                            elif error_stmt in if_stmt.orelse :
                                new_stmt = ast.If(
                                    test=if_stmt.test,
                                    body=if_stmt.body,
                                    orelse=[]
                                )
                                should_fix, target_stmt = usage.get_stmt(new_stmt)
                        else :
                            should_fix, target_stmt = usage.get_stmt(if_stmt)

                        if should_fix is not None :
                            is_should_fix = should_fix
                            break

                    if is_should_fix is True :
                        # 가장 앞에 있는 코드 찾기
                        fastest_line = error_if_stmt.lineno
                        target_stmt = error_if_stmt

                        for if_stmt in if_list :
                            if fastest_line > if_stmt.lineno :
                                fastest_line = if_stmt.lineno
                                target_stmt = error_if_stmt

                        self.change_localize(target_stmt, fastest_line, neg_args, neg_file_node, neg_funcname, neg_filename, neg_funcname, neg_classname, test, synthe, var_score=var_score)

                    # Add Neg Guard
                    if isinstance(error_stmt, ast.If) :
                        add_guard = AddGuard(neg_file_node)
                        complete_list = add_guard.get_guard_list(var_score, neg_args, error_stmt)

                        for node in complete_list :
                            find_template = FindTemplate()
                            targets = find_template.get_target(node)

                            self.validate.validate(node, neg_filename, targets, test, self.total_test_num)

                    add_typecasting = AddTypeCasting()
                    complete_list = add_typecasting.get_typecasting_list(var_score, neg_args, neg_file_node)
                    


                    # 단순 TypeCasting
                    for node in complete_list :
                        find_template = FindTemplate()
                        targets = find_template.get_target(node)

                        self.validate.validate(node, neg_filename, targets, test, self.total_test_num)


                    # 단순 operator mutate
                    if localize_line == neg_lineno :
                        for (op_node, ops, _) in operator_mutate :
                            prev_op = op_node.op
                            find_template = FindTemplate()
                            op_node.mark = True
                            for op in ops :
                                op_node.op = op()
                                targets = [op_node]
                                self.validate.validate(neg_file_node, neg_filename, targets, test, self.total_test_num)

                            op_node.op = prev_op
                            del op_node.mark

                    # 변수 변경
                    for target_node, diff in var_score.items() :
                        for typ, count in diff.items() :
                            change = ChangeVariable(neg_args)

                            ast_list = change.change_variable(neg_file_node, target_node, neg_args.get(ast.unparse(target_node), ['None']), typ)

                            for node in ast_list :
                                find_template = FindTemplate()
                                targets = find_template.get_target(node)
                                self.validate.validate(node, neg_filename, targets, test, self.total_test_num)            

                    # Template 만들어서

                    for target_node, diff in var_score.items() :
                        len_keys = len(diff.keys())

                        templates = []
                        #templates = copy(TYPE_CASTING) 

                        target_arg = ast.unparse(target_node)

                        target_typ = neg_args.get(target_arg, ['None'])

                        if not target_typ :
                            continue
                            #if diff : 
                            #    continue

                            # 없으면 내가 억지로 추가한거임
                            #target_typ = ['None']

                        

                        error_is_if_stmt = False
                        if isinstance(error_stmt, ast.If) :
                            error_is_if_stmt = True

                        if 'None' in target_typ :
                            if error_is_if_stmt == True :
                                templates.append(Template.IfNoneCheck)
                            templates.extend(NONE_PATCH)

                        templates.extend(TYPE_CASTING)
                        if len_keys >= 2 :
                            templates.append(Template.Return)

                        check_loop = IsInLoop()
                        is_in_loop = check_loop.isin_loop(int(localize_line), neg_file_node)

                        selector = Selector({target_arg: target_typ}, diff, error_is_if_stmt, is_in_loop)
                        score_templates = selector.scoring_template(diff=diff)

                        '''
                        미리 모으기
                        '''

                        
                        if target_arg == 'self' :
                            continue 

                        candidate_templates = list()
                        import itertools
                        candidate_templates.extend(list(itertools.product(target_typ, copy(BASIC))))

                        for template in candidate_templates :
                            make_template = MakeTemplate(neg_file_node, target_arg, target_typ, dict(), [template], neg_args, self.pos_func_infos)
                            ast_list = make_template.get_ast_list(neg_funcname, error_stmt)

                            if ast_list is None :
                                continue

                            self.stmt_hole_list.extend([(node, neg_filename, neg_funcname, neg_classname, neg_args, neg_file_node, error_stmt) for node in ast_list])
                        
                        #if "::" in target_typ :
                        #    templates.append(Template.SubClass)

                        candidate_templates = list()
                        import itertools
                        candidate_templates.extend(list(itertools.product(target_typ, templates)))

                        for template in candidate_templates :
                            make_template = MakeTemplate(neg_file_node, target_arg, target_typ, diff, [template], neg_args, self.pos_func_infos)
                            ast_list = make_template.get_ast_list(neg_funcname, error_stmt)

                            for node in ast_list :
                                synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, context_aware, None, None, test, self.total_test_num)
                    
                        for (arg, arg_typ_info, templates) in score_templates :
                            #print(arg, arg_typ_info, templates)
                            for template in templates :
                                if len(template) >= 3 :
                                    continue
                                    # only multiple patch

                                make_template = MakeTemplate(neg_file_node, arg, neg_args.get(arg, ['None']), arg_typ_info, template, neg_args, self.pos_func_infos)
                                ast_list = make_template.get_ast_list(funcname, error_stmt)
                                if ast_list is None :
                                    continue

                                if len(template) == 2 and template[1] in TemplateMethod.Multiple.value :
                                    self.stmt_hole_list.extend([(node, neg_filename, neg_funcname, neg_classname, neg_args, neg_file_node, error_stmt) for node in ast_list])

                                for node in ast_list :
                                    #continue
                                    '''
                                    Synthesis
                                    '''
                                    components = None
                                    synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, context_aware, None, self.neg_additional, test, self.total_test_num)


                    
                    # Template 만들어서 operator mutate
                    for (op_node, ops, args_node) in operator_mutate :
                        templates = [Template.OpMutate]

                        for arg_node in args_node :
                            target_arg = ast.unparse(arg_node)
                            target_typ = neg_args[target_arg]

                            candidate_templates = list()
                            import itertools
                            candidate_templates.extend(list(itertools.product(target_typ, templates)))

                            for template in candidate_templates :
                                make_template = MakeTemplate(neg_file_node, target_arg, target_typ, (op_node, ops), [template], neg_args, self.pos_func_infos)
                                ast_list = make_template.get_ast_list(neg_funcname, error_stmt)

                                for node in ast_list :
                                    synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, context_aware, None, None, test, self.total_test_num)

                    # Type Chain
                    for target_node in var_score.keys() :
                        type_chain = TypeChain(self.neg_localize, neg_filename, target_node, neg_file_node, target_node, self.neg_func_infos, self.pos_func_infos)
                        chain_result = type_chain.get_type_chain(neg_file_node)

                        '''
                        print("[[[ Type Chain ]]]")
                        pprint(chain_result)
                        input()
                        '''

                        if chain_result :
                            error_stmt = chain_result[0]
                            target_arg = chain_result[1][0]
                            type_info = chain_result[1][1]
                            templates = copy(TYPE_CASTING)

                            for neg_type in type_info[0] :
                                #if "::" in neg_type :
                                #    templates.append(Template.SubClass)

                                diff_info = type_info[1]

                                candidate_templates = list()
                                import itertools
                                candidate_templates.extend(list(itertools.product([neg_type], templates)))

                                for template in candidate_templates :
                                    make_template = MakeTemplate(neg_file_node, target_arg, neg_type, diff_info, [template], neg_args, self.pos_func_infos)
                                    ast_list = make_template.get_ast_list(neg_funcname, error_stmt)

                                    for node in ast_list :
                                        synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, None, None, None, test, self.total_test_num)

                self.remain_test = prev_remain_test

        if not is_run_func_spec :
            self.func_spec_inference(synthe)
        
    def patch_only_once(self, synthe, ranking_localize) :
        '''
        Type Difference 정보에서 equal이 생기기 시작했을 때
        한번 시도해보는 패치
        '''
       
        # test file 수정이냐?
        if len(self.neg_infos) == 1 :
            neg_info = self.neg_infos[0]
            neg_filename = neg_info['info']['filename']
            neg_funcname = neg_info['info']['funcname']
        
            if 'test' in neg_filename and 'test' in neg_funcname : # test method면 msg 분석만
                self.msg_patch(synthe)

                return


        # function input type으로 변경
        func_diff = FuncTypeDifference(self.neg_infos, self.neg_func_infos, self.pos_func_infos)

        ranking_func = func_diff.scoring_input_type_comments()

        self.print_loc.func_diff = ranking_func

        done_spec_inference = False

        
        for info in ranking_func :
            if (not done_spec_inference) and (info['equal'] > 0 or info['diff_total'] == 0) :
                self.spec_inference(synthe, ranking_localize)
                done_spec_inference = True

                return

            #continue 

            for neg_info in self.neg_infos :
                if not (neg_info['info']['filename'] == info['filename'] and neg_info['info']['funcname'] == info['funcname']) :
                    continue

                neg_filename = neg_info['info']['filename']
                neg_funcname = neg_info['info']['funcname']
                neg_classname = neg_info['info']['classname']
                neg_lineno = neg_info['info']['line']
                neg_args = neg_info['args']

                test = set(neg_info['idx'])

                if not test.issubset(self.remain_test) :
                    continue 
                prev_remain_test = self.remain_test
                self.remain_test = self.remain_test - test

                neg_file_node = deepcopy(self.files[neg_filename])

                entry = FunctionEntry()
                target_arg, target_node = entry.get_function_entry_info(info, neg_file_node, neg_lineno)


                len_keys = len(info['diff'].keys())
                template = copy(TYPE_CASTING) 
                if len_keys >= 2 :
                    template = [Template.Return]

                info['typ'] = list(dict.fromkeys(info['typ']))
                import itertools
                templates = list()
                for neg_typ in info['typ'] :
                    candidate_template = template

                    if "::" in neg_typ :
                        tmp_typ = neg_typ.split("::")[-1]

                        if 'collections.abc' in tmp_typ : # 상위의 타입
                            # 하위 타입이랑 비슷하게 처리할 거임 그걸 찾아야함
                            find_func = FindTargetFunc(target_node)
                            target_func = find_func.get_func(neg_file_node)

                            target_func.body.insert(0, ast.ImportFrom(
                                module='collections', 
                                names=[ast.alias(name='abc')], 
                                level=0
                            ))

                            type_set = [('Mapping', ['dict']), ('Iterable', ['list', 'tuple']), ('Set', ['set'])]

                            for (upper_typ, lower_typs) in type_set :
                                if upper_typ in tmp_typ :
                                    for lower_typ in lower_typs :
                                        find_isinstance = FindIsInstance(target_arg, lower_typ)
                                        isinstance_list = find_isinstance.get_isinstance(target_func)

                                        for isinstance_stmt in isinstance_list :
                                            test_origin = isinstance_stmt.test
                                            isinstance_stmt.test = ast.BoolOp(
                                                op=ast.Or(),
                                                values=[
                                                    test_origin,
                                                    ast.Call(
                                                        func=ast.Name(id='isinstance', ctx=ast.Load()),
                                                        args=[
                                                            ast.Name(id=target_arg, ctx=ast.Load()),
                                                            ast.Name(id='abc.' + upper_typ, ctx=ast.Load())
                                                        ],
                                                        keywords=[]
                                                    )
                                                ],
                                                mark=True
                                            )

                                            targets = isinstance_stmt.test
                                            self.validate.validate(neg_file_node, neg_filename, targets, test, self.total_test_num)
                                            isinstance_stmt.test = test_origin
                            
                            del target_func.body[0]




                    templates.append([(neg_typ, template) for template in candidate_template])
                    #templates.extend(list(itertools.product([neg_typ], candidate_template)))
        
                find_func = FindTargetFunc(target_node)
                target_func = find_func.get_func(neg_file_node)

                typecheck_candidates = extract_info.extract_isinstance_stmt_info(target_func)
                context_aware = ContextAware(typecheck_candidates, [neg_file_node])

                for template in itertools.product(*templates) :
                    make_template = MakeTemplate(neg_file_node, target_arg, info['typ'], info['diff'], template, neg_args, self.pos_func_infos)
                    ast_list = make_template.get_ast_list(neg_funcname, target_node)

                    for node in ast_list :
                        synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_info['args'], self.pos_func_infos, None, context_aware, None, None, test, self.total_test_num, func_patch=True)

                self.remain_test = prev_remain_test

        if not done_spec_inference :
            self.spec_inference(synthe, ranking_localize)

    def change_localize(self, error_stmt, localize_line, neg_args, neg_file_node, funcname, neg_filename, neg_funcname, neg_classname, test, synthe, var_score=None, pos_samples={}) :
        find_func = FindTargetFunc(error_stmt)
        target_func = find_func.get_func(neg_file_node)

        typecheck_candidates = extract_info.extract_isinstance_stmt_info(target_func)
        context_aware = ContextAware(typecheck_candidates, [neg_file_node])

        if var_score is not None : 
            for target_node, diff in var_score.items() :
                len_keys = len(diff.keys())

                templates = copy(TYPE_CASTING) 
                target_arg = ast.unparse(target_node)

                target_typ = neg_args.get(target_arg, ['None'])
                #print(target_typ, target_arg)
                #input()

                if not target_typ :
                    continue

                if 'None' in target_typ :
                    templates.extend(NONE_PATCH)

                if len_keys >= 2 :
                    templates.append(Template.Return)

                #if "::" in target_typ :
                #    templates.append(Template.SubClass)

                candidate_templates = list()
                import itertools
                candidate_templates.extend(list(itertools.product(target_typ, templates)))

                for template in candidate_templates :
                    make_template = MakeTemplate(neg_file_node, target_arg, target_typ, diff, [template], neg_args, self.pos_func_infos)
                    ast_list = make_template.get_ast_list(neg_funcname, error_stmt)

                    for node in ast_list :
                        synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, context_aware, None, None, test, self.total_test_num)
            return

        '''
        Make Template List
        '''

        error_is_if_stmt = False
        if isinstance(error_stmt, ast.If) :
            error_is_if_stmt = True

        check_loop = IsInLoop()
        is_in_loop = check_loop.isin_loop(int(localize_line), neg_file_node)

        selector = Selector(neg_args, pos_samples, error_is_if_stmt, is_in_loop)
        templates = selector.scoring_template()

        '''
        Template to AST
        '''
        for (arg, arg_typ_info, templates) in templates :
            #print("Arg_Type_Info : ", arg_typ_info)
            #input()
            for template in templates :
                if len(template) >= 3 :
                    continue
                    # only multiple patch

                make_template = MakeTemplate(neg_file_node, arg, neg_args[arg], arg_typ_info, template, neg_args, self.pos_func_infos)
                ast_list = make_template.get_ast_list(funcname, error_stmt)
                if ast_list is None :
                    continue

                for node in ast_list :
                    '''
                    Synthesis
                    '''
                    components = None
                    synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, context_aware, None, self.neg_additional, test, self.total_test_num)


    def work(self) :
        '''
            Error 난 코드 line 먼저 선택
            -> 안되면, sbfl을 통해 수정할 line 선택
            Mutation을 통해 어떤 mutate를 할지 결정
            Synthesize를 통해 어떤 합성을 할지 선택
        '''

        if not self.neg_infos :
            return 
            
        try :
            #print(self.remain_test)
            synthe = synthesize.Synthesize(self.files_src, self.validate, self.files, self.neg_func_infos)
            
            
            # 메세지 패치 먼저
            self.msg_patch(synthe)
            
            # Call Chain
            for neg_info in self.neg_infos :
                #continue
                test = set(neg_info['idx'])

                if not test.issubset(self.remain_test) :
                    continue 
                prev_remain_test = self.remain_test
                self.remain_test = self.remain_test - test

                neg_lineno = neg_info['info']['line']
                neg_filename = neg_info['info']['filename']
                neg_funcname = neg_info['info']['funcname']
                try :
                    neg_file_node = deepcopy(self.files[neg_filename])
                except Exception as e :
                    print(neg_filename, "not exists")
                    break
                error_stmt = extract_info.find_error_stmt(neg_file_node, neg_lineno)


                call_chain = CallChain(self.neg_localize, self.files, self.neg_infos, self.pos_info, self.pos_func_infos, test)
                #pprint(call_chain)
                #input()
                ast_list = call_chain.do_call_chain()

                find_func = FindTargetFunc(error_stmt)
                target_func = find_func.get_func(neg_file_node)

                typecheck_candidates = extract_info.extract_isinstance_stmt_info(target_func)
                context_aware = ContextAware(typecheck_candidates, [neg_file_node])


                for (neg_filename, neg_funcname, neg_classname, neg_args, node) in ast_list :
                    synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, context_aware, None, self.neg_additional, test, self.total_test_num)
                    #find_template = FindTemplate()
                    #targets = find_template.get_target(node)
                    #self.validate.validate(node, filename, targets, test, self.total_test_num)



                self.remain_test = prev_remain_test
                break

            # try-except 안에 있는가?
            for neg_info in self.neg_infos :
                #continue
                neg_lineno = neg_info['info']['line']
                neg_funcname = neg_info['info']['funcname']
                neg_filename = neg_info['info']['filename']

                test = set(neg_info['idx'])

                if not test.issubset(self.remain_test) :
                    continue 
                prev_remain_test = self.remain_test
                self.remain_test = self.remain_test - test

                try :
                    neg_file_node = deepcopy(self.files[neg_filename])
                except Exception as e :
                    print(neg_filename, "not exists")
                    continue
                error_stmt = extract_info.find_error_stmt(neg_file_node, neg_lineno)



                add_exception = AddException(neg_file_node, error_stmt)
                complete_list = add_exception.get_exception_list(neg_file_node)

                for node in complete_list :
                    find_template = FindTemplate()
                    targets = find_template.get_target(node)

                    self.validate.validate(node, neg_filename, targets, test, self.total_test_num)

                self.remain_test = prev_remain_test



            #for key in sorted(self.sbfl.keys(), reverse=True) :
            #    for file, lines in self.sbfl[key].items() :
                # 원본 파일 ast

            '''
            Check Type Assert
            '''

            '''
            if self.neg_infos[0]['info'] == 'AssertionError' :
                self.assertion_patch(synthe)
                return
            '''

            '''
            Localize
            '''

            #print_sbfl(self.neg_localize, self.pos_localize, self.neg_infos)

            type_diff = TypeDifference(self.neg_infos, self.pos_info)
            type_diff_result = type_diff.scoring_by_function_line()


            ranking_localize = get_ranking_localize(self.neg_localize, self.pos_localize, type_diff_result)
            self.print_loc.type_diff = ranking_localize
            #pprint(ranking_localize)
            #input()
            #exit()

            for rank_by_type in ranking_localize : # type difference 가장 큰 순으로
                #break
                #print("[ Different Type Score ]")
                for localize_list in rank_by_type.values() : # sbfl 점수 순서대로 나옴
                    #print("[ Different Sbfl Score ]")

                    for localize in localize_list : # 같은 점수대가 있을 수도 있으니!
                        # equal이 생기거나 diff가 없어졌으면 다른 패치 한번 시도
                        if (not self.done_patch_only_once) and (localize['info']['equal'] > 0 or localize['info']['diff_total'] == 0) :
                            #if (not self.done_patch_only_once) and (localize['info']['diff_total'] == 0) :
                            self.done_patch_only_once = True
                            self.patch_only_once(synthe, ranking_localize)
                        
                        #continue

                        (filename, funcname, localize_line) = localize['localize']


                        if 'test' in filename and 'test' in funcname : # test method 수정 ㄴㄴ 
                            continue

                        arg_name = localize['info']['name']
                        if arg_name == 'self' :
                            continue

                        for neg_info in self.neg_infos :
                            (neg_filename, neg_funcname) = self.get_neg_filename_funcname(neg_info)

                            if neg_filename == filename and neg_funcname == funcname :
                                neg_args = dict()
                                try :
                                    neg_args[arg_name] = neg_info['args'][arg_name]
                                except :
                                    # 같은 line 다른 neg_info
                                    continue

                                neg_lineno = neg_info['info']['line']
                                try:
                                    neg_file_node = deepcopy(self.files[neg_filename])
                                except Exception as e :
                                    print(neg_filename, "not exists")
                                    continue
                                neg_classname = neg_info['info']['classname']
                                test = set(neg_info['idx'])

                                if not test.issubset(self.remain_test) :
                                    continue 

                                prev_remain_test = self.remain_test
                                self.remain_test = self.remain_test - test

                                try :
                                    pos_samples = self.pos_info[neg_filename][str(neg_lineno)]
                                except Exception as e:
                                    pos_samples = []

                                pos_typs = set([])
                                for pos_sample in pos_samples :
                                    typ = pos_sample['info'].get(arg_name, None)
                                    if typ is None :
                                        continue

                                    pos_typs.add(typ)

                                '''
                                처음에 error_stmt가 If문에 걸려있으면
                                Else문이 should_fix인지 보아야함
                                should_fix면 그 밖에다가 패치하기!
                                '''
                                #localize_line = 279
                                error_stmt = extract_info.find_error_stmt(neg_file_node, int(localize_line))

                                # init complicated variable
                                for child_node in ast.walk(error_stmt) :
                                    if isinstance(child_node, ast.Attribute) and isinstance(child_node.value, ast.Subscript) :
                                        neg_info['args'][ast.unparse(child_node)] = ['None']
                                        neg_args[ast.unparse(child_node)] = ['None']

                                suspicious = FindSuspiciousNode(error_stmt)
                                stmt_list_list, if_list, error_if_stmt = suspicious.get_node_list(neg_file_node)

                                is_should_fix = None

                                for stmt_list in stmt_list_list :
                                    usage = UsageAnalysis(arg_name)
                                    #usage = UsageAnalysis(localize['info']['name'], neg_lineno)
                                    for stmt in stmt_list :
                                        should_fix, target_stmt = usage.get_stmt(stmt)
                                        if should_fix is not None :
                                            is_should_fix = should_fix
                                            break

                                    if is_should_fix is not None :
                                        break

                                usage = UsageAnalysis(arg_name)
                                for if_stmt in if_list :
                                    if is_should_fix : 
                                        break

                                    if if_stmt == error_if_stmt :
                                        if error_stmt in if_stmt.body:
                                            if len(if_stmt.orelse) == 1 and isinstance(if_stmt.orelse[0], ast.If) :
                                                continue

                                            new_stmt = ast.If(
                                                test=if_stmt.test,
                                                body=ast.Pass(),
                                                orelse=if_stmt.orelse
                                            )
                                            should_fix, target_stmt = usage.get_stmt(new_stmt)

                                        elif error_stmt in if_stmt.orelse :
                                            new_stmt = ast.If(
                                                test=if_stmt.test,
                                                body=if_stmt.body,
                                                orelse=[]
                                            )
                                            should_fix, target_stmt = usage.get_stmt(new_stmt)
                                    else :
                                        should_fix, target_stmt = usage.get_stmt(if_stmt)

                                    if should_fix is not None :
                                        is_should_fix = should_fix
                                        break

                                if is_should_fix is True :
                                    # 가장 앞에 있는 코드 찾기
                                    fastest_line = error_if_stmt.lineno
                                    target_stmt = error_if_stmt

                                    for if_stmt in if_list :
                                        if fastest_line > if_stmt.lineno :
                                            fastest_line = if_stmt.lineno
                                            target_stmt = error_if_stmt

                                    self.change_localize(target_stmt, fastest_line, neg_args, neg_file_node, neg_funcname, neg_filename, neg_funcname, neg_classname, test, synthe, pos_samples=pos_samples)

                                

                                find_func = FindTargetFunc(error_stmt)
                                target_func = find_func.get_func(neg_file_node)

                                typecheck_candidates = extract_info.extract_isinstance_stmt_info(target_func)
                                context_aware = ContextAware(typecheck_candidates, [neg_file_node])


                                error_is_if_stmt = False
                                if isinstance(error_stmt, ast.If) :
                                    error_is_if_stmt = True

                                def find_node(node) :
                                    for child in ast.walk(node) :
                                        if isinstance(child, ast.Call) :
                                            call_name = ast.unparse(child.func) 
                                            # if call_name in neg_info['args'] and 'function' in neg_info['args'][call_name] :
                                            if call_name in neg_info['args'] :
                                                # function은 여러 함수 타입을 가질 수 있기 때문에
                                                # 함부로 argument를 Type Casting을 하면 안됨
                                                return None

                                        if isinstance(child, (ast.Subscript, ast.Attribute, ast.Name)) and ast.unparse(child) == arg_name :
                                            return child

                                # Neg None Guard
                                #if len(neg_info['args'][arg_name]) == 1 and error_is_if_stmt :
                                def neg_guard() :
                                    if len(neg_info['args'][arg_name]) >= 1 and error_is_if_stmt :
                                        arg_node = None
                                        arg_node = find_node(error_stmt)

                                        if arg_node is not None :
                                            neg_typ = tuple(set(abstract_type_list(neg_info['args'][arg_name])))
                                            #if neg_typ == 'None' :
                                            if len(neg_typ) == 1 :
                                                neg_typ = neg_typ[0]

                                            add_guard = AddGuard(neg_file_node)
                                            complete_list = add_guard.get_guard_list({arg_node : {neg_typ : 1}}, neg_args, error_stmt, True)

                                            for node in complete_list :
                                                #continue
                                                find_template = FindTemplate()
                                                targets = find_template.get_target(node)

                                                self.validate.validate(node, neg_filename, targets, test, self.total_test_num)

                                def pos_guard() :                                         
                                    if len(pos_typs) >= 1 :
                                        var_score = dict()
                                        arg_node = None
                                        arg_node = find_node(error_stmt)
                                        abs_pos_typs = tuple(set(abstract_type_list(pos_typs)))
                                            
                                        if arg_node is not None :
                                            
                                            def pos_typecast() :
                                                if len(abs_pos_typs) == 1 :
                                                    var_score[arg_node] = {abs_pos_typs[0] : 1}

                                                    add_typecasting = AddTypeCasting()
                                                    complete_list = add_typecasting.get_typecasting_list(var_score, neg_args, neg_file_node)
                                                    # 단순 TypeCasting
                                                    for node in complete_list :
                                                        #continue
                                                        find_template = FindTemplate()
                                                        targets = find_template.get_target(node)

                                                        self.validate.validate(node, neg_filename, targets, test, self.total_test_num)

                                            var_score[arg_node] = {abs_pos_typs : 1}

                                            def pos_onlyguard() :
                                                # Add Guard

                                                if error_is_if_stmt :
                                                    # Pos Guard
                                                    add_guard = AddGuard(neg_file_node)
                                                    complete_list = add_guard.get_guard_list(var_score, neg_args, error_stmt)

                                                    for node in complete_list :
                                                        #continue
                                                        find_template = FindTemplate()
                                                        targets = find_template.get_target(node)

                                                        self.validate.validate(node, neg_filename, targets, test, self.total_test_num)

                                            if '[' in arg_name:
                                                var_score[arg_node] = {abs_pos_typs : 1}
                                                pos_onlyguard()
                                                pos_typecast()
                                                var_score[arg_node] = {abs_pos_typs : 1}
                                            else :
                                                pos_typecast()
                                                var_score[arg_node] = {abs_pos_typs : 1}
                                                pos_onlyguard()

                                        for target_node in var_score.keys() :
                                            type_chain = TypeChain(self.neg_localize, neg_filename, target_node, neg_file_node, target_node, self.neg_func_infos, self.pos_func_infos)
                                            chain_result = type_chain.get_type_chain(neg_file_node)

                                            '''
                                            print("[[[ Type Chain ]]]")
                                            pprint(chain_result)
                                            input()
                                            '''

                                            if chain_result :
                                                chain_error_stmt = chain_result[0]
                                                target_arg = chain_result[1][0]
                                                type_info = chain_result[1][1]
                                                templates = copy(TYPE_CASTING)

                                                for neg_type in type_info[0] :
                                                    #if "::" in neg_type :
                                                    #    templates.append(Template.SubClass)

                                                    diff_info = type_info[1]

                                                    candidate_templates = list()
                                                    import itertools
                                                    candidate_templates.extend(list(itertools.product([neg_type], templates)))

                                                    for template in candidate_templates :
                                                        make_template = MakeTemplate(neg_file_node, target_arg, neg_type, diff_info, [template], neg_args, self.pos_func_infos)
                                                        ast_list = make_template.get_ast_list(neg_funcname, chain_error_stmt)

                                                        for node in ast_list :
                                                            #continue
                                                            synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, context_aware, None, None, test, self.total_test_num)

                                if '[' in arg_name: # iterable 타입은 여러 타입을 가질 수 있으므로 pos_guard부터
                                    pos_guard()
                                    neg_guard()
                                else :   
                                    neg_guard()    
                                    pos_guard()
                                               
                                
                                find_func = FindTargetFunc(error_stmt)
                                target_func = find_func.get_func(neg_file_node)

                                typecheck_candidates = extract_info.extract_isinstance_stmt_info(target_func)
                                context_aware = ContextAware(typecheck_candidates, [neg_file_node])

                                '''
                                Make Template List
                                '''      

                                '''
                                미리 if, ifelse 모으기
                                '''

                                for arg, typ in neg_args.items() :
                                    if arg == 'self' :
                                        continue 

                                    candidate_templates = list()
                                    import itertools
                                    candidate_templates.extend(list(itertools.product(typ, copy(BASIC))))

                                    for template in candidate_templates :
                                        make_template = MakeTemplate(neg_file_node, arg, typ, dict(), [template], neg_args, self.pos_func_infos)
                                        ast_list = make_template.get_ast_list(neg_funcname, error_stmt)

                                        if ast_list is None :
                                            continue

                                        self.stmt_hole_list.extend([(node, neg_filename, neg_funcname, neg_classname, neg_args, neg_file_node, error_stmt) for node in ast_list])

                                check_loop = IsInLoop()
                                is_in_loop = check_loop.isin_loop(int(localize_line), neg_file_node)

                                selector = Selector(neg_args, pos_samples, error_is_if_stmt, is_in_loop)
                                templates = selector.scoring_template()

                                '''
                                Template to AST
                                '''

                                for (arg, arg_typ_info, templates) in templates :
                                    for template in templates :
                                        if len(template) >= 3 :
                                            continue
                                            # only multiple patch

                                        make_template = MakeTemplate(neg_file_node, arg, neg_args[arg], arg_typ_info, template, neg_args, self.pos_func_infos)
                                        ast_list = make_template.get_ast_list(funcname, error_stmt)
                                        if ast_list is None :
                                            continue

                                        if len(template) == 2 and template[1] in TemplateMethod.Multiple.value :
                                            self.stmt_hole_list.extend([(node, neg_filename, neg_funcname, neg_classname, neg_args, neg_file_node, error_stmt) for node in ast_list])

                                        for node in ast_list :
                                            #continue
                                            '''
                                            Synthesis
                                            '''
                                            components = None
                                            synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, context_aware, None, self.neg_additional, test, self.total_test_num)

                                self.remain_test = prev_remain_test
  
            if not self.done_patch_only_once :
                self.patch_only_once(synthe, ranking_localize)
                self.done_patch_only_once = True

            #self.print_loc.print_all()
            #return
            '''
            최종 합성 => enumerative
            error 난 위치에서 if, ifelse 만 이용하고
            context-aware로 stmt 스코어링 해서 따옴
            그걸로 대체
            '''
            #print("[[ Final ]]")

            for (node, neg_filename, neg_funcname, neg_classname, neg_args, neg_file_node, error_stmt) in self.stmt_hole_list :
                for neg_info in self.neg_infos :
                    (filename, funcname) = self.get_neg_filename_funcname(neg_info)

                    if not (filename == neg_filename and funcname == neg_funcname) :
                        continue

                    if 'test' in neg_filename and 'test' in neg_funcname :
                        continue 
                        
                    test = set(neg_info['idx'])

                    if not test.issubset(self.remain_test) :
                        continue 

                    prev_remain_test = self.remain_test
                    self.remain_test = self.remain_test - test 


                    find_func = FindTargetFunc(error_stmt)
                    target_func = find_func.get_func(neg_file_node)

                    typecheck_candidates = extract_info.extract_isinstance_stmt_info(target_func)
                    context_aware = ContextAware(typecheck_candidates, [neg_file_node])

                    target_node = FindTemplate().get_target(node)   
                    context_score = context_aware.extract_score(target_node, [node])

                    synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, None, context_score, self.neg_additional, test, self.total_test_num)

                    self.remain_test = prev_remain_test

            for (node, neg_filename, neg_funcname, neg_classname, neg_args, neg_file_node, error_stmt) in self.stmt_hole_list :
                for neg_info in self.neg_infos :
                    (filename, funcname) = self.get_neg_filename_funcname(neg_info)

                    if not (filename == neg_filename and funcname == neg_funcname) :
                        continue

                    if 'test' in neg_filename and 'test' in neg_funcname :
                        continue 
                        
                    test = set(neg_info['idx'])

                    if not test.issubset(self.remain_test) :
                        continue 

                    prev_remain_test = self.remain_test
                    self.remain_test = self.remain_test - test 

                    find_func = FindTargetFunc(error_stmt)
                    target_func = find_func.get_func(neg_file_node)

                    typecheck_candidates = extract_info.extract_isinstance_stmt_info(target_func)
                    context_aware = ContextAware(typecheck_candidates, [neg_file_node])

                    target_node = FindTemplate().get_target(node)   
                    context_score = context_aware.extract_score(target_node, [node])

                    synthe.synthesize(node, neg_filename, neg_funcname, neg_classname, neg_args, self.pos_func_infos, None, None, context_score, self.neg_additional, test, self.total_test_num, final=True)

                    self.remain_test = prev_remain_test

        except synthesize.PassAllTests as e: 
            test = e.test
            prev_patch = self.patch_file_dict.get(e.filename, dict())
            self.patch_file_dict[e.filename] = e.node

            if self.remain_test : # test 남아 있으면
                #print(self.remain_test)
                for pass_target in e.targets :
                    pass_target.mark = False

                prev = self.files[e.filename]
                self.files[e.filename] = e.node

                works = Work(self.files_src, self.validate, self.files, self.neg_localize, self.pos_localize,
                self.pos_info, self.pos_func_infos, self.neg_infos, self.neg_func_infos, self.neg_msg, self.neg_additional, self.remain_test, self.total_test_num + len(test))
                works.work()

                self.files[e.filename] = prev
                self.patch_file_dict[e.filename] = prev_patch
            else : # test 다 통과하면
                patcher = FindUpperStmt(self.patch_file_dict)
                patcher.change_upper_node()
                raise e

        except synthesize.PassAllTestsMultiple as e :
            test = e.test
            prev_patch_dict = dict()
            for patch_node, patch_filename in e.node_list :
                prev_patch_dict[patch_filename] = self.patch_file_dict.get(patch_filename, dict())
                self.patch_file_dict[patch_filename] = patch_node

            #print(e.node_list)
            if self.remain_test : # test 남아 있으면
                for pass_target in e.targets :
                    pass_target.mark = False

                prev_file_dict = dict()

                for patch_node, patch_filename in e.node_list :
                    prev_file_dict[patch_filename] = self.files[patch_filename]
                    self.files[patch_filename] = patch_node

                works = Work(self.files_src, self.validate, self.files, self.neg_localize, self.pos_localize,
                self.pos_info, self.pos_func_infos, self.neg_infos, self.neg_func_infos, self.neg_msg, self.neg_additional, self.remain_test, self.total_test_num + len(test))
                works.work()

                for patch_node, patch_filename in e.node_list :
                    self.files[patch_filename] = prev_file_dict[patch_filename]
                    self.patch_file_dict[patch_filename] = prev_patch_dict[patch_filename]
            else : # test 다 통과하면
                patcher = FindUpperStmt(self.patch_file_dict)
                patcher.change_upper_node()
                raise e