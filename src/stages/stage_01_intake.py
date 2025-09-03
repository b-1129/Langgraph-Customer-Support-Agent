"""
Stage 01: INTAKE
Accept and validate incoming payload

This is the entry point of our workflow. It receives the customer's request
and creates the initial state that will flow through all other stages.
"""

from typing import Dict, Any
from datetime import datetime
import logging
from pydantic import ValidationError
from agent.state_manager import AgentState, StateManager, StageStatus

logger = logging.getLogger(__name__)

class IntakeStage:
    """
    Stage 01: INTAKE
    
    Responsibilities:
    - Aceept incoming customer request payload
    - Validate required fields
    - Create initial agent state
    - Set up session tracking
    
    This stage is "payload_only" - it doesn't call external services,
    just processes the input data.
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.stage_id = 1
        self.stage_name = "INTAKE"

    async def execute(self, input_payload: Dict[str, Any]) -> AgentState:
        """
        Execute the INTAKE stage.

        Args:
            input_payload: Raw customer request data
        
        Returns:
            Initial AgentState with validated data
        """

        start_time = datetime.now()

        try:
            logger.info(f"starting {self.stage_name} stage")

            # Validate reqired fields
            validation_errors = self._validate_payload(input_payload)
            if validation_errors:
                error_msg = f"Payload validation failed: {','.join(validation_errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Extract validated fields
            customer_name = input_payload["customer_name"]
            email = input_payload["email"]
            query = input_payload["query"]
            priority = input_payload.get("priority", "medium")
            ticket_id = input_payload.get("ticket_id")

            # Create initial state
            initial_state = self.state_manager.create_initial_state(
                customer_name=customer_name,
                email=email,
                query=query,
                priority=priority,
                ticket_id=ticket_id
            )

            # Log successful execution
            execution_time = ((datetime.now() - start_time).total_seconds() * 1000)

            self.state_manager.log_stage_execution(
                session_id=initial_state["session_id"],
                stage_id=self.stage_id,
                stage_name=self.stage_name,
                status=StageStatus.COMPLETED,
                abilities_executed=["accept_payload"],
                server_used=None, # No external server used
                duration_ms=execution_time,
                output={
                    "ticket_id":initial_state["ticket_id"],
                    "session_id":initial_state["session_id"],
                    "validation_passed":True
                }
            )

            logger.info(f"{self.stage_name} completed successfully")
            logger.info(f"Created ticket: {initial_state["ticket_id"]}")
            logger.info(f"Session ID: {initial_state["session_id"]}")

            return initial_state
        
        except Exception as e:
            # Log error
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create minimal state for error tracking if possible
            try:
                session_state = self.state_manager.create_initial_state(
                    customer_name=input_payload.get("customer_name", "Unknown"),
                    email=input_payload.get("email", "unknown@example.com"),
                    query=input_payload.get("query", "Failed to process"),
                    priority="high",  # High priority for failed intakes
                    ticket_id=None
                )
                
                self.state_manager.log_stage_execution(
                    session_id=session_state["session_id"],
                    stage_id=self.stage_id,
                    stage_name=self.stage_name,
                    status=StageStatus.FAILED,
                    abilities_executed=["accept_payload"],
                    duration_ms=execution_time,
                    error_message=str(e)
                )
            except:
                pass  # If we can't even create basic state, just continue with the error
            
            logger.error(f"{self.stage_name} failed: {str(e)}")

    def _validate_payload(self, payload: Dict[str, Any]) -> list[str]:
        """
        Validate the incoming payload for required fields and formats.
        
        Args:
            payload: Raw input payload
            
        Returns:
            List of validation errors (empty if valid)
        """
        
        errors = []
        
        # Required fields check
        required_fields = ["customer_name", "email", "query"]
        for field in required_fields:
            if not payload.get(field):
                errors.append(f"Missing required field: {field}")
            elif not isinstance(payload[field], str) or not payload[field].strip():
                errors.append(f"Field '{field}' must be a non-empty string")
        
        # Email format validation (basic)
        email = payload.get("email", "")
        if email and "@" not in email:
            errors.append("Invalid email format")
        
        # Priority validation
        priority = payload.get("priority", "medium")
        if priority and priority not in ["low", "medium", "high", "urgent"]:
            errors.append(f"Invalid priority '{priority}'. Must be: low, medium, high, or urgent")
        
        # Query length validation
        query = payload.get("query", "")
        if len(query) > 5000:
            errors.append("Query too long (max 5000 characters)")
        
        return errors
    
    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Accept and validate incoming customer request payload",
            "mode": "payload_only",
            "abilities": ["accept_payload"],
            "required_input": ["customer_name", "email", "query"],
            "optional_input": ["priority", "ticket_id"],
            "next_stage": "UNDERSTAND"
        }