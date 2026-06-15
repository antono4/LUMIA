"""
OpenHands Dev AI Agent
AI Agent sesuai dengan UI Mockup - menggunakan OpenHands SDK sebagai engine
"""

import os
import asyncio
import logging
import threading
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import SecretStr

# OpenHands SDK imports
from openhands.sdk import LLM, Agent, Conversation, Event
from openhands.sdk.conversation.types import ConversationCallbackType
from openhands.sdk.tool import Tool
from openhands.sdk.utils.async_utils import AsyncCallbackWrapper
from openhands.sdk import get_logger
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool

# Configure logging
logger = get_logger(__name__)


@dataclass
class ChatMessage:
    """Chat message structure"""
    id: str
    role: str  # 'user' or 'agent'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'actions': self.actions
        }


@dataclass
class AgentState:
    """Agent state management"""
    status: str = "idle"  # idle, thinking, working, completed
    current_task: Optional[str] = None
    message_history: List[ChatMessage] = field(default_factory=list)
    workspace_path: str = "/workspace"
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status,
            'current_task': self.current_task,
            'message_count': len(self.message_history),
            'workspace_path': self.workspace_path,
            'last_error': self.last_error
        }


class DevAgent:
    """
    OpenHands Dev AI Agent - sesuai dengan UI Mockup
    Menggunakan OpenHands SDK untuk capabilities AI Agent
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "anthropic/claude-sonnet-4-5-20250929",
        workspace_path: str = "/workspace",
        base_url: Optional[str] = None
    ):
        """
        Initialize Dev Agent
        
        Args:
            api_key: LLM API key (from LLM_API_KEY env var if not provided)
            model: Model to use (default: anthropic/claude-sonnet-4-5-20250929)
            workspace_path: Path for agent workspace
            base_url: Optional base URL for LLM API
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.model = model
        self.workspace_path = workspace_path
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        
        # State
        self.state = AgentState(workspace_path=workspace_path)
        
        # OpenHands components
        self.llm: Optional[LLM] = None
        self.agent: Optional[Agent] = None
        self.conversation: Optional[Conversation] = None
        
        # Callbacks for UI updates
        self.on_status_change: Optional[Callable] = None
        self.on_message: Optional[Callable] = None
        self.on_action: Optional[Callable] = None
        
        # Thread management
        self._processing_thread: Optional[threading.Thread] = None
        self._is_running = False
        
        logger.info(f"DevAgent initialized with model: {self.model}")
        logger.info(f"Workspace: {self.workspace_path}")
    
    def _initialize_llm(self) -> LLM:
        """Initialize LLM with configuration"""
        if not self.api_key:
            raise ValueError(
                "LLM API key not provided. "
                "Set LLM_API_KEY environment variable or pass api_key parameter."
            )
        
        return LLM(
            model=self.model,
            api_key=SecretStr(self.api_key),
            base_url=self.base_url
        )
    
    def _initialize_agent(self, llm: LLM) -> Agent:
        """Initialize OpenHands Agent with tools"""
        return Agent(
            llm=llm,
            tools=[
                Tool(name=TerminalTool.name),
                Tool(name=FileEditorTool.name),
                Tool(name=TaskTrackerTool.name),
            ],
            description="Dev AI Agent - Helper untuk development",
        )
    
    async def initialize(self) -> bool:
        """
        Initialize OpenHands SDK components
        Returns True if successful, False otherwise
        """
        try:
            logger.info("Initializing OpenHands SDK...")
            
            # Initialize LLM
            self.llm = self._initialize_llm()
            logger.info("✓ LLM initialized")
            
            # Initialize Agent
            self.agent = self._initialize_agent(self.llm)
            logger.info("✓ Agent initialized")
            
            # Initialize Conversation
            self.conversation = Conversation(agent=self.agent)
            logger.info("✓ Conversation initialized")
            
            self.state.status = "ready"
            logger.info("✓ DevAgent fully initialized")
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to initialize: {str(e)}"
            logger.error(error_msg)
            self.state.last_error = error_msg
            self.state.status = "error"
            return False
    
    def _update_status(self, status: str, task: Optional[str] = None):
        """Update agent status and notify UI"""
        self.state.status = status
        if task:
            self.state.current_task = task
        
        if self.on_status_change:
            try:
                self.on_status_change(self.state.to_dict())
            except Exception as e:
                logger.warning(f"Error in status callback: {e}")
    
    async def _event_callback(self, event: Event):
        """Callback for conversation events"""
        # Notify UI about events
        if self.on_action:
            try:
                self.on_action({
                    'type': event.__class__.__name__,
                    'event': str(event)[:500],
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.warning(f"Error in action callback: {e}")
    
    async def send_message(self, message: str) -> ChatMessage:
        """
        Send message to agent and get response
        
        Args:
            message: User message
            
        Returns:
            ChatMessage object with agent response
        """
        if not self.conversation:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        # Create user message
        user_msg = ChatMessage(
            id=f"user_{len(self.state.message_history)}",
            role="user",
            content=message
        )
        self.state.message_history.append(user_msg)
        
        # Notify UI of new message
        if self.on_message:
            self.on_message(user_msg.to_dict())
        
        # Update status
        self._update_status("thinking", f"Processing: {message[:50]}...")
        
        try:
            # Send message to conversation
            logger.info(f"Sending message: {message}")
            self._update_status("working", "Agent is thinking...")
            
            # Create async callback wrapper
            loop = asyncio.get_running_loop()
            callback_coro = self._event_callback
            callback = AsyncCallbackWrapper(callback_coro, loop)
            
            # Add callback to conversation
            if not hasattr(self.conversation, 'callbacks'):
                self.conversation.callbacks = []
            self.conversation.callbacks.append(callback)
            
            # Send message
            self.conversation.send_message(message)
            
            # Run conversation in background thread
            self._is_running = True
            self._processing_thread = threading.Thread(
                target=self._run_conversation_sync
            )
            self._processing_thread.start()
            
            # Wait for completion
            self._processing_thread.join()
            self._is_running = False
            
            # Get final response
            final_response = self.conversation.get_last_response()
            
            # Create agent message
            agent_msg = ChatMessage(
                id=f"agent_{len(self.state.message_history)}",
                role="agent",
                content=final_response or "Task completed.",
            )
            self.state.message_history.append(agent_msg)
            
            # Notify UI
            if self.on_message:
                self.on_message(agent_msg.to_dict())
            
            self._update_status("ready")
            logger.info("Message processed successfully")
            
            return agent_msg
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            self.state.last_error = error_msg
            self._update_status("error")
            
            # Return error message
            error_response = ChatMessage(
                id=f"error_{len(self.state.message_history)}",
                role="agent",
                content=f"Error: {error_msg}"
            )
            return error_response
    
    def _run_conversation_sync(self):
        """Run conversation synchronously (called in thread)"""
        try:
            self.conversation.run()
        except Exception as e:
            logger.error(f"Error in conversation run: {e}")
            self.state.last_error = str(e)
            self._update_status("error")
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get chat history"""
        return [msg.to_dict() for msg in self.state.message_history]
    
    def clear_history(self):
        """Clear chat history"""
        self.state.message_history.clear()
        logger.info("Chat history cleared")
    
    def set_workspace(self, path: str):
        """Change workspace path"""
        self.workspace_path = path
        self.state.workspace_path = path
        
        # Reinitialize conversation with new workspace
        if self.agent:
            self.conversation = Conversation(
                agent=self.agent,
                workspace=path
            )
        logger.info(f"Workspace changed to: {path}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return self.state.to_dict()
    
    def get_intro_message(self) -> str:
        """Get intro message for new session"""
        return (
            f"Halo! Saya adalah **Dev AI Agent** powered by OpenHands. "
            f"Ruang kerja saya adalah `{self.workspace_path}`. "
            f"Saya bisa membantu Anda:\n\n"
            f"📁 **File Operations** - Membaca, menulis, dan mengedit file\n"
            f"💻 **Terminal Commands** - Menjalankan perintah shell\n"
            f"🔍 **Code Analysis** - Menganalisis dan memahami kode\n"
            f"🛠️ **Development Tasks** - Membantu development aplikasi\n\n"
            f"Apa yang ingin kita bangun atau perbaiki hari ini?"
        )


# Standalone usage example
async def main():
    """Example usage of DevAgent"""
    
    # Check for API key
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        print("❌ LLM_API_KEY not set. Please set it first:")
        print("   export LLM_API_KEY=your-api-key")
        return
    
    # Initialize agent
    agent = DevAgent(
        api_key=api_key,
        workspace_path="/workspace"
    )
    
    # Setup callbacks for logging
    def on_status_change(status):
        print(f"[Status] {status['status']}: {status.get('current_task', '')}")
    
    def on_message(msg):
        print(f"\n[{'USER' if msg['role'] == 'user' else 'AGENT'}]")
        print(msg['content'][:200] + "..." if len(msg['content']) > 200 else msg['content'])
    
    def on_action(action):
        print(f"[Action] {action['type']}: {action.get('event', '')[:100]}")
    
    agent.on_status_change = on_status_change
    agent.on_message = on_message
    agent.on_action = on_action
    
    # Initialize
    print("🚀 Initializing DevAgent...")
    if not await agent.initialize():
        print("❌ Failed to initialize agent")
        return
    
    print("✅ Agent ready!\n")
    print(agent.get_intro_message())
    
    # Interactive loop
    print("\n" + "="*50)
    print("DevAgent Interactive Mode")
    print("Type 'exit' to quit")
    print("="*50 + "\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye! 👋")
                break
            
            if not user_input:
                continue
            
            print("\n" + "-"*30)
            response = await agent.send_message(user_input)
            print("-"*30 + "\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())