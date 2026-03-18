# OpenCode Discord Bot Backend Bridge Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the WebSocket client into an HTTP/SSE client that directly communicates with the real OpenCode server via REST (`POST /session`, `POST /session/:id/message`) and SSE (`GET /global/event`).

**Architecture:** Use `aiohttp` to perform HTTP POST requests for commands and messages. Run a background task that consumes the `/global/event` SSE endpoint using `aiohttp`'s stream reader. We will parse `message.part.updated` events to look for tool states and questions, updating the Discord embed exactly as we did with the mock websocket.

**Tech Stack:** Python 3.12+, `aiohttp`, `discord.py`.

---

## Chunk 1: SSE and HTTP Client Base

### Task 1: Replace WS with REST/SSE Base Client

**Files:**
- Modify: `pyproject.toml`
- Create: `src/opencode_client.py` (Replacing `src/ws_client.py`)
- Modify: `src/bot.py`

- [ ] **Step 1: Update Dependencies**
Remove `websockets` from `pyproject.toml` and add `aiohttp>=3.9.0`. Update lockfile with `uv sync`.

- [ ] **Step 2: Create opencode_client.py**
Move `ProgressEmbedManager` and `ChannelProgressState` logic from `ws_client.py` to `opencode_client.py` (renaming class to `OpenCodeClient`). 
Add an `aiohttp.ClientSession` initialized on `connect()`.

- [ ] **Step 3: Implement HTTP Methods**
Implement `create_session()` which posts to `http://127.0.0.1:4096/session` and returns the session ID.
Implement `send_message(session_id, content)` which posts to `http://127.0.0.1:4096/session/{session_id}/message`.

- [ ] **Step 4: Update bot.py**
Change the import in `src/bot.py` from `OpenCodeWSClient` to `OpenCodeClient` and update the initialization. Run `uv run ruff check .` to fix imports.

- [ ] **Step 5: Commit Client Base**
```bash
git rm src/ws_client.py
git add pyproject.toml uv.lock src/opencode_client.py src/bot.py
git commit -m "refactor: replace websockets with aiohttp client for opencode server"
```

## Chunk 2: SSE Event Loop

### Task 2: Implement SSE stream consumer

**Files:**
- Modify: `src/opencode_client.py`

- [ ] **Step 1: SSE Listener Loop**
In `OpenCodeClient.connect()`, after creating the `aiohttp` session, open a GET request to `http://127.0.0.1:4096/global/event` using `stream=True`.

- [ ] **Step 2: Parse SSE Data**
Iterate over `response.content`. If a line starts with `data: `, decode the JSON payload. Handle `message.part.updated` events. 

- [ ] **Step 3: Map Events to Discord UI**
When parsing `message.part.updated`, check `part["tool"]` and `part["state"]["status"]` (`running` vs `done`/`error`). Feed this into the existing `ChannelProgressState.update_and_render()` logic. Note: Since `global/event` has `sessionID`, we need a mapping from `sessionID` to `channel_id` (this will be populated when the cog creates a session).

- [ ] **Step 4: Commit SSE Loop**
```bash
git add src/opencode_client.py
git commit -m "feat: implement SSE event loop to capture opencode progress"
```

## Chunk 3: Integrate with Session Manager Cog

### Task 3: Use OpenCode API in Bot Commands

**Files:**
- Modify: `src/cogs/session_manager.py`
- Modify: `src/opencode_client.py`

- [ ] **Step 1: Connect /new and #welcome to API**
In `src/cogs/session_manager.py`, when a new session is created (via `/new` or in `#welcome`), call `bot.ws_client.create_session()`. Store the returned OpenCode `session_id` in the `active_sessions` dict, and register the reverse mapping `session_id -> channel_id` in `OpenCodeClient`.

- [ ] **Step 2: Pass User Messages**
In the `on_message` listener (for both FULL_CONTROL and NORMAL modes), if the channel is an active session and the message is from a user, send it to OpenCode using `bot.ws_client.send_message(session_id, content)`.

- [ ] **Step 3: Handle Session Deletion**
In the `/exit` command and delete button, call a new `bot.ws_client.delete_session(session_id)` method to clean up the backend session.

- [ ] **Step 4: Commit Cog Integration**
```bash
git add src/cogs/session_manager.py src/opencode_client.py
git commit -m "feat: connect discord channels to opencode sessions and forward messages"
```