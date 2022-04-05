import ast

class FindUpperStmt(ast.NodeVisitor) :
    find_upper = False
    upper_node = None

    def __init__(self, file_dict) :
        self.file_dict = file_dict

    def generic_visit(self, node) :
        if self.upper_node :
            return

        super().generic_visit(node)

        if self.upper_node :
            return

        if isinstance(node, (ast.stmt, ast.expr)) and self.find_upper is True :
            self.upper_node = node

        if node is self.target :
            self.find_upper = True

    
    def change_upper_node(self) :
        # 이거 고쳐야됨
        def find_upper_node(node, upper_node_list) :
            for child in ast.iter_child_nodes(node) :
                if hasattr(child, 'mark') :
                    if isinstance(node, (ast.stmt)) :
                        return [node]
                    else :
                        return True
                
                result = find_upper_node(child, [])

                if result :
                    if isinstance(result, list) :
                        upper_node_list.extend(result)
                    else :
                        if isinstance(node, (ast.stmt)) :
                            upper_node_list.append(node)
                            return upper_node_list
                        else :
                            return True

            return upper_node_list

        for e_file, e_node in self.file_dict.items() :
            self.upper_node_list = find_upper_node(e_node, [])

            for upper_node in self.upper_node_list :
                print("[[[ Node ]]]")
                print(ast.unparse(ast.fix_missing_locations(upper_node)))

            with open(e_file) as f :
                text = f.read()
                lines = text.splitlines()

                modify_lineno = 0

                for self.upper_node in self.upper_node_list :
                    start_line = self.upper_node.lineno - modify_lineno
                    end_line = self.upper_node.end_lineno - modify_lineno
                    offset = self.upper_node.col_offset

                    fix_upper_node = ast.fix_missing_locations(self.upper_node)
                    upper_code = ast.unparse(fix_upper_node)
                    
                    upper_lines = upper_code.splitlines()
                    for i, upper_line in enumerate(upper_lines) :
                        upper_lines[i] = (' ' * offset) + upper_line
                    
                    upper_code = '\n'.join(upper_lines)

                    del lines[start_line-1:end_line]

                    lines.insert(start_line-1, upper_code)
                    text = '\n'.join(lines)

                    modify_lineno += end_line - start_line
                
                with open(e_file+'_solution', 'w') as solution :
                    solution.write(text)

                #return text
