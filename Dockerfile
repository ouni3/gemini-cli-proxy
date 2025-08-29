# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies, including Node.js and npm
RUN apt-get update && apt-get install -y curl && \
    curl -sL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Install uv, the Python package manager used by this project
RUN pip install uv

# Install the Gemini CLI globally using npm
RUN npm install -g @google/gemini-cli

# Copy the project's dependency files
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Copy the rest of the application's source code
COPY src/ ./src/
COPY LICENSE ./

# Install the project and its dependencies
RUN uv pip install . --system

# Expose the port the app runs on
EXPOSE 8765

# Copy and set up the entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
# Ensure the script has Unix-style line endings and is executable
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh && \
    chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
