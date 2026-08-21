"""
Event-driven architecture for observability and tracing
Based on CrewAI's event system
"""
from enum import Enum
from typing import Optional, Dict, Any, Callable, List
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Event types for observability"""
    # Task events
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    
    # Agent events
    AGENT_ACTIVATED = "agent_activated"
    AGENT_DEACTIVATED = "agent_deactivated"
    AGENT_THINKING = "agent_thinking"
    AGENT_ACTING = "agent_acting"
    AGENT_OBSERVING = "agent_observing"
    
    # LLM events
    LLM_CALL_STARTED = "llm_call_started"
    LLM_CALL_COMPLETED = "llm_call_completed"
    LLM_CALL_FAILED = "llm_call_failed"
    
    # Token events
    TOKEN_BUDGET_CHECK = "token_budget_check"
    TOKEN_BUDGET_EXCEEDED = "token_budget_exceeded"
    
    # System events
    SYSTEM_ERROR = "system_error"
    SYSTEM_WARNING = "system_warning"


class Event(BaseModel):
    """Event model for observability"""
    event_type: EventType
    task_id: Optional[str] = None
    agent_key: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "agent_key": self.agent_key,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }


class EventBus:
    """
    Event bus for publish-subscribe pattern
    Enables observability and tracing
    """
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._event_history: List[Event] = []
        self._max_history = 1000
    
    def subscribe(self, event_type: EventType, callback: Callable):
        """Subscribe to an event type"""
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to {event_type.value}")
    
    def publish(self, event: Event):
        """Publish an event to all subscribers"""
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
        
        # Notify subscribers
        for callback in self._subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")
        
        # Log event
        logger.info(f"Event: {event.event_type.value} | Task: {event.task_id} | Agent: {event.agent_key}")
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Event]:
        """Get event history"""
        if event_type:
            events = [e for e in self._event_history if e.event_type == event_type]
        else:
            events = self._event_history
        
        return events[-limit:]
    
    def clear_history(self):
        """Clear event history"""
        self._event_history = []


# Global event bus instance
event_bus = EventBus()


# Convenience functions
def emit_task_created(task_id: str, prompt: str, organization_id: str):
    """Emit task created event"""
    event_bus.publish(Event(
        event_type=EventType.TASK_CREATED,
        task_id=task_id,
        data={"prompt": prompt, "organization_id": organization_id}
    ))


def emit_task_started(task_id: str):
    """Emit task started event"""
    event_bus.publish(Event(
        event_type=EventType.TASK_STARTED,
        task_id=task_id
    ))


def emit_task_completed(task_id: str, result: str, tokens_used: int):
    """Emit task completed event"""
    event_bus.publish(Event(
        event_type=EventType.TASK_COMPLETED,
        task_id=task_id,
        data={"result": result, "tokens_used": tokens_used}
    ))


def emit_task_failed(task_id: str, error: str):
    """Emit task failed event"""
    event_bus.publish(Event(
        event_type=EventType.TASK_FAILED,
        task_id=task_id,
        data={"error": error}
    ))


def emit_agent_activated(task_id: str, agent_key: str):
    """Emit agent activated event"""
    event_bus.publish(Event(
        event_type=EventType.AGENT_ACTIVATED,
        task_id=task_id,
        agent_key=agent_key
    ))


def emit_agent_deactivated(task_id: str, agent_key: str, status: str):
    """Emit agent deactivated event"""
    event_bus.publish(Event(
        event_type=EventType.AGENT_DEACTIVATED,
        task_id=task_id,
        agent_key=agent_key,
        data={"status": status}
    ))


def emit_llm_call_started(task_id: str, agent_key: str, model: str):
    """Emit LLM call started event"""
    event_bus.publish(Event(
        event_type=EventType.LLM_CALL_STARTED,
        task_id=task_id,
        agent_key=agent_key,
        data={"model": model}
    ))


def emit_llm_call_completed(task_id: str, agent_key: str, tokens: int, duration_ms: int):
    """Emit LLM call completed event"""
    event_bus.publish(Event(
        event_type=EventType.LLM_CALL_COMPLETED,
        task_id=task_id,
        agent_key=agent_key,
        data={"tokens": tokens, "duration_ms": duration_ms}
    ))


def emit_token_budget_exceeded(task_id: str, tokens_used: int, token_budget: int):
    """Emit token budget exceeded event"""
    event_bus.publish(Event(
        event_type=EventType.TOKEN_BUDGET_EXCEEDED,
        task_id=task_id,
        data={"tokens_used": tokens_used, "token_budget": token_budget}
    ))
