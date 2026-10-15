# Environments

Each `data/environments/<owner__repo>/` directory builds the run image `forkdpo-run:<owner__repo>`.

- `Dockerfile` starts from `forkdpo-base:<tag>`, copies the repository at the task's `base_commit`, runs `install.sh`, and turns off git `fileMode`.
- `install.sh` installs the repository's dependencies.
- `extra_install.sh`, when present, adds dependencies the task needs beyond that install.

`bases/` holds the Dockerfiles for the base images.

```bash
bash scripts/build_image.sh jaegertracing__jaeger
```

This builds the base image if it is missing, checks out the repository at the task commit under `env/<owner__repo>/src`, and builds the run image.
