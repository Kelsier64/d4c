# OpenCode Discord Bot (d4c) Architecture

This document outlines the detailed system architecture and design of `d4c`, the Discord Bot that serves as a bridge to the OpenCode engineering agent. 

## 1. System Overview

The primary goal of `d4c` is to enable Discord users to interact directly with OpenCode through a seamless, native Discord experience. The architecture follows a client-server model where the Discord bot acts as the intelligent frontend client ("Smart Bot"), and OpenCode runs as the backend service.

### High-Level Components

*   **Discord Frontend Client (`d4c` Bot)**: Built with `discord.py`. It manages Discord API rate limits, renders interactive UIs (Embeds, Select Menus, Modals), and orchestrates channel lifecycles and user sessions.
*   **OpenCode Backend Service**: The core agent that executes tasks. It communicates with the Discord bot via a local WebSocket or Server-Sent Events (SSE) stream, sending raw execution events.
*   **Communication Bridge (`opencode_client.py`)**: The asynchronous client responsible for maintaining the persistent connection to the OpenCode backend, parsing incoming streams, and dispatching events to the Discord bot.

## 2. Component Architecture

### 2.1 Bot Core (`src/bot.py`)
The main entry point of the Discord bot. It initializes the `discord.ext.commands.Bot` instance, loads necessary Cogs, and establishes the global configuration.

### 2.2 Session Management (`src/cogs/session_manager.py`)
Responsible for managing the lifecycle of an OpenCode session mapped to a Discord channel. It supports two distinct operational modes:

#### Full Control Mode (Auto-Channel Management)
*   **Entry Point**: A dedicated `#welcome` channel acts as the primary interface.
*   **Trigger**: When a user sends their first message in `#welcome`, the bot locks the channel, renames it to reflect the task (e.g., `#task-build-api`), and immediately creates a new `#welcome` channel for the next request.
*   **Isolation**: Each renamed channel represents a completely isolated OpenCode session.
*   **Cleanup**: Provides mechanisms to archive or delete finished task channels to prevent hitting Discord's 500-channel limit.

#### Normal Listening Mode (Opt-in)
*   **Default State**: The bot remains passive and does not listen to messages.
*   **Activation**: Users invoke the `/new` slash command to bind the current channel to a new OpenCode session.
*   **Deactivation**: Users invoke `/exit` to unbind the session and stop the bot from listening in that channel.

### 2.3 User Interface (UI) System (`src/ui/`)

The UI system translates raw OpenCode events into rich Discord components.

#### Progress Embed (`src/ui/progress_embed.py`)
*   **Real-time Updates**: Dynamically updates a Discord Embed message to reflect OpenCode's current execution state (e.g., running `bash`, `read`, `write` tools).
*   **Visual Indicators**: Uses color coding (Yellow for in-progress, Green for success, Red for errors) and displays the history of the 3-5 most recently executed tools.
*   **Rate Limit Mitigation (`src/utils/debouncer.py`)**: To avoid Discord's API rate limits (maximum 5 edits per 5 seconds per message), updates are heavily debounced (typically restricted to one update every 2.5 - 3.0 seconds).
*   **Retry Handling**: Implements Exponential Backoff for HTTP 429 (Too Many Requests) errors to ensure the final state of the UI is eventually consistent.

#### Interactive Question Forms (`src/ui/question_view.py`)
*   **Dynamic Component Generation**: When OpenCode utilizes its `question` tool, the bot dynamically constructs `discord.ui.View` and `discord.ui.Select` components.
*   **Option Mapping**: Translates OpenCode's choices into native Discord dropdown options.
*   **Custom Input Integration**: If a question allows "Custom Input", selecting this option triggers a `discord.ui.Modal`, allowing the user to type a free-form text response.
*   **State Locking**: Once a user selects an answer or submits a modal, the UI components are immediately disabled (`disabled=True`) to prevent duplicate submissions, and the response is routed back to the OpenCode WebSocket.

## 3. Communication Flow

1.  **User Input**: User sends a message or triggers a command in an active Discord channel.
2.  **Dispatch**: The `session_manager` intercepts the message and forwards it via `opencode_client.py` to the OpenCode backend.
3.  **Execution Stream**: OpenCode processes the input and begins streaming events back (e.g., `tool_call_start`, `tool_call_end`, `question`).
4.  **UI Translation**: 
    *   For tool events, the `progress_embed` is updated (throttled by the `debouncer`).
    *   For questions, `question_view` generates and posts the interactive UI.
5.  **User Feedback**: User interacts with the UI (e.g., selects an option), which sends data back to step 2.

## 4. Command Interface

The bot implements slash commands to manage the environment and agent state:
*   `/mode`: Toggles the bot between "Full Control Mode" and "Normal Listening Mode".
*   `/new`: Starts a new session in the current channel (Normal Mode only).
*   `/exit`: Terminates the active session in the current channel.
*   `/agent [name]`: Switches the active OpenCode agent type (e.g., `build`, `plan`, `explore`).