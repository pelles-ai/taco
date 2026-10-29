# Build context is the repository root (see docker-compose.yml); the
# .dockerignore there keeps .git, secrets (examples/.env) and local junk out.
FROM python:3.12-slim
WORKDIR /app

# Install TACO SDK. The SDK takes its version from git tags (hatch-vcs), and
# there is no .git in the image, so pin a placeholder version for this one
# install. hatch-vcs does not pass the distribution name to setuptools-scm,
# so the per-package SETUPTOOLS_SCM_PRETEND_VERSION_FOR_TACO_AGENT form is
# ignored; the generic variable is scoped to this RUN instead.
COPY sdk/ /sdk/
COPY README.md /README.md
RUN SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0+docker \
    pip install --no-cache-dir "/sdk[server]"

# Install example dependencies
COPY examples/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy example code
COPY examples/ .
ENV PYTHONPATH=/app
