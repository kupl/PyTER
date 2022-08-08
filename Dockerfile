FROM marinelay/pypebugs:base

ARG USERNAME=wonseok
ARG PROJECT
ARG VERSION

# make directory
USER root
RUN mkdir /pyter && chmod 777 /pyter
RUN apt-get install dos2unix
USER ${USERNAME}
WORKDIR /pyter

# copy file
#COPY benchmark/${PROJECT}/${PROJECT}-${VERSION}/dependency_setup.sh /pyfix_bench/dependency_setup.sh
#COPY benchmark/${PROJECT}/${PROJECT}-${VERSION}/requirements.txt /pyfix_bench/requirements.txt
#COPY benchmark/${PROJECT}/${PROJECT}-${VERSION}/bug_info.json /pyfix_bench/bug_info.json
#COPY benchmark/${PROJECT}/${PROJECT}-${VERSION}/test.sh /pyfix_bench/test.sh
COPY change_core_async.py /pyter/change_core_async.py
COPY benchmark_info /pyter/benchmark_info
COPY bugsinpy_info /pyter/bugsinpy_info
COPY bugsinpy_setup /pyter/bugsinpy_setup
COPY setup.sh /pyter/setup.sh
COPY ready.sh /pyter/ready.sh


USER root
RUN chmod +x setup.sh
RUN chmod +x ready.sh
RUN chmod +x /pyter/bugsinpy_setup/bugsinpy_install.sh
RUN chmod +x /pyter/bugsinpy_setup/bugsinpy_ready.sh
RUN chmod +x /pyter/bugsinpy_setup/bugsinpy_setup.sh
RUN chmod +x /pyter/bugsinpy_setup/bugsinpy-compile
#RUN chmod +x dependency_setup.sh
#RUN chmod +x test.sh
USER ${USERNAME}
#RUN ./setup.sh

