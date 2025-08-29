# Gemini CLI Proxy

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Mentioned in Awesome Gemini CLI](https://awesome.re/mentioned-badge.svg)](https://github.com/Piebald-AI/awesome-gemini-cli)

Wrap Gemini CLI as an OpenAI-compatible API service, allowing you to enjoy the free Gemini 2.5 Pro model through API!

[English](./README.md) | [简体中文](./README_zh.md)

## ✨ Features

- 🔌 **OpenAI API Compatible**: Implements `/v1/chat/completions` endpoint
- 🚀 **Quick Setup**: Zero-config run with `uvx`
- ⚡ **High Performance**: Built on FastAPI + asyncio with concurrent request support

If you want to know the principle of this tool, you can read [my blog post](https://www.nettee.io/blog/gemini-cli-proxy) (in Chinese).

## 🚀 Quick Start

### Network Configuration

Since Gemini needs to access Google services, you may need to configure terminal proxy in certain network environments:

```bash
# Configure proxy (adjust according to your proxy server)
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890  
export all_proxy=socks5://127.0.0.1:7890
```

### Install Gemini CLI

Install Gemini CLI:
```bash
npm install -g @google/gemini-cli
```

After installation, use the `gemini` command to run Gemini CLI. You need to start it once first for login and initial configuration.

After configuration is complete, please confirm you can successfully run the following command:

```bash
gemini -p "Hello, Gemini"
```

### Start Gemini CLI Proxy

Method 1: Direct startup
```bash
uvx gemini-cli-proxy
```

Method 2: Clone this repository and run:
```bash
uv run gemini-cli-proxy
```

Gemini CLI Proxy listens on port `8765` by default. You can customize the startup port with the `--port` parameter.

### 🐳 Deployment with Docker

This project includes a `Dockerfile` and an entrypoint script to provide a seamless and automated deployment experience.

**1. Build the Docker Image**

First, build the Docker image from the project root:
```bash
docker build -t gemini-cli-proxy .
```

**2. Run the Container**

There are two recommended methods for running the container, depending on your authentication preference.

#### Method 1: API Key (Recommended for Automation)

You can provide your Gemini API key as an environment variable. This is the most reliable method for automated deployments.

```bash
docker run -d -p 8765:8765 \
  --restart always \
  -e GEMINI_API_KEY="YOUR_API_KEY" \
  --name gemini-proxy \
  gemini-cli-proxy
```
Replace `"YOUR_API_KEY"` with your actual Gemini API key.

#### Method 2: Interactive Browser Login (One-Time Setup)

If you prefer to use browser-based authentication, you can perform a one-time interactive login. The credentials will be stored in a persistent Docker volume.

**Step 1: Start the container in interactive mode.**
This command creates a named volume `gemini-config` to store your credentials.
```bash
docker run -it -p 8765:8765 \
  --restart always \
  -v gemini-config:/root/.gemini \
  --name gemini-proxy \
  gemini-cli-proxy
```

**Step 2: Follow the on-screen instructions for one-time setup.**
The first time you run this command, the container needs your permission to access Google. This requires a one-time interactive setup:
- The container will print a long URL to your console.
- **On your main computer**, copy this URL and paste it into your browser.
- Complete the Google login process.
- Google will give you an authorization code. Copy this code.
- Paste the code back into the container's terminal and press Enter.

Once you provide the code, the proxy service will start automatically in the same terminal. Your credentials are now saved permanently in the `gemini-config` volume.

**Step 3: Run the container in the background (Optional).**
After the one-time setup is complete, you can stop the container (with `Ctrl+C`) and run it in detached (`-d`) mode for regular use. It will now start automatically every time.

```bash
docker run -d -p 8765:8765 \
  --restart always \
  -v gemini-config:/root/.gemini \
  --name gemini-proxy \
  gemini-cli-proxy
```
On subsequent runs, the container will automatically find the credentials in the volume and start the proxy server directly.

After startup, test the service with curl:

```bash
curl http://localhost:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dummy-key" \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Usage Examples

#### OpenAI Client

```python
from openai import OpenAI

client = OpenAI(
    base_url='http://localhost:8765/v1',
    api_key='dummy-key'  # Any string works
)

response = client.chat.completions.create(
    model='gemini-2.5-pro',
    messages=[
        {'role': 'user', 'content': 'Hello!'}
    ],
)

print(response.choices[0].message.content)
```

#### Cherry Studio

Add Model Provider in Cherry Studio settings:
- Provider Type: OpenAI
- API Host: `http://localhost:8765`
- API Key: Any string works
- Model Name: `gemini-2.5-pro` or `gemini-2.5-flash`

![Cherry Studio Config 1](./img/cherry-studio-1.jpg)

![Cherry Studio Config 2](./img/cherry-studio-2.jpg)

## ⚙️ Configuration Options

View command line parameters:

```bash
gemini-cli-proxy --help
```

Available options:
- `--host`: Server host address (default: 127.0.0.1)
- `--port`: Server port (default: 8765)
- `--gemini-path`: Path to the Gemini CLI executable (default: gemini)
- `--rate-limit`: Max requests per minute (default: 60)
- `--max-concurrency`: Max concurrent subprocesses (default: 4)
- `--timeout`: Gemini CLI command timeout in seconds (default: 30.0)
- `--debug`: Enable debug mode (enables debug logging and file watching)

## ❓ FAQ

### Q: Why do requests keep timing out?

A: This is usually a network connectivity issue. Gemini needs to access Google services, which may require proxy configuration in certain regions:

```bash
# Configure proxy (adjust according to your proxy server)
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7890

# Then start the service
uvx gemini-cli-proxy
```

## 📄 License

MIT License

## 🤝 Contributing

Issues and Pull Requests are welcome!
