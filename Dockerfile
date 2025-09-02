# Multi-stage build for optimized Lambda deployment
FROM public.ecr.aws/lambda/python:3.13-arm64 as builder

# Install system dependencies
RUN dnf update -y && \
    dnf install -y gcc g++ && \
    dnf clean all

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt -t .

# Production stage
FROM public.ecr.aws/lambda/python:3.13-arm64 as production

# Copy installed packages from builder
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copy application code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Set the handler
CMD ["src.handlers.message_handler.lambda_handler"]

# Metadata
LABEL maintainer="AI Nutritionist Team"
LABEL version="1.0.0"
LABEL description="AI Nutritionist Assistant Lambda Function"
