FROM python:3.12-slim
WORKDIR /app

# Install CAIP SDK
COPY sdk/ /sdk/
COPY README.md /README.md
RUN pip install --no-cache-dir /sdk[server]

# Install example dependencies
COPY examples/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy example code
COPY examples/ .
ENV PYTHONPATH=/app
