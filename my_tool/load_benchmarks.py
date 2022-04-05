import json
import glob

class LoadBenchmarks() :
    def __init__(self) :
        self.benchmarks = ['luigi']

    def load_pytest_info(self, pyfix_dir, benchmark_dir, project, idx, assertion="") :
        with open(pyfix_dir + "/pytest-" + project + ".json") as pytest_json :
            pytest_json = json.load(pytest_json)

        if idx != "" :
            pytest_json_single = dict()
            name = project + "-" + idx + ("-noassert" if assertion != "" else "")
            pytest_json_single[name] = pytest_json[name]

            return pytest_json_single
            
        return pytest_json

            


    def load_benchmarks(self, dir) :
        with open(dir + "/bug_infos.json", "r") as bug_infos :
            bug_infos_py = json.load(bug_infos)
            #bug_infos_py = json.loads(bug_infos_json)

        src_paths = {}
        exec_paths = {}
        test_paths = {}

        #print(json.dumps(bug_infos_py, indent=4))

        for project in bug_infos_py :
            exec_path = {}
            src_path = {}
            test_path = {}
            for test_number in bug_infos_py[project] :
                exec_path[test_number] = bug_infos_py[project][test_number]["exec_path"]
                src_path[test_number] = bug_infos_py[project][test_number]["src_path"]
                test_path[test_number] = bug_infos_py[project][test_number]["test_path"]

            exec_paths[project] = exec_path
            src_paths[project] = src_path
            test_paths[project] = test_path

        return exec_paths, src_paths, test_paths