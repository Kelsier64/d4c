# OpenCode Discord Bot Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a Smart Discord Bot (d4c) that acts as a frontend for OpenCode, managing channel-based sessions and rendering real-time UI updates (Embeds/Modals) via WebSocket communication.

**Architecture:** The bot uses `discord.py` with app_commands (Slash Commands) for user interaction. It maintains a WebSocket connection to the OpenCode backend to receive tool execution events and prompts, translating them into Discord Embeds (with debounced updates to respect rate limits) and UI Selects/Modals.

**Tech Stack:** Python 3.12+, `discord.py`, `websockets` (or `aiohttp` for WS client), `python-dotenv`.

---

## Chunk 1: Foundation and WebSocket Client

### Task 1: Setup dependencies and basic WebSocket client structure

**Files:**
- Modify: `pyproject.toml`
- Create: `src/bot.py` (Refactoring `main.py`)
- Create: `src/ws_client.py`

- [ ] **Step 1: Add websockets dependency to pyproject.toml**
Update `dependencies` in `pyproject.toml` to include `"websockets>=12.0",`.

- [ ] **Step 2: Run uv to lock and install dependencies**
Run: `uv sync`

- [ ] **Step 3: Create src/ws_client.py placeholder**
Create a basic asyncio WebSocket client class that can connect to a given URI and has hooks for `on_message`.

- [ ] **Step 4: Refactor main.py to src/bot.py**
Move the bot initialization from `main.py` into `src/bot.py`, keeping the token loading and basic `on_ready`.

- [ ] **Step 5: Commit Foundation**
```bash
git add pyproject.toml uv.lock src/bot.py src/ws_client.py
git commit -m "build: add websockets dependency and base project structure"
```

## Chunk 2: Session Management (Full Control & Normal Mode)

### Task 2: Implement Slash Commands and Mode State

**Files:**
- Modify: `src/bot.py`
- Create: `src/cogs/session_manager.py`

- [ ] **Step 1: Create session_manager cog**
Implement a Cog that holds the current operating mode (`FULL_CONTROL` or `NORMAL`) and a dictionary tracking active sessions by channel ID.

- [ ] **Step 2: Implement /mode, /new, /exit, and /agent commands**
In `session_manager.py`, add slash commands. `/mode` toggles the global state. `/new` (if in NORMAL mode) registers the current channel. `/exit` removes it and provides an option to delete/archive the channel if in FULL_CONTROL mode. `/agent` sends an agent switch command via WS.

- [ ] **Step 3: Implement Full Control #welcome logic**
In the same Cog, add an `on_message` listener. If in `FULL_CONTROL` mode, and the message is in a channel named `welcome` (and not from a bot), rename the channel to `#task-<uuid>`, create a new `#welcome` channel, and register the renamed channel in active sessions.

- [ ] **Step 4: Load Cog in bot.py**
Update `src/bot.py`'s `setup_hook` to load `src.cogs.session_manager`.

- [ ] **Step 5: Commit Session Management**
```bash
git add src/bot.py src/cogs/session_manager.py
git commit -m "feat: implement session management and channel lifecycle"
```

## Chunk 3: Real-time Progress Embeds

### Task 3: Implement Debounced Embed Updater

**Files:**
- Create: `src/ui/progress_embed.py`
- Create: `src/utils/debouncer.py`

- [ ] **Step 1: Create async debouncer**
Implement `src/utils/debouncer.py` with a class `AsyncDebouncer` that groups rapid calls and executes a target async function at most once every 3.0 seconds.

- [ ] **Step 2: Create Progress Embed builder**
Implement `src/ui/progress_embed.py` with a class that maintains a list of recent tool executions and generates a `discord.Embed` (Yellow for running, Green for done, Red for error).

- [ ] **Step 3: Connect WS events to Embed updates with Retry**
Create a manager that listens to WS tool events, updates the `ProgressEmbed` state, and calls the debounced edit function. Wrap the API call in an exponential backoff retry handler (e.g., catching `discord.HTTPException` for 429 status) to handle Discord API limits gracefully.

- [ ] **Step 4: Commit Progress Embeds**
```bash
git add src/ui/progress_embed.py src/utils/debouncer.py
git commit -m "feat: implement debounced progress embeds for tool execution"
```

## Chunk 4: Interactive Questions (UI Components)

### Task 4: Dynamic Selects and Modals

**Files:**
- Create: `src/ui/question_view.py`

- [ ] **Step 1: Create dynamic OpenCodeView and Select**
Refactor the mock view from `main.py` into `src/ui/question_view.py`. Make it accept a list of options from the WS JSON.

- [ ] **Step 2: Implement Custom Input Modal**
Create a `discord.ui.Modal` subclass for the "自行輸入答案" option. When the select callback detects the custom option, return `interaction.response.send_modal()`.

- [ ] **Step 3: Send answers back via WS**
Update the Select callback and Modal submit to disable the UI components (`disabled=True`), edit the message to reflect the choice, and push the JSON answer payload back to the WebSocket client.

- [ ] **Step 4: Commit UI Components**
```bash
git add src/ui/question_view.py
git commit -m "feat: implement dynamic selects and modals for opencode questions"
```