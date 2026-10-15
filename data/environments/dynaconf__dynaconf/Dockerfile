FROM forkdpo-base:python_3.10
COPY src /dynaconf
COPY install.sh /install.sh
RUN chmod -R 777 /dynaconf && bash /install.sh 2>&1 | tail -n 400
RUN git -C /dynaconf config core.fileMode false && git -C /dynaconf update-index -q --refresh; git config --global --add safe.directory '*' && git config --global core.fileMode false && git config --global user.email dev@example.com && git config --global user.name dev
COPY extra_install.sh /extra_install.sh
RUN bash /extra_install.sh 2>&1 | tail -n 400
WORKDIR /dynaconf
