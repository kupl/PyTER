# -*- coding: utf-8 -*-
import execute
import os

class Sbfl():
    def score_formular(self, neg, pos) :
        return neg / (neg + pos)

    def calculate_score(self, neg_localize, pos_localize, neg_infos=None) :
        sbfl = dict()

        neg_localize = dict(sorted(neg_localize.items(), key=lambda x:int(x[0].split()[2])))

        for i, (key, neg_samples) in enumerate(neg_localize.items()) :
            pos_samples = pos_localize.get(key, 0)
            score = self.score_formular(neg_samples, pos_samples)
            split_key = key.split()

            if neg_infos :
                for neg_info in neg_infos :
                    line = str(neg_info['info']['line'])
                    funcname = neg_info['info']['funcname']
                    if split_key[2] == line and split_key[1] == funcname:
                        score = 1
            elif i == len(neg_localize)-1 : # traceback이랑 관련된 line을 최우선으로
                score = 1

            sbfl_score = sbfl.get(score, [])

            
            sbfl_score = [tuple(split_key)] + sbfl_score
            sbfl[score] = sbfl_score

        sbfl = dict(sorted(sbfl.items(), key=lambda item : item[0], reverse=True))

        return sbfl

    def filter_pos_localize(self, neg_localize, pos_localize) :
        # neg에 있는 pos 정보만 남기기
        def filter_pos_info(item) :
            return item[0] in neg_localize
        
        filter_pos = dict(filter(filter_pos_info, pos_localize.items()))

        return filter_pos

    

    def filter_candidate_function(self, neg_localize, candidate_line):
        def filter_neg_info(item) :
            key, value = item
            split_key = key.split()

            return (split_key[0], split_key[1], split_key[2]) in candidate_line

        filter_neg = dict(filter(filter_neg_info, neg_localize.items()))

        return filter_neg


    def fault_localization(self, neg_localize, pos_localize, candidate_line) :
        neg_localize = self.filter_candidate_function(neg_localize, candidate_line) # neg_func에 있는거만 고르기
        pos_localize = self.filter_pos_localize(neg_localize, pos_localize) # neg_info에 있는 pos_info만 고르기

        sbfl = self.calculate_score(neg_localize, pos_localize)
        return sbfl

        

        
         
