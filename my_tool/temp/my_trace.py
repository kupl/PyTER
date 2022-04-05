'''
TODO : Fix 대상 프로그램의 실행 Flow를 Trace하는 파일

MyTrace
    __init__(self, trace_folder) : trace_folder에는 추적할 프로그램 폴더를 넣어준다.
    trace_lines(self, frame, event, arg) : 실행 Flow의 line을 추적 해준다.
    trace_calls(self, frame, event, arg) : trace_folder 하위에서 실행되는 python 파일들을 추적해준다.
'''

import os
import trace
import sys
import ast

class MyTrace() :
    def __init__(self, trace_folder) :
        self.TRACE_FOLDER = trace_folder
        self.message = list()

    def trace_lines(self, frame, event, arg):
        if event != 'line':
            return
        co = frame.f_code
        func_name = co.co_name
        line_no = frame.f_lineno
        filename = co.co_filename
        #self.message.append('%s %s %s' % (filename, func_name, line_no))
        print('%s %s %s' % (filename, func_name, line_no))
        #ast.parse(co)

    def trace_calls(self, frame, event, arg):
        if event != 'call':
            return
        co = frame.f_code
        func_name = co.co_name
        if func_name == 'write':
            # Ignore write() calls from print statements
            return
        line_no = frame.f_lineno
        filename = co.co_filename
        #print(filename)
        #print ('Call to %s on line %s of %s' % (func_name, line_no, filename))
        #print(filename, func_name)
        if self.TRACE_FOLDER in filename:
            # Trace into this function
            return self.trace_lines
        return

    def start_trace(self) :
        sys.settrace(self.trace_calls)

'''
TRACE_INTO = ['format_meter']

os.chdir('/mnt/c/Users/user/Desktop/BugsInPy/checkout/tqdm')

print("Wonseok")
sys.settrace(trace_calls)
format_meter = tqdm.format_meter

assert format_meter(0, 1000, 13, ncols=68, prefix='desc: ') == \
        "desc:   0%|                                | 0/1000 [00:13<?, ?it/s]"

assert (format_meter(0, 1000, 13) == \
    "  0%|          | 0/1000 [00:13<?, ?it/s]")
#
#result = os.popen('bugsinpy-test').read()
print("!?")
print(result)
'''