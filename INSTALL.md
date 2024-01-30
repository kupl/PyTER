# Installation

### 1. Build docker image

We have packaged our artifacts in a Docker image to reproduce the main results of our paper.

```
./docker_build.sh
```

You can make and run docker container using this command:

```
./docker_run.sh
```

### 2. Download PyTER and TypeBugs benchmark

You can download our framework PyTER:

```
git clone https://github.com/kupl/pyter_tool.git
```

and also our benchmark TypeBugs by following commands:

```
./setup.sh
```

### 3. Install essential libraries

After downloading our framework and becnhmark, you should install essential libraries for each programs in benchmark.
It will take a long time. Take a break for a while!

```
./ready.sh
```

# Reproducing Our Results in the Paper

### 1. Preprocessing

Because syntax of **core** program is for Python 2.x.x, you should change some syntax in **core** program:

```
python change_core_async.py
```

### 2. Running Dynamic Analysis

You will get result of dynamic analysis by this script:

```
./pyter_tool/dynamic.sh
```

The result of dynamic analysis will be stored in `/<each_program_path>/pyter` folder.
For example, you can find dynamic analysis result of pandas-17609 program in `/pyter/benchmark/pandas-113/pyter`.

### 3. Running PyTER

You can run our repair framework PyTER for all programs in TypeBugs:

```
python -u ./pyter_tool/my_tool/test_main.py -d "/pyter/benchmark" -c "" 
```

It takes quite a long time.
If you want to see only correct result, then change option of `-c` from "" to "p"

The results of PyTER are stored in `./result/total.result` and you can find detailed information about specific program in `./result/<speicif-program>.result`.
This step contains all of PyTER's patch generation except for dynamic analysis: (1) Static Analysis, (2) Fault Localization, (3) Patch Generation.

# Reproducing BugsInPy Results in the Paper

### 1. Preprocessing

First, download BugsInPy framework:

```
git clone https://github.com/soarsmu/BugsInPy
```

You should copy `bugsinpy-compile` file for our framework:

```
\cp /pyter/bugsinpy_setup/bugsinpy-compile /pyter/BugsInPy/framework/bin/bugsinpy-compile
```

You can download BugsInPy benchmark programs and build by the follwing command:

```
./bugsinpy_setup/bugsinpy_install.sh
```

You can change testfiles of BugsInPy benchmark for our framework:

```
./bugsinpy_setup/bugsinpy_setup.sh
```

You can install libraries to run becnhmark properly:

```
./bugsinpy_setup/bugsinpy_ready.sh
```

### 2. Running Dynamic Analysis

You will get result of dynamic analysis by this script:

```
./pyter_tool/dynamic_bugsinpy.sh
```

The result of dynamic analysis will be stored in `/<each_program_path>/pyter` folder.
For example, you can find dynamic analysis result of pandas-17609 program in `/pyter/benchmark/pandas-113/pyter`.

### 3. Running PyTER

You can run our repair framework PyTER for all programs in BugsInPy:

```
python -u ./pyter_tool/my_tool/test_main.py -d "/pyter/BugsInPy/benchmark" -b "bugsinpy" -c "" 
```

It takes quite a long time.
If you want to see only correct result, then change option of `-c` from "" to "p"

The results of PyTER are stored in `./result/bugsinpy_total.result` and you can find detailed information about specific program in `./result/<speicif-program>.result`.
