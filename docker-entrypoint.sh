#!/bin/bash
set -e

# Check if credentials exist or if an API key is provided
if [ -n "$GEMINI_API_KEY" ]; then
    echo "Using GEMINI_API_KEY for authentication."
elif [ -f "/root/.gemini/credentials.json" ]; then
    echo "Found existing credentials."
else
    echo "No credentials found. Starting interactive browser authentication."
    echo "Please follow the prompts to log in."
    
    # Set the flag to use browser auth and run the command
    export GOOGLE_GENAI_USE_GCA=true
    gemini -p "hello"
fi

# Now that authentication is handled, start the proxy server
echo "Starting Gemini CLI Proxy..."
exec gemini-cli-proxy
