import json
import glob
import shutil
import os
import subprocess

def main() :
    for filename in glob.iglob("/pyter/benchmark/core-8065/**/*.py", recursive=True) :
        if filename == "/pyter/benchmark/core-8065/homeassistant/util/async.py" :
            
            with open(filename, 'r') as f :
                lines = f.readlines()

            for i, line in enumerate(lines) :
                if "from asyncio import async" in line :
                    lines[i] = line.replace("from asyncio import async", "")

                if "ensure_future = async" in line :
                    lines[i] = line.replace("ensure_future = async", "pass")

            with open(filename+"_new", 'w') as f :
                for line in lines :
                    f.write(line)

            os.rename(filename, filename+"_old")
            os.rename(filename+"_new", "/pyter/benchmark/core-8065/homeassistant/util/core_async.py")
            continue
        change = False

        with open(filename, 'r') as f :
            lines = f.readlines()

            for i, line in enumerate(lines) :
                if "homeassistant.util.async" in line :
                    lines[i] = line.replace("homeassistant.util.async", "homeassistant.util.core_async")
                    change = True
                    break

                if "..util.async" in line :
                    lines[i] = line.replace(" ..util.async ", " ..util.core_async ")
                    change = True
                    break

                if ".async" in line :
                    lines[i] = line.replace(" .async ", " .core_async ")
                    change = True
                    break
        
        if change :
            with open(filename+"_new", 'w') as f :
                for line in lines :
                    f.write(line)

            os.rename(filename, filename+"_old")
            os.rename(filename+"_new", filename)
        

        
main()