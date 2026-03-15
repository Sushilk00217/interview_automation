FROM gcc:latest

# Create a non-privileged user to run the code
RUN useradd -m sandbox

# Set working directory
WORKDIR /code

# Switch to the non-privileged user
USER sandbox

# Default command
CMD ["/bin/bash"]
