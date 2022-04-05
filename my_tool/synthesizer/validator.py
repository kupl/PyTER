import ast
import shutil
import os

from synthesizer.synthesize import PassAllTests, PassAllTestsMultiple

class ValidateCorrect(ast.NodeVisitor) :
    def __init__(self, target) :
        self.target = target[0]
        self.valid = True


    def none_check(self, expr, name) :
        if isinstance(expr, ast.Name) :
            if ast.unparse(expr) == ast.unparse(name) :
                return False
        
        if isinstance(expr, ast.Compare) :
            if ast.unparse(expr.left) == ast.unparse(name) :
                if len(expr.ops) == 1 and isinstance(expr.ops[0], ast.Is) :
                    if len(expr.comparators) == 1 and ast.unparse(expr.comparators[0]) == 'None' :
                        return False

        return True

    def if_check(self, node) :
        pass

    def ifs_check(self, stmt_list) :
        flag = False
        name = None
        for statement in stmt_list :
            if isinstance(statement, ast.If) :
                if flag :
                    is_good = self.none_check(statement.test, name)
                    self.valid = self.valid and is_good
                    flag = False
                    name = None
                if statement is self.target:
                    test = statement.test
                    if isinstance(test, ast.Call) :
                        if isinstance(test.func, ast.Name) and test.func.id == 'isinstance' :
                            name = test.args[0]
                            for arg in test.args :
                                for child in ast.walk(arg) :
                                    if isinstance(child, ast.Name) and child.id == 'None' :
                                        flag = True
            else :
                flag = False
                name = None

    def generic_visit(self, node) :
        if isinstance(node, (ast.mod, ast.stmt)) :
            if hasattr(node, 'body') :
                stmt_list = node.body
                self.ifs_check(stmt_list)
            if hasattr(node, 'orelse') :
                stmt_list = node.body
                self.ifs_check(stmt_list)
            if hasattr(node, 'finalbody') :
                stmt_list = node.body
                self.ifs_check(stmt_list)

        super().generic_visit(node)


    def check_valid(self, node) :
        self.visit(node)

        return self.valid

class Validator() :
    
    def __init__(self, exec_prog) :
        self.prev_list = dict()
        self.exec_prog = exec_prog

    def validate_message(self, out, err, test=[], total_test_num=0) :
        fail_messages = ["FAILED", "FAILURES"] # 이거 있으면 안댐
        
        if test :
            ok_messages = [str(total_test_num + len(test)) + " passed"]
            #print(ok_messages)
        else :
            ok_messages = ["OK", "100%"] # 이거 있으면 오키

        '''
        from pprint import pprint

        pprint(out)
        input()
        pprint(err)
        input()
        '''

        if not test :
            for message in fail_messages :
                if message in err :
                    return False

                if message in out :
                    return False

        for message in ok_messages :
            if message in err :
                return True

            if message in out :
                return True

        return False


    def validate_neg(self, test, total_test_num) :
        out, err = self.exec_prog.execute_neg()
        result = self.validate_message(out, err, test, total_test_num)

        return result

    def validate_pos(self) :
        out, err = self.exec_prog.execute_pos()
        result = self.validate_message(out, err)

        return result

    def validate(self, node, filename, target, test, total_test_num) : 
        #print(ast.dump(node, include_attributes=True, indent=4))
        skip = False
        for child in ast.walk(node) :
            if isinstance(child, ast.Constant) and child.value == '<pyfix_template>' :
                skip = True
                break

        if skip :
            return

        
            
        
        if target and isinstance(target, list):
            correct = ValidateCorrect(target)
            is_valid = correct.check_valid(node)

            if not is_valid : 
                return 

        new_node = ast.fix_missing_locations(node)
        new_file = ast.unparse(new_node)
        
        file_prev_list = self.prev_list.get(filename, set([]))
    
        #print(file_prev_list)
        if new_file in file_prev_list : # 이미 시도해본거임
            #print(new_file)
            #input()
            return

        file_prev_list.add(new_file)
        self.prev_list[filename] = file_prev_list

        copy_name = filename + "_origin"
        shutil.move(filename, copy_name)

        try :
            with open(filename, "w+") as f :
                f.write(new_file)

            #print(filename, 'validate')
            #if target :
            #    print(ast.unparse(ast.fix_missing_locations(target[0])))

            #print(new_file)
            #input()
            
            
            

            if self.validate_neg(test, total_test_num) and self.validate_pos() :
                raise PassAllTests(filename, node, test, targets=target)

        except PassAllTests as e :            
            raise e

        finally :
                os.remove(filename)
                shutil.move(filename + "_origin", filename)

    def multiple_file_validate(self, node_list, targets, test, total_test_num) : 
        #print(ast.dump(node, include_attributes=True, indent=4))
        new_file_list = list()
        filename_set = set()

        for node, filename in node_list :
            new_node = ast.fix_missing_locations(node)
            new_file = ast.unparse(new_node)
            new_file_list.append(new_file)

            filename_set.add(filename)

        for filename in filename_set :
            copy_name = filename + "_origin"
            shutil.move(filename, copy_name)

        try :
            for i, new_file in enumerate(new_file_list) :
                with open(node_list[i][1], "w+") as f :
                    f.write(new_file)

            #for _, filename in node_list :
            #    print(filename, 'validate')
            #if targets :
            #    print(ast.unparse(ast.fix_missing_locations(targets[0]))) 
            #input()            

            if self.validate_neg(test, total_test_num) and self.validate_pos() :
                raise PassAllTestsMultiple(node_list, test, targets=targets)

        except PassAllTestsMultiple as e :            
            raise e

        finally :
            for filename in filename_set :
                os.remove(filename)
                shutil.move(filename + "_origin", filename)