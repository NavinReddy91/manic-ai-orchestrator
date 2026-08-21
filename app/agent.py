"""
Production-grade Agent Architecture
Based on best practices from CrewAI, MetaGPT, and AutoGPT
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent execution states"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentMemory(BaseModel):
    """Agent memory management"""
    short_term: List[Dict[str, Any]] = Field(default_factory=list)
    long_term: Dict[str, Any] = Field(default_factory=dict)
    working_memory: Dict[str, Any] = Field(default_factory=dict)
    
    def add_observation(self, observation: Dict[str, Any]):
        """Add to short-term memory"""
        self.short_term.append({
            "timestamp": datetime.utcnow().isoformat(),
            "data": observation
        })
        # Keep only last 10 observations
        if len(self.short_term) > 10:
            self.short_term = self.short_term[-10:]
    
    def get_context(self) -> str:
        """Get memory context for LLM"""
        context_parts = []
        
        if self.short_term:
            context_parts.append("Recent observations:")
            for obs in self.short_term[-3:]:
                context_parts.append(f"- {json.dumps(obs['data'])}")
        
        if self.working_memory:
            context_parts.append("\nWorking memory:")
            context_parts.append(json.dumps(self.working_memory))
        
        return "\n".join(context_parts)


class AgentMessage(BaseModel):
    """Message passed between agents"""
    sender: str
    receiver: str
    content: str
    message_type: str = "task"  # task, result, feedback, error
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Agent(BaseModel):
    """
    Production-grade Agent with state management, memory, and message passing
    """
    id: str
    name: str
    role: str
    goal: str
    state: AgentState = AgentState.IDLE
    memory: AgentMemory = Field(default_factory=AgentMemory)
    messages: List[AgentMessage] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    
    # Execution config
    max_iterations: int = 5
    current_iteration: int = 0
    
    class Config:
        arbitrary_types_allowed = True
    
    def think(self, context: str) -> str:
        """Agent thinks about what to do next"""
        self.state = AgentState.THINKING
        logger.info(f"Agent {self.name} is thinking...")
        
        # Add to working memory
        self.memory.working_memory["last_thought"] = context
        
        return context
    
    def act(self, action: str) -> Dict[str, Any]:
        """Agent performs an action"""
        self.state = AgentState.ACTING
        logger.info(f"Agent {self.name} is acting: {action}")
        
        result = {
            "action": action,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to memory
        self.memory.add_observation(result)
        
        return result
    
    def observe(self, observation: Dict[str, Any]):
        """Agent observes and learns"""
        self.state = AgentState.OBSERVING
        self.memory.add_observation(observation)
        logger.info(f"Agent {self.name} observed: {observation}")
    
    def send_message(self, receiver: str, content: str, msg_type: str = "task"):
        """Send message to another agent"""
        message = AgentMessage(
            sender=self.id,
            receiver=receiver,
            content=content,
            message_type=msg_type
        )
        self.messages.append(message)
        logger.info(f"Agent {self.name} sent message to {receiver}")
        return message
    
    def receive_message(self, message: AgentMessage):
        """Receive message from another agent"""
        self.messages.append(message)
        self.observe({"received_message": message.dict()})
        logger.info(f"Agent {self.name} received message from {message.sender}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status"""
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "state": self.state.value,
            "iteration": self.current_iteration,
            "memory_size": len(self.memory.short_term),
            "message_count": len(self.messages)
        }
    
    def reset(self):
        """Reset agent state"""
        self.state = AgentState.IDLE
        self.current_iteration = 0
        self.memory = AgentMemory()
        self.messages = []
        logger.info(f"Agent {self.name} reset")
