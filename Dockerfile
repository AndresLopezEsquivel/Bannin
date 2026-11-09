# Images are pinned to a digest.
# Guide: https://docs.astral.sh/uv/guides/integration/docker/

# Stage 1: install the app and its dependencies into /app/.venv.
FROM python:3.14-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS builder
# The base image has no uv. Later instructions need it.
# We copy it from Astral's official uv image on GitHub's registry.
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /bin/uv

# Settings that uv reads when it runs. For example, they apply to the uv sync lines below.
#
# UV_COMPILE_BYTECODE=1:
# https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
#
# UV_LINK_MODE=copy:
# https://docs.astral.sh/uv/guides/integration/docker/#caching
#
# UV_PYTHON_DOWNLOADS=0: uv uses the Python already in this image and never downloads another one.
# https://docs.astral.sh/uv/reference/environment/#uv_python_downloads
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Docker saves the result of each instruction as a layer. It reuses a saved
# layer when the instruction and the files it copies haven't changed.
# We install the dependencies first, then our project. If only src/ changes,
# Docker reuses the installed dependencies. Without this split, every code
# change would reinstall all the dependencies.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
# Copies our package into .venv. Stage 2 doesn't copy src/, so a link to it would break.
RUN uv sync --locked --no-dev --no-editable

# Stage 2: the final image. Keeps only .venv; leaves out uv, the source code and dev tools.
FROM python:3.14-slim-trixie@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f
# Creates the system user bannin, with UID 10001 and no home directory.
# We use this account so the app doesn't run as root.
RUN useradd --system --uid 10001 --no-create-home bannin
# The copied files belong to root: the bannin user can read them but not change them.
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
USER bannin
EXPOSE 8000
CMD ["uvicorn", "bannin.main:app", "--host", "0.0.0.0", "--port", "8000"]
