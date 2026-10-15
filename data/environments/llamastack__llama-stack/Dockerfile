FROM forkdpo-base:python_3.12
COPY src /llama-stack
COPY install.sh /install.sh
RUN chmod -R 777 /llama-stack && bash /install.sh 2>&1 | tail -n 400
RUN git -C /llama-stack config core.fileMode false && git -C /llama-stack update-index -q --refresh; git config --global --add safe.directory '*' && git config --global core.fileMode false && git config --global user.email dev@example.com && git config --global user.name dev
RUN cd /llama-stack && R=""; for f in AGENTS.md CLAUDE.md GEMINI.md .cursorrules .windsurfrules .claude .codex .cursor .agents .github/copilot-instructions.md; do [ -e "$f" ] && R="$R $f"; done; \
    if [ -n "$R" ]; then git rm -rq $R && GIT_AUTHOR_DATE="$(git log -1 --format=%cI)" GIT_COMMITTER_DATE="$(git log -1 --format=%cI)" git commit -q -m "chore: remove contributor guidance files" --author="$(git log -1 --format='%an <%ae>')"; echo "removed_rules:$R" > /removed_rules.txt; else echo "removed_rules:" > /removed_rules.txt; fi
WORKDIR /llama-stack
