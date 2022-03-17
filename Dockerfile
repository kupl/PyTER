FROM marinelay/pypebugs:base

ARG USERNAME=wonseok
ARG PROJECT
ARG VERSION

# make directory
USER root
RUN mkdir /pyfix_bench && chmod 777 /pyfix_bench
USER ${USERNAME}
WORKDIR /pyfix_bench

# copy file
COPY benchmark/${PROJECT}/${PROJECT}-${VERSION}/dependency_setup.sh /pyfix_bench/dependency_setup.sh
COPY benchmark/${PROJECT}/${PROJECT}-${VERSION}/requirements.txt /pyfix_bench/requirements.txt
COPY benchmark/${PROJECT}/${PROJECT}-${VERSION}/bug_info.json /pyfix_bench/bug_info.json
COPY benchmark/${PROJECT}/${PROJECT}-${VERSION}/test.sh /pyfix_bench/test.sh
COPY setup.sh /pyfix_bench/setup.sh


USER root
RUN chmod +x setup.sh
RUN chmod +x dependency_setup.sh
RUN chmod +x test.sh
USER ${USERNAME}
RUN ./setup.sh

