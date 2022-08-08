# PyTER

PyTER is the first technique that can automatically fix type errors in Python.
The key novelty of PyTER is its type-aware technique that uses type information to increase performance of fault localization and patch geneartion.
To do so, PyTER inferences the incorrect and correct types of candidate variables using dynamic and static analyses.
We utilize the difference of those types to localize buggy locations accurately and prioritize candidate patches that are likely to repair the given error properly.
We implemented the dynamic analysis on top of PyAnnotate, a framework to instrument Python source code.
Other techniques were developed by authors in about 8,000 lines of Python code (v.3.9.1).
For more technical details, please consult our paper or contact us.

# Contents of PyTER

* `all_result` : All result of PyTER on benchmarks. It consists of original file (*.py) and patched file (*.py_solutoin)
* `benchmark_info` : Information and configuration for building TypeBugs benchmark.
* `bugsinpy_info` : Information and configuration for building BugsInPy benchmark.
* `bugsinpy_setup` : Sciprts for installing BugsInPy benchmark.

# Installation

We provide docker container for convinience.
This container consists of only example cases: requests projects in TypeBugs (4 cases) and luigi projects in BugsInPy (7 cases) because providing all benchmarks is time-consuming and large in capacity too much.

You can download our docker conatiner: [here](https://doi.org/10.6084/m9.figshare.20448573.v1)

If you hope to run all benchmarks, then please follow scripts in [INSTALL.md](/INSTALL.md)

### 1. Import docker container

You can import our container as following script:

```
docker import exmaple.tar pyter
```

After then, you can run docker through this script:

```
docker run -it pyter /bin/bash
```

### 2. Setup

You should setup serveral paths to run properly our framework:

```
export PATH=$PATH:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/wonseok/.pyenv/plugins/pyenv-virtualenv/shims:/home/wonseok/.pyenv/shims:/home/wonseok/.pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/pyter/BugsInPy/framework/bin
```

```
source ~/.bashrc
```

When you move to `pyter` folder, then you can reproduce our results:

```
cd pyter
```

# Reproducing Our Results in the Paper

### 1. Running Dynamic Analysis

You will get result of dynamic analysis by this script:

```
./pyter_tool/dynamic.sh
```

The result of dynamic analysis will be stored in `/<each_program_path>/pyter` folder.
For example, you can find dynamic analysis result of requests-3179 program in `/pyter/benchmark/requests-3179/pyter`.

### 2. Running PyTER

You can run our reapir framework PyTER for all programs in TypeBugs:

```
python -u ./pyter_tool/my_tool/test_main.py -d "/pyter/benchmark" -p "requests" -c "" 
```

It takes quite a long time.

The results of PyTER are stored in `./result/total.result` and you can find detailed information about specific program in `./result/<program-number>.result`.
This step contains all of PyTER's patch generation except for dynamic analysis: (1) Static Analysis, (2) Fault Localization, (3) Patch Generation.

# Reproducing BugsInPy Results in the Paper

### 1. Running Dynamic Analysis

You will get result of dynamic analysis by this script:

```
./pyter_tool/dynamic_bugsinpy.sh
```

The result of dynamic analysis will be stored in `/<each_program_path>/pyter` folder.
For example, you can find dynamic analysis result of luigi-4 program in `/pyter/benchmark/luigi-4/pyter`.

### 2. Running PyTER

You can run our reapir framework PyTER for all programs in BugsInPy:

```
python -u ./pyter_tool/my_tool/test_main.py -d "/pyter/BugsInPy/benchmark" -b "bugsinpy" -p "luigi" -c "" 
```

It takes quite a long time.
If you want to see only correct result, then change option of `-c` from "" to "p"

The results of PyTER are stored in `./result/bugsinpy_total.result` and you can find detailed information about specific program in `./result/<program-number>.result`.
