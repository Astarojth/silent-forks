FROM forkdpo-base:python_3.10
COPY src /moto
COPY install.sh /install.sh
RUN chmod -R 777 /moto && bash /install.sh 2>&1 | tail -n 400
RUN git -C /moto config core.fileMode false && git -C /moto update-index -q --refresh; git config --global --add safe.directory '*' && git config --global core.fileMode false && git config --global user.email dev@example.com && git config --global user.name dev
WORKDIR /moto
