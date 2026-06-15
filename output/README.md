# OpenHands Dev AI Agent

AI Agent sesuai dengan desain UI Mockup - menggunakan **OpenHands SDK** sebagai engine AI.

## 🚀 Fitur

- 💬 **Chat Interface** - Interface obrolan interaktif untuk berkomunikasi dengan AI Agent
- 📁 **File Operations** - Membaca, menulis, dan mengedit file di workspace
- 💻 **Terminal** - Menjalankan perintah shell langsung dari UI
- 🌐 **Web Preview** - Preview aplikasi web
- 🔄 **Real-time Updates** - WebSocket untuk update status dan pesan secara real-time
- 🤖 **OpenHands SDK** - Powered by OpenHands Software Agent SDK

## 📋 Prerequisites

- Python 3.10+
- uv package manager (direkomendasikan)
- LLM API Key (OpenAI, Anthropic, atau OpenHands Cloud)

## 🛠️ Installation

### 1. Clone/Download Project

```bash
cd /workspace/output
```

### 2. Install Dependencies

Menggunakan uv (direkomendasikan):
```bash
uv sync
```

Atau menggunakan pip:
```bash
pip install -r requirements.txt
```

### 3. Set Environment Variables

```bash
# Set LLM API Key (wajib)
export LLM_API_KEY=your-api-key-here

# Optional: Set model (default: anthropic/claude-sonnet-4-5-20250929)
export LLM_MODEL=anthropic/claude-sonnet-4-5-20250929

# Optional: Set workspace path (default: /workspace)
export WORKSPACE_PATH=/workspace
```

### 4. Run the Server

```bash
cd /workspace/output
uv run python agent_server.py
```

Atau:
```bash
python agent_server.py
```

### 5. Open Browser

Buka browser dan kunjungi:
```
http://localhost:8000
```

## 📁 Project Structure

```
output/
├── agent_server.py      # FastAPI server - main entry point
├── dev_agent.py         # OpenHands Agent configuration
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── ui/
    └── index.html      # Frontend UI (served by FastAPI)
```

## 🔧 Configuration

### Model Selection

Default model menggunakan Anthropic Claude. Untuk menggunakan model lain:

```bash
# OpenAI GPT-4
export LLM_MODEL=openai/gpt-4-turbo
export LLM_API_KEY=sk-...

# OpenHands Cloud (recommended for best results)
export LLM_MODEL=openhands/claude-sonnet-4-5-20250929
export LLM_API_KEY=oh-... # Get from OpenHands Cloud
```

### Workspace Path

```bash
export WORKSPACE_PATH=/path/to/your/project
```

## 🎮 Usage

### Basic Chat

1. Ketik pesan di input box
2. Tekan Enter atau klik tombol Send
3. Agent akan memproses dan merespons
4. Lihat output di terminal/workspace panel

### File Operations

Agent secara otomatis bisa:
- Read file: `Read the file at /workspace/app/main.py`
- Write file: `Create a new file called hello.py`
- Edit file: `Modify the function to add error handling`

### Terminal Commands

Gunakan tab Terminal untuk:
- Menjalankan command shell
- npm/yarn commands
- Git commands
- Build commands

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get agent status |
| `/api/chat` | POST | Send message to agent |
| `/api/chat/history` | GET | Get chat history |
| `/api/chat/clear` | POST | Clear chat history |
| `/api/files` | GET | List files in workspace |
| `/api/files/read` | POST | Read file content |
| `/api/files/write` | POST | Write file content |
| `/api/terminal` | POST | Execute terminal command |
| `/ws` | WebSocket | Real-time updates |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│              UI (HTML/CSS/JS)               │
│  - Activity Bar                             │
│  - Chat Panel                               │
│  - Workspace Panel (Code/Terminal/Preview)  │
└─────────────────┬───────────────────────────┘
                  │ HTTP/WebSocket
                  ▼
┌─────────────────────────────────────────────┐
│           FastAPI Server                    │
│  - REST API                                 │
│  - WebSocket Handler                        │
│  - Static File Server                       │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│         OpenHands SDK                       │
│  - LLM (Claude/GPT/etc.)                    │
│  - Agent                                    │
│  - Conversation                             │
│  - Tools (Terminal, FileEditor, TaskTracker)│
└─────────────────────────────────────────────┘
```

## 🛠️ Development

### Run in Development Mode

```bash
uv run uvicorn agent_server:app --reload --host 0.0.0.0 --port 8000
```

### Testing API

```bash
# Health check
curl http://localhost:8000/api/health

# Send message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, create a simple hello world Python file"}'

# List files
curl http://localhost:8000/api/files
```

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📚 Resources

- [OpenHands Documentation](https://docs.openhands.dev/)
- [OpenHands SDK Reference](https://docs.openhands.dev/sdk/)
- [OpenHands GitHub](https://github.com/All-Hands-AI/OpenHands)