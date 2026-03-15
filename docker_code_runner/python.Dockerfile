FROM python:3.10-slim

# Create a non-privileged user to run the code
RUN useradd -m sandbox

# Set working directory
WORKDIR /code

# Switch to the non-privileged user
USER sandbox

# Default command (overridden by code execution service)
CMD ["python3"]
