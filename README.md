# Installation

We provide docker container for convinience.
This container consists of only example cases: requests projects in TypeBugs (4 cases) and luigi projects in BugsInPy (7 cases) because providing all benchmarks is too much time-consumed and large capacity.
You can download our docker conatiner: [here]
If you hope to run all benchmarks, then please follow scripts in INSTALL.md

### 1. Import docker container


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