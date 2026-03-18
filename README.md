# d4c - OpenCode Discord Bot

**d4c** is a powerful, asynchronous Discord bot built with Python that serves as a seamless bridge to the OpenCode engineering agent. It allows users to interact with an advanced AI coding assistant directly from Discord, featuring rich interactive UIs, real-time progress tracking, and intelligent channel session management.

## 🌟 Key Features

- **OpenCode Backend Integration**: Communicates with the OpenCode agent backend via Server-Sent Events (SSE) and WebSockets to stream raw execution events in real-time.
- **Smart Session Management**:
  - **Full Control Mode (Auto-Channel Management)**: Users drop a request in a `#welcome` channel, and the bot automatically locks it, renames it to an isolated task channel (e.g., `#task-build-api`), and provisions a new `#welcome` channel for the next user.
  - **Normal Listening Mode**: Opt-in session binding using slash commands (`/new` and `/exit`) for passive channel listening.
- **Rich Interactive UI**:
  - **Real-Time Progress Embeds**: Dynamically updating Discord Embeds that track the AI's execution state (e.g., running `bash`, `read`, `write`), complete with color-coded statuses (Yellow: In-progress, Green: Success, Red: Error) and tool history.
  - **Interactive Question Forms**: Dynamically generated dropdowns (`discord.ui.Select`) and modals (`discord.ui.Modal`) that allow the agent to ask users questions and receive custom text input seamlessly.
- **Robust & Performant**:
  - Built on `discord.py` and `aiohttp` for high-performance asynchronous operations.
  - Built-in rate limit mitigation, debouncing, and exponential backoff to handle Discord's API limits gracefully.
- **Modern Python Tooling**: Uses Python 3.12+ and [uv](https://github.com/astral-sh/uv) for lightning-fast dependency and virtual environment management.

## 📂 Project Structure

```text
d4c/
├── src/                  # Main bot source code (Bot core, Cogs, UI, Utils)
├── tests/                # Unit and integration tests
├── parse_*.py            # Utility scripts for parsing various response formats and SSE logic
├── test_ws.py            # WebSocket streaming test scripts
├── test_sse_*.py         # SSE streaming test scripts
├── architecture.md       # Detailed system architecture documentation
├── pyproject.toml        # Project metadata and dependencies
└── uv.lock               # Dependency lockfile
```

## 🚀 Getting Started

### Prerequisites

- **Python**: Version 3.12 or higher.
- **Package Manager**: [uv](https://github.com/astral-sh/uv) is highly recommended for dependency management.
- **Discord Bot Token**: A registered bot application on the Discord Developer Portal.

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repository-url>
   cd d4c
   ```

2. **Install dependencies using `uv`:**
   ```bash
   uv sync
   ```
   *This command automatically creates a `.venv` virtual environment and installs all required packages (including `dev` tools like Ruff) based on `pyproject.toml`.*

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your necessary credentials:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   # Add other required API keys or OpenCode backend URLs here
   ```

## 💻 Usage

### Bot Commands

The bot utilizes Discord Slash Commands for environment and agent state management:

- `/mode`: Toggles the bot between **Full Control Mode** (auto-channel creation) and **Normal Listening Mode**.
- `/new`: Starts a new OpenCode session in the current channel (Only available in Normal Listening Mode).
- `/exit`: Terminates and unbinds the active session in the current channel.
- `/agent [name]`: Switches the active OpenCode agent type (e.g., `build`, `plan`, `explore`).

## 🛠️ Development & Testing

**Linting and Formatting**
We use `ruff` for fast code linting and formatting. Run the following command to check your code:
```bash
uv run ruff check .
```

**Testing**
The project includes several test scripts for SSE and WebSocket connections. You can run them directly, for example:
```bash
uv run python test_ws.py
```

## 🏗️ Architecture

For a deep dive into the bot's internal architecture, UI rate-limit debouncing, and event dispatching logic, please refer to the [architecture.md](./architecture.md) file.