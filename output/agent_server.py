"""
OpenHands Agent Server
FastAPI server untuk menghubungkan UI dengan OpenHands Dev Agent
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from dev_agent import DevAgent, ChatMessage, AgentState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============== Pydantic Models ==============

class ChatRequest(BaseModel):
    message: str
    workspace_path: Optional[str] = None


class FileReadRequest(BaseModel):
    path: str
    workspace_path: Optional[str] = None


class FileWriteRequest(BaseModel):
    path: str
    content: str
    workspace_path: Optional[str] = None


class TerminalRequest(BaseModel):
    command: str
    workspace_path: Optional[str] = None


# ============== Connection Manager ==============

class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.agent_status_subscribers: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")


# ============== Global State ==============

manager = ConnectionManager()
agent: Optional[DevAgent] = None


# ============== Lifespan ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - initialize and cleanup"""
    global agent
    
    logger.info("🚀 Starting OpenHands Agent Server...")
    
    # Initialize agent
    api_key = os.getenv("LLM_API_KEY")
    workspace_path = os.getenv("WORKSPACE_PATH", "/workspace")
    
    if not api_key:
        logger.warning("⚠️ LLM_API_KEY not set. Agent will run in limited mode.")
    
    agent = DevAgent(
        api_key=api_key,
        workspace_path=workspace_path
    )
    
    # Setup callbacks for broadcasting to UI
    def on_status_change(status):
        asyncio.create_task(manager.broadcast({
            'type': 'status_change',
            'data': status
        }))
    
    def on_message(msg):
        asyncio.create_task(manager.broadcast({
            'type': 'message',
            'data': msg
        }))
    
    def on_action(action):
        asyncio.create_task(manager.broadcast({
            'type': 'action',
            'data': action
        }))
    
    agent.on_status_change = on_status_change
    agent.on_message = on_message
    agent.on_action = on_action
    
    # Initialize OpenHands SDK
    if api_key:
        success = await agent.initialize()
        if success:
            logger.info("✅ OpenHands Agent initialized successfully")
        else:
            logger.error("❌ Failed to initialize OpenHands Agent")
    else:
        logger.warning("⚠️ Running without LLM - limited functionality")
        agent.state.status = "ready"
    
    logger.info(f"✅ Server ready at http://0.0.0.0:8000")
    
    yield
    
    # Cleanup
    logger.info("🛑 Shutting down server...")
    agent = None


# ============== FastAPI App ==============

app = FastAPI(
    title="OpenHands Dev Agent API",
    description="API untuk OpenHands AI Agent sesuai UI Mockup",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Static Files (UI) ==============

# Serve the UI
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main UI"""
    return FileResponse("ui/index.html")


# ============== Status Endpoints ==============

@app.get("/api/status")
async def get_status():
    """Get agent status"""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return agent.get_status()


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "agent_ready": agent is not None and agent.state.status != "error"
    }


# ============== Chat Endpoints ==============

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Send message to agent and get response
    This is the main endpoint for interacting with the AI agent
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    if agent.state.status == "error" and not agent.api_key:
        raise HTTPException(
            status_code=400,
            detail="Agent not configured. Set LLM_API_KEY environment variable."
        )
    
    # Update workspace if provided
    if request.workspace_path:
        agent.set_workspace(request.workspace_path)
    
    try:
        # Process message asynchronously
        response = await agent.send_message(request.message)
        
        return {
            "success": True,
            "message": response.to_dict(),
            "agent_status": agent.get_status()
        }
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history")
async def get_chat_history():
    """Get chat history"""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    return {
        "history": agent.get_history()
    }


@app.post("/api/chat/clear")
async def clear_chat():
    """Clear chat history"""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    agent.clear_history()
    return {"success": True, "message": "Chat history cleared"}


# ============== File Endpoints ==============

@app.get("/api/files")
async def list_files(path: str = "/", workspace_path: Optional[str] = None):
    """List files in workspace"""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    workspace = workspace_path or agent.workspace_path
    full_path = os.path.join(workspace, path.lstrip("/"))
    
    try:
        files = []
        if os.path.exists(full_path) and os.path.isdir(full_path):
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                stat = os.stat(item_path)
                files.append({
                    "name": item,
                    "path": os.path.join(path, item),
                    "is_dir": os.path.isdir(item_path),
                    "size": stat.st_size if os.path.isfile(item_path) else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return {"files": sorted(files, key=lambda x: (not x["is_dir"], x["name"]))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/read")
async def read_file(request: FileReadRequest):
    """Read file content"""
    workspace = request.workspace_path or agent.workspace_path
    full_path = os.path.join(workspace, request.path.lstrip("/"))
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"success": True, "content": content, "path": request.path}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {request.path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/write")
async def write_file(request: FileWriteRequest):
    """Write file content"""
    workspace = request.workspace_path or agent.workspace_path
    full_path = os.path.join(workspace, request.path.lstrip("/"))
    
    try:
        # Create parent directories if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(request.content)
        
        return {"success": True, "message": f"File written: {request.path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...), workspace_path: Optional[str] = None):
    """Upload file to workspace"""
    workspace = workspace_path or agent.workspace_path
    full_path = os.path.join(workspace, file.filename)
    
    try:
        contents = await file.read()
        with open(full_path, 'wb') as f:
            f.write(contents)
        
        return {"success": True, "message": f"File uploaded: {file.filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Terminal Endpoints ==============

@app.post("/api/terminal")
async def execute_terminal(request: TerminalRequest):
    """Execute terminal command"""
    workspace = request.workspace_path or agent.workspace_path
    
    try:
        process = await asyncio.create_subprocess_shell(
            request.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "success": process.returncode == 0,
            "returncode": process.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else ""
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== WebSocket Endpoint ==============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    Clients can subscribe to receive:
    - Agent status changes
    - New messages
    - Action updates
    """
    await manager.connect(websocket)
    
    # Send initial status
    if agent:
        await manager.send_personal(websocket, {
            'type': 'status_change',
            'data': agent.get_status()
        })
        
        # Send intro message if no history
        if len(agent.get_history()) == 0:
            await manager.send_personal(websocket, {
                'type': 'message',
                'data': {
                    'id': 'intro',
                    'role': 'agent',
                    'content': agent.get_intro_message(),
                    'timestamp': datetime.now().isoformat()
                }
            })
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            if data.get('type') == 'ping':
                await manager.send_personal(websocket, {'type': 'pong'})
            elif data.get('type') == 'chat':
                if agent:
                    message = data.get('message', '')
                    if message:
                        await agent.send_message(message)
            elif data.get('type') == 'set_workspace':
                if agent:
                    path = data.get('path', '/workspace')
                    agent.set_workspace(path)
                    await manager.send_personal(websocket, {
                        'type': 'workspace_changed',
                        'data': {'path': path}
                    })
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from WebSocket")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============== Main ==============

def main():
    """Run the server"""
    uvicorn.run(
        "agent_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()