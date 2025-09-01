"""
State manager for LangGraph Customer Support Agent

This module handles state persistence and management across all stages.
State flows like a pipeline: each stage can read from and write to the state.
"""

from typing import Any, Dict, Optional, List, TypedDict
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
from enum import Enum

class StageStatus(str, Enum):
    """Status of the stage execution"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class ExecutionLog(BaseModel):
    """"Log entry for stage execution"""
    stage_id: int
    stage_name: str
    timestamp: datetime
    status: StageStatus
    abilities_executed: List[str] = []
    server_used: Optional[str] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    output: Optional[Dict[str, Any]] = None

class AgentState(TypedDict):
    """
    Complete state structure that flows through the stages.
    This is like a clipboard that all stages can read from and write to.
    """
    # Original Input (Stage 1: INTAKE)
    customer_name: str
    email: str
    query: str
    priority: str
    ticket_id: Optional[str]

    # Stage 2: UNDERSTAND
    parsed_request: Optional[Dict[str, Any]]
    extracted_entities: Optional[Dict[str, Any]]

    # Stage 3: PREPARE
    normalized_fields: Optional[Dict[str, Any]]
    enriched_records: Optional[Dict[str, Any]]
    calculated_flags: Optional[Dict[str, Any]]

    # Stage 4: ASK
    clarification_needed: Optional[bool]
    questions_asked: Optional[List[str]]
    
    # Stage 5: WAIT
    customer_responses: Optional[Dict[str, Any]]
    
    # Stage 6: RETRIEVE
    knowledge_base_results: Optional[List[Dict[str, Any]]]
    retrieved_solutions: Optional[List[Dict[str, Any]]]
    
    # Stage 7: DECIDE (Critical decision point!)
    solution_scores: Optional[Dict[str, float]]
    escalation_decision: Optional[bool]
    selected_solution: Optional[Dict[str, Any]]
    decision_reasoning: Optional[str]
    
    # Stage 8: UPDATE
    ticket_updates: Optional[Dict[str, Any]]
    ticket_status: Optional[str]
    
    # Stage 9: CREATE
    generated_response: Optional[str]
    
    # Stage 10: DO
    api_calls_executed: Optional[List[str]]
    notifications_sent: Optional[List[str]]
    
    # Stage 11: COMPLETE
    final_payload: Optional[Dict[str, Any]]
    
    # Metadata (maintained throughout)
    session_id: str
    current_stage: str
    execution_log: List[ExecutionLog]
    created_at: datetime
    updated_at: datetime
    errors: List[str]

class StateManager:
    """
    Manages state persistence and transitions between stages.

    Think of this as the "memory" of our agent - it remembers everything
    that happened in previous stages and makes it available to future stages.
    """

    def __init__(self):
        self._state_history: Dict[str, List[AgentState]] = {}

    def create_initial_state(
            self,
            customer_name: str,
            email: str,
            query: str,
            priority: str = "medium",
            ticket_id: Optional[str] = None
    ) -> AgentState:
        """"
        Create the initial state from input payload.
        This is called at stage 1: INTAKE
        """

        session_id = str(uuid.uuid4())
        current_time = datetime.now()

        # Generate ticket_id if not provided
        if not ticket_id:
            ticket_id = f"TKT-{current_time.strftime('%Y%m%d')}-{session_id[:8]}"

        initial_state= AgentState(
            # Input data
            customer_name=customer_name,
            email=email,
            query=query,
            priority=priority,
            ticket_id=ticket_id,

            # Initialize all stage-specific fields as None
            parsed_request=None,
            extracted_entities=None,
            normalized_fields=None,
            enriched_records=None,
            calculated_flags=None,
            clarification_needed=None,
            questions_asked=None,
            customer_responses=None,
            knowledge_base_results=None,
            retrieved_solutions=None,
            solution_scores=None,
            escalation_decision=None,
            selected_solution=None,
            decision_reasoning=None,
            ticket_updates=None,
            ticket_status="open",
            generated_response=None,
            api_calls_executed=None,
            notifications_sent=None,
            final_payload=None,

            # Metadata
            session_id=session_id,
            current_stage="INTAKE",
            execution_log=[],
            created_at=current_time,
            updated_at=current_time,
            errors=[]
        )

        # Store initial state
        self._state_history[session_id] = [initial_state]
        return initial_state
    
    def update_state(
            self,
            session_id: str,
            updates: Dict[str, Any],
            stage_name: str
    ) -> AgentState:
        """"
        Update the state with new information from a stage
        
        Args:
            session_id: Unique session identifier
            updates: Dictionary of fields to update
            stage_name: Name of stage making the update
            
        Returns:
            Updated state
        """

        if session_id not in self._state_history:
            raise ValueError(f"Session ID {session_id} not found")
        
        current_state = self._state_history[session_id][-1].copy()

        # Apply updates to the current state
        for key, value in updates.items():
            if key in current_state:
                current_state[key] = value
            else:
                # Log warning for unknown keys but don't fail
                current_state.setdefault("errors",[]).append(
                    f"Unknown state key: {key} from stage {stage_name}")
                
        # Update metadata
        current_state["current_stage"] = stage_name
        current_state["updated_at"] = datetime.now()

        # Store updated state in history
        self._state_history[session_id].append(current_state)

        return current_state
    
    def get_current_state(self, session_id: str) -> AgentState:
        """Get the most recent state for a given session"""
        if session_id not in self._state_history:
            raise ValueError(f"Session ID {session_id} not found")
        return self._state_history[session_id][-1]
    
    def get_state_history(self, session_id: str) -> List[AgentState]:
        """Get the full state history for debugging or analysis"""
        return self._state_history.get(session_id, [])
    
    def log_stage_execution(
            self,
            session_id: str,
            stage_id: int,
            stage_name: str,
            status: StageStatus,
            abilities_executed: List[str] = None,
            server_used: str = None,
            duration_ms: int = None,
            error_message: str = None,
            output: Dict[str, Any] = None
    ) -> None:
        """
        Log the execution of a stage for debugging and monitoring.
        
        This helps us track what happened at each stage - crucial for debugging!
        """

        if session_id not in self._state_history:
            raise ValueError(f"Session ID {session_id} not found")
        
        log_entry = ExecutionLog(
            stage_id=stage_id,
            stage_name=stage_name,
            timestamp=datetime.now(),
            status=status,
            abilities_executed=abilities_executed or [],
            server_used=server_used,
            duration_ms=duration_ms,
            error_message=error_message,
            output=output
        )

        # Get current state and add log entry
        current_state = self._state_history[session_id][-1]
        current_state["execution_log"].append(log_entry)

        # If there's an error, also add to errors list
        if error_message:
            current_state["errors"].append(f"{stage_name}: {error_message}")

    def is_stage_completed(self, session_id:str, stage_name:str) -> bool:
        """Check if a specific stage has been completed"""
        if session_id not in self._state_history:
            return False
        
        current_state = self._state_history[session_id][-1]

        for log_entry in current_state["execution_log"]:
            if (log_entry.stage_name == stage_name and
                log_entry.status == StageStatus.COMPLETED):
                return True
        return False
    
    def get_stage_output(
            self,
            session_id: str,
            stage_name: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve the output of a specific stage"""
        if session_id not in self._state_history:
            return None
        
        current_state = self._state_history[session_id][-1]

        for log_entry in current_state["execution_log"]:
            if log_entry.stage_name == stage_name:
                return log_entry.output
        return None
    
    def cleanup_session(self, session_id: str) -> None:
        """cleanup state history for a completed session"""
        if session_id in self._state_history:
            del self._state_history[session_id]

# Global state manager instance
state_manager = StateManager()


