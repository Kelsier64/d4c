# d4c - Discord for Coding-Agent
(only support opencode now) 

d4c is a powerful asynchronous Discord bot built with Python that serves as a seamless bridge to the OpenCode engineering agent. It allows users to interact with an advanced AI coding assistant directly from Discord, featuring rich interactive UIs, real-time progress tracking, and intelligent channel session management.

## Key Features

- **OpenCode Backend Integration**: Communicates with the OpenCode agent backend via Server-Sent Events (SSE) and WebSockets to stream raw execution events in real-time.
- **Smart Session Management**:
  - **Full Control Mode (Auto-Channel Management)**: Users drop a request in a `#welcome` channel, and the bot automatically renames it to an isolated task channel (e.g., `#task-1234abcd`), registers the OpenCode session, and provisions a new `#welcome` channel for the next user.
  - **Normal Listening Mode**: Opt-in session binding using slash commands (`/new` and `/exit`) for passive channel listening.
- **Rich Interactive UI**:
  - **Real-Time Progress Embeds**: Dynamically updating Discord Embeds that track the AI's execution state, complete with color-coded statuses (Yellow: In-progress, Green: Success, Red: Error) and tool history. The embeds automatically stay pinned to the bottom of the chat.
  - **Interactive Question Forms**: Dynamically generated dropdowns (`discord.ui.Select`) and modals (`discord.ui.Modal`) that allow the agent to ask users questions and receive custom text input seamlessly.
- **Robust & Performant**: Built on `discord.py` and `aiohttp` for high-performance asynchronous operations. Includes built-in rate limit mitigation, debouncing, and exponential backoff to handle Discord's API limits gracefully.

## Prerequisites

- **Python**: Version 3.12 or higher.
- **Package Manager**: [uv](https://github.com/astral-sh/uv) is highly recommended for dependency management.
- **Discord Bot Token**: A registered bot application on the Discord Developer Portal with appropriate intents (Message Content, Server Members, etc.).
- **OpenCode CLI**: The OpenCode CLI must be installed and accessible.

## Setting up the OpenCode Server

The bot requires an active, headless OpenCode server to function. You must start the OpenCode server in your target project directory and secure it with a password.

1. Navigate to your target project directory in your terminal.
2. Start the OpenCode server. By default, the bot expects the server to run on port `4096`. You must set a password using the `OPENCODE_SERVER_PASSWORD` environment variable to secure the connection.

```bash
OPENCODE_SERVER_PASSWORD=your_secure_password opencode serve --port 4096
```

This will spin up the backend agent listener. The Discord bot will use this exact password to authenticate requests to the agent backend using Basic HTTP Authentication (with the username implicitly set to `opencode`).

## Bot Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Kelsier64/d4c.git
   cd d4c
   ```

2. **Install dependencies using `uv`:**
   ```bash
   uv sync
   uv pip install -e .
   ```
   *This command automatically creates a `.venv` virtual environment and installs all required packages based on `pyproject.toml`.*

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your credentials. Make sure the password matches the one you used to start the OpenCode server.

   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   OPENCODE_SERVER_PASSWORD=your_secure_password
   ```

4. **Start the bot:**
   Run the bot as a Python module to ensure internal imports resolve correctly:
   ```bash
   uv run python -m src.bot
   ```

## Usage

### Bot Commands

The bot utilizes Discord Slash Commands for environment and agent state management:

- `/mode`: Toggles the bot between **Full Control Mode** (auto-channel creation) and **Normal Listening Mode**. Requires administrator permissions.
- `/new`: Starts a new OpenCode session in the current channel (only available in Normal Listening Mode).
- `/exit`: Terminates and unbinds the active session in the current channel.
- `/agent [name]`: Switches the active OpenCode agent type for the upcoming or active session. Available options are `Build Agent` (`build`) and `Plan Agent` (`plan`). Can be used in the `#welcome` channel to prepare the agent before dropping your first prompt.

## Architecture

For a deep dive into the bot's internal architecture, UI rate-limit debouncing, and event dispatching logic, please refer to the [architecture.md](./architecture.md) file.
