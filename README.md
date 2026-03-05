# GoldenCheetah Proxy

A small tool that lets web apps access your [GoldenCheetah](https://www.goldencheetah.org/) data. It runs on your computer and keeps your data private. Nothing is sent to the cloud.

## Installation

You don't need Python or any other programming tools installed. The commands below handle everything automatically.

**macOS and Linux:** open Terminal (on Mac: press Cmd+Space, type "Terminal", press Enter) and paste:

```
curl -LsSf uvx.sh/goldencheetah-proxy/install.sh | sh
```

**Windows:** open PowerShell (press the Windows key, type "PowerShell", press Enter) and paste:

```
powershell -ExecutionPolicy ByPass -c "irm https://uvx.sh/goldencheetah-proxy/install.ps1 | iex"
```

> **Important:** After installing, close your terminal and open a fresh one. This is needed so your terminal picks up the newly installed command.

## How to use

### 1. Enable the GoldenCheetah API

Open GoldenCheetah, then go to:

**Settings → General → Integration → Enable API Web Services**

### 2. Start the proxy

Open a terminal (or PowerShell on Windows) and run:

```
goldencheetah-proxy
```

You should see:

```
GoldenCheetah Proxy v0.1.0
Proxy running on http://localhost:12022
Forwarding to GoldenCheetah at http://localhost:12021
Waiting for connections...
```

Leave this running while you use the web viewer.

### 3. Open the web viewer

Open `goldencheetah-web-viewer/index.html` in your browser and click **Connect**.

The proxy will ask you to approve the website. Click **Allow** (or type `y` in the terminal on Linux).

## What does the proxy do?

GoldenCheetah has a built-in API that runs on your computer. Browsers can't talk to it directly due to security restrictions (CORS). The proxy sits in between and adds the right headers so your browser can access the data.

```
Browser  →  Proxy (localhost:12022)  →  GoldenCheetah API (localhost:12021)
```

Your data never leaves your computer.

## Options

```
goldencheetah-proxy --port 9999       # Use a different port (default: 12022)
goldencheetah-proxy --gc-port 5555    # GoldenCheetah API port (default: 12021)
```

## Agent skill

Building a web app that uses GoldenCheetah data? This repo includes an [agent skill](https://agentskills.io) that teaches AI coding agents how to build against the proxy. Install it into your project with:

```
npx skills add SweatStack/goldencheetah-proxy
```

## For developers

Source: [github.com/SweatStack/goldencheetah-proxy](https://github.com/SweatStack/goldencheetah-proxy)

This project uses [uv](https://docs.astral.sh/uv/) for development:

```
git clone git@github.com:SweatStack/goldencheetah-proxy.git
cd goldencheetah-proxy
uv sync                        # Set up the project
uv run goldencheetah-proxy     # Run during development
uv run pytest                  # Run tests
```
