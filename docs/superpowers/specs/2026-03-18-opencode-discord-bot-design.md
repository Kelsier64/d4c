# OpenCode Discord Bot (d4c) - Design Specification

## 1. Overview
此文件描述了 `d4c` (OpenCode Discord Bot) 的系統架構與設計。目標是建立一個能讓 Discord 使用者直接與 OpenCode 互動的機器人，支援兩種頻道管理模式，並能透過 Discord 原生 UI (Embeds, Select, Modals) 即時展示 OpenCode 的執行進度與提問。

## 2. Architecture: Smart Bot with WebSocket
*   **前端 (Discord Bot)**: 使用 `discord.py` 開發的 "Smart Bot"。負責處理 Discord API 的限制、渲染 UI、管理頻道狀態。
*   **後端 (OpenCode Service)**: 透過本地 WebSocket (或 HTTP API) 與 Bot 通訊。
*   **職責劃分**: 
    *   後端只負責發送原始事件 (例如: `tool_use_start`, `question_ask`)。
    *   Bot 負責將這些事件轉換為 Discord 的 Embed 更新或 UI 互動元件。

## 3. Channel Management & Session Lifecycle
Bot 支援兩種運行模式，並可透過 Slash Command 切換。

### 3.1 完全控制模式 (Full Control Mode)
*   **入口**: 伺服器中固定存在一個 `#welcome` 頻道作為首頁。
*   **觸發**: 使用者在 `#welcome` 發送第一則訊息時，Bot 會鎖定該頻道並將其重新命名為任務名稱 (例如 `#task-build-bot`)，隨後自動建立一個全新的 `#welcome` 頻道。
*   **清理機制 (Channel Cleanup)**: 當任務完成或呼叫結束指令時，Bot 可提供選項將該頻道封存 (Archive) 或刪除，避免達到 Discord 的 500 個頻道上限。
*   **Session**: 每個改名後的頻道代表一個獨立的 OpenCode Session。

### 3.2 正常監聽模式 (Normal Mode)
*   **預設**: Bot 不主動監聽任何頻道。
*   **啟動**: 使用者輸入 `/new`，Bot 開始在當前頻道綁定 Session 並監聽對話。
*   **停止**: 使用者輸入 `/exit`，Bot 解除綁定。

## 4. UI Interaction & Progress Display

### 4.1 即時進度展示 (Progress Embed)
*   **動態更新**: Bot 使用 Embed 顯示 OpenCode 目前的執行進度 (如 `bash`, `read`, `write`)。
*   **Debounce 機制**: 為避免觸發 Discord API Rate Limit (5 edits per 5 seconds)，Embed 更新頻率限制為每 2.5 - 3.0 秒一次。
*   **重試處理 (Retry Handler)**: 遇到 HTTP 429 錯誤時，Bot 需具備退避重試的邏輯 (Exponential Backoff)，以保證 UI 最終能正確更新而不被 API 暫時封鎖。
*   **視覺設計**: 執行中為黃色，完成為綠色，錯誤為紅色。顯示最近執行的 3-5 個工具。

### 4.2 互動提問 (Interactive Questions)
*   當 OpenCode 呼叫 `question` 工具時，Bot 動態產生 `discord.ui.View` 與 `discord.ui.Select`。
*   **選項映射**: 將 OpenCode 傳來的選項轉為 Discord Select Options。
*   **自訂輸入 (Custom Input)**: 若選項包含「自行輸入」，使用者選擇後彈出 Discord Modal 讓其輸入文字。
*   **狀態鎖定**: 選擇後立即禁用 (`disabled=True`) 該 Select，並將答案透過 WebSocket 傳回 OpenCode。

## 5. Slash Commands
繼承並擴充 OpenCode 的指令：
*   `/mode`: 切換「完全控制模式」與「正常監聽模式」。
*   `/new`: (正常模式下) 在當前頻道啟動監聽。
*   `/exit`: (正常模式下) 停止當前頻道監聽。
*   `/agent [name]`: 切換 OpenCode 的 Agent (例如 `build`, `plan`)。