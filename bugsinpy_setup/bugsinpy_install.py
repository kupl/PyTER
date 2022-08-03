import json
import glob
import shutil
import os
import subprocess

def main() :
    for filename in glob.iglob("/pyter/bugsinpy_info/*", recursive=False) :
        project = filename.split('/')[-1]

        project_name = project.split('-')[0]
        project_number = project.split('-')[1]

        if project_name == 'youtubedl' :
            project_name = 'youtube-dl'

        bugsinpy_directory = "/pyter/BugsInPy/projects/" + project_name + "/bugs/" + project_number + '/bug.info' 
        

        with open(bugsinpy_directory, 'r') as f :
            lines = f.readlines()

            for line in lines :
                if "python_version" in line :
                    version = line[line.find('"')+1:-1]
                    version = version.replace('"', '')
                    version = version.strip()

        os.system('sh /pyter/bugsinpy_install.sh %s %s %s' % (project_name, project_number, version))
        

        
main()