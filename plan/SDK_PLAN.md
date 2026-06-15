# OpenHands Dev AI Agent - Technical Implementation Plan

## Overview
Membuat AI Agent sesuai dengan desain UI mockup HTML yang menggunakan OpenHands SDK sebagai engine.

## UI Mockup Analysis
- **Activity Bar**: Navigasi utama (Bot, Chat, Files, Git, Settings)
- **Chat Panel**: Panel obrolan dengan selector model dan path workspace
- **Workspace Panel**: Tab untuk Code Editor, Terminal, Browser Preview

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        UI Frontend (HTML)                        │
│  ┌──────────┐  ┌─────────────────┐  ┌──────────────────────────┐ │
│  │ Activity │  │   Chat Panel    │  │    Workspace Panel       │ │
│  │   Bar    │  │  - Messages     │  │  ┌────┬────────┬──────┐  │ │
│  │          │  │  - Input        │  │  │Code│Terminal│Browse│  │ │
│  └──────────┘  └─────────────────┘  │  └────┴────────┴──────┘  │ │
│                                     │  ┌────────────────────┐   │ │
│                                     │  │  Content Area      │   │ │
│                                     │  └────────────────────┘   │ │
└──────────────────────────────────────┴──────────────────────────┘
                                    │
                                    │ HTTP/WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Server (Flask/FAST)                     │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    OpenHands SDK                         │    │
│  │  ┌─────────┐  ┌──────────┐  ┌────────────────────────┐  │    │
│  │  │   LLM   │  │  Agent   │  │     Conversation       │  │    │
│  │  └─────────┘  └──────────┘  └────────────────────────┘  │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │                    Tools                          │    │
│  │  │  TerminalTool | FileEditorTool | TaskTrackerTool │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Agent Server (Python + FastAPI)
- REST API untuk komunikasi dengan UI
- WebSocket untuk real-time updates
- Integrasi dengan OpenHands SDK
- Workspace management

### 2. Tools yang Digunakan
- `TerminalTool` - Eksekusi command shell
- `FileEditorTool` - Read/write/edit file
- `TaskTrackerTool` - Task management

### 3. UI Integration
- Modifikasi HTML mockup untuk koneksi ke agent server
- Real-time message streaming
- File tree visualization
- Terminal output streaming

## API Endpoints

### POST /api/chat
Send message to agent
```json
{
  "message": "string",
  "workspace_path": "string"
}
```

### GET /api/chat/history
Get chat history

### GET /api/files
List files in workspace

### POST /api/terminal
Execute terminal command

### GET /api/terminal/output
Get terminal output stream

### POST /api/files/read
Read file content

### POST /api/files/write
Write file content

## File Structure
```
/workspace/
├── plan/
│   └── SDK_PLAN.md          # This file
├── output/
│   ├── agent_server.py      # Main agent server
│   ├── dev_agent.py         # OpenHands agent configuration
│   ├── api_routes.py        # FastAPI routes
│   ├── websocket_handler.py # WebSocket for real-time comm
│   └── requirements.txt     # Dependencies
├── workspace/               # Agent workspace directory
└── ui/
    └── index.html           # Modified UI mockup
```

## Implementation Steps

1. ✅ Create plan directory
2. ⬜ Create agent_server.py with OpenHands SDK
3. ⬜ Create API routes
4. ⬜ Create WebSocket handler
5. ⬜ Modify UI to connect to server
6. ⬜ Create requirements.txt
7. ⬜ Test the implementation

## Dependencies
- openhands-sdk
- openhands-tools
- fastapi
- uvicorn
- websockets
- python-socketio