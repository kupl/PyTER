'''
어디 함수를 먼저 패치할지
스코어링 하는 파일입니다

처음으로 (neg, pos가 만나면서 && 타입 다른 변수가 존재)
를 기준으로 스코어링 합니다
'''

class ScoringErrorFunction() :
    def __init__(self, neg_info, pos_info) :
        self.neg_info = neg_info
        self.pos_info = pos_info

    