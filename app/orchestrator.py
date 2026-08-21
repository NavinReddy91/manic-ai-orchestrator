"""
Production-grade Orchestrator
Implements best practices from CrewAI, MetaGPT, and AutoGPT
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from .agent import Agent, AgentState, AgentMemory
from .events import (
    event_bus, emit_task_started, emit_task_completed, 
    emit_task_failed, emit_agent_activated, emit_agent_deactivated,
    emit_llm_call_started, emit_llm_call_completed
)
from .models import Task, AgentRun
from .org_chart import ORG_CHART
from .llm import call_llm
from .config import settings

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Production-grade orchestrator with:
    - Event-driven architecture
    - Agent state management
    - Memory management
    - Observability and tracing
    - Error handling and recovery
    """
    
    def __init__(self, db: Session, task: Task):
        self.db = db
        self.task = task
        self.agents: Dict[str, Agent] = {}
        self.execution_log: List[Dict[str, Any]] = []
        
        # Initialize agents from org chart
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize agents from organization chart"""
        for agent_key, agent_config in ORG_CHART.items():
            agent = Agent(
                id=f"{self.task.id}_{agent_key}",
                name=agent_config["label"],
                role=agent_config["team"],
                goal=agent_config.get("goal", ""),
                capabilities=agent_config.get("capabilities", [])
            )
            self.agents[agent_key] = agent
    
    async def execute(self) -> str:
        """
        Execute task with full orchestration
        """
        try:
            emit_task_started(self.task.id)
            logger.info(f"Starting task execution: {self.task.id}")
            
            # Update task status
            self.task.status = "running"
            self.task.started_at = datetime.utcnow()
            self.db.commit()
            
            # Step 1: CEO plans execution
            ceo_result = await self._execute_ceo_planning()
            
            # Step 2: Execute departments sequentially
            departments = ceo_result.get("departments", [])
            accumulated_context = ""
            
            for dept_info in departments:
                dept_key = dept_info["agent_key"]
                dept_instructions = dept_info["instructions"]
                
                # Execute department
                dept_result = await self._execute_department(
                    dept_key, 
                    dept_instructions, 
                    accumulated_context
                )
                
                # Accumulate context
                accumulated_context += f"\n\n[{dept_key} completed]:\n{dept_result}"
            
            # Step 3: CEO reviews and compiles final result
            final_result = await self._execute_ceo_review(accumulated_context)
            
            # Mark task as completed
            self.task.status = "done"
            self.task.final_report = final_result
            self.task.completed_at = datetime.utcnow()
            self.db.commit()
            
            emit_task_completed(
                self.task.id, 
                final_result, 
                self.task.tokens_used
            )
            
            logger.info(f"Task completed: {self.task.id}")
            return final_result
            
        except Exception as e:
            logger.exception(f"Task execution failed: {e}")
            self.task.status = "failed"
            self.task.final_report = f"Execution failed: {str(e)}"
            self.task.completed_at = datetime.utcnow()
            self.db.commit()
            
            emit_task_failed(self.task.id, str(e))
            raise
    
    async def _execute_ceo_planning(self) -> Dict[str, Any]:
        """CEO plans task execution"""
        ceo = self.agents["ceo"]
        ceo.state = AgentState.THINKING
        
        emit_agent_activated(self.task.id, "ceo")
        
        # Get CEO system prompt
        ceo_system = ORG_CHART["ceo"]["system"]
        
        # Prepare context
        context = f"Task: {self.task.prompt}"
        
        # Call LLM
        emit_llm_call_started(self.task.id, "ceo", settings.llm_model)
        start_time = datetime.utcnow()
        
        response = await call_llm(ceo_system, context, max_tokens=800)
        
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        tokens = len(response) // 4
        emit_llm_call_completed(self.task.id, "ceo", tokens, duration_ms)
        
        # Update token usage
        self.task.tokens_used += tokens
        self.task.llm_call_count += 1
        self.db.commit()
        
        # Parse response
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Fallback: default to marketing
            result = {
                "departments": [
                    {"agent_key": "marketing_head", "instructions": self.task.prompt}
                ]
            }
        
        ceo.state = AgentState.COMPLETED
        emit_agent_deactivated(self.task.id, "ceo", "completed")
        
        return result
    
    async def _execute_department(
        self, 
        dept_key: str, 
        instructions: str, 
        context: str
    ) -> str:
        """Execute a department"""
        if dept_key not in self.agents:
            logger.warning(f"Unknown department: {dept_key}")
            return f"Department {dept_key} not found"
        
        agent = self.agents[dept_key]
        agent.state = AgentState.THINKING
        
        emit_agent_activated(self.task.id, dept_key)
        
        # Get department system prompt
        dept_system = ORG_CHART[dept_key]["system"]
        
        # Prepare full context
        full_context = f"Instructions: {instructions}\n\nContext: {context}"
        
        # Call LLM
        emit_llm_call_started(self.task.id, dept_key, settings.llm_model)
        start_time = datetime.utcnow()
        
        response = await call_llm(dept_system, full_context, max_tokens=1000)
        
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        tokens = len(response) // 4
        emit_llm_call_completed(self.task.id, dept_key, tokens, duration_ms)
        
        # Update token usage
        self.task.tokens_used += tokens
        self.task.llm_call_count += 1
        self.db.commit()
        
        # Update agent state
        agent.state = AgentState.COMPLETED
        agent.memory.add_observation({
            "instructions": instructions,
            "result": response
        })
        
        emit_agent_deactivated(self.task.id, dept_key, "completed")
        
        return response
    
    async def _execute_ceo_review(self, accumulated_context: str) -> str:
        """CEO reviews and compiles final result"""
        ceo = self.agents["ceo"]
        ceo.state = AgentState.THINKING
        
        emit_agent_activated(self.task.id, "ceo")
        
        # Get CEO review prompt
        review_system = ORG_CHART["ceo"]["review_system"]
        
        # Call LLM
        emit_llm_call_started(self.task.id, "ceo", settings.llm_model)
        start_time = datetime.utcnow()
        
        response = await call_llm(
            review_system, 
            accumulated_context, 
            max_tokens=800
        )
        
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        tokens = len(response) // 4
        emit_llm_call_completed(self.task.id, "ceo", tokens, duration_ms)
        
        # Update token usage
        self.task.tokens_used += tokens
        self.task.llm_call_count += 1
        self.db.commit()
        
        ceo.state = AgentState.COMPLETED
        emit_agent_deactivated(self.task.id, "ceo", "completed")
        
        # Parse response
        try:
            result = json.loads(response)
            return result.get("summary", response)
        except json.JSONDecodeError:
            return response
    
    def get_execution_log(self) -> List[Dict[str, Any]]:
        """Get execution log for debugging"""
        return self.execution_log
    
    def get_agent_status(self, agent_key: str) -> Optional[Dict[str, Any]]:
        """Get agent status"""
        if agent_key in self.agents:
            return self.agents[agent_key].get_status()
        return None
