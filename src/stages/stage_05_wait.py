"""
Stage 05: WAIT
Wait for and capture human response

This stage handles receiving and processing customer responses
to clarification questions from the ASK stage.
It's a DETERMINISTIC stage - abilities execute in sequence.
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
from agent.state_manager import AgentState, StateManager, StageStatus
from mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class WaitStage:
    """
    Stage 05: WAIT
    
    Responsibilities:
    - Wait for customer response to clarification questions
    - Extract and validate customer answers
    - Store answers in the state for further processing
    
    Mode: Deterministic (abilities execute in sequence)
    Abilities: extract_answer (ATLAS) -> store_answer (state management)
    """

    def __init__(self, state_manager: StateManager, mcp_client: MCPClient):
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.stage_id = 5
        self.stage_name = "WAIT"

        # Define execution order for deterministic mode
        self.execution_order = ["extract_answer", "store_answer"]

    async def execute(self, session_id: str, customer_responses: Optional[Dict[str, Any]] = None) -> AgentState:
        """
        Execute the WAIT stage in deterministic sequence.
        
        Args:
            session_id: Current session identifier
            customer_responses: Customer's responses to questions (if available)
            
        Returns:
            Updated AgentState with customer responses
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting {self.stage_name} stage (deterministic)")

            # Get current state
            current_state = self.state_manager.get_current_state(session_id)

            # Check if we should skip this stage (no clarification was needed)
            if not current_state.get("clarification_needed", False):
                logger.info("No clarification was needed, skipping WAIT stage")
                
                # Log skipped execution
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                self.state_manager.log_stage_execution(
                    session_id=session_id,
                    stage_id=self.stage_id,
                    stage_name=self.stage_name,
                    status=StageStatus.SKIPPED,
                    abilities_executed=[],
                    duration_ms=execution_time,
                    output={"reason": "No clarification needed"}
                )
                
                return current_state
            
            # If no customer responses provided, this means we're still waiting
            if not customer_responses:
                logger.info("Waiting for customer responses...")

                results = {
                    "customer_responses": None,
                    "waiting_for_response": True,
                    "questions_sent_at": datetime.now().isoformat()
                }
                
                updated_state = self.state_manager.update_state(
                    session_id=session_id,
                    updates=results,
                    stage_name=self.stage_name
                )
                
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                
                self.state_manager.log_stage_execution(
                    session_id=session_id,
                    stage_id=self.stage_id,
                    stage_name=self.stage_name,
                    status=StageStatus.IN_PROGRESS,
                    abilities_executed=[],
                    duration_ms=execution_time,
                    output={"status": "waiting_for_customer_response"}
                )
                
                return updated_state
            
            # Process customer responses
            abilities_executed = []
            results = {}

            # Step 1: Extract and validate answers (ATLAS server)
            extract_result = await self._extract_answer(current_state, customer_responses)
            abilities_executed.append("extract_answer")

            logger.info("Customer answers extracted successfully")

            # Step 2: Store answers (state management)
            store_result = self._store_answer(extract_result)
            abilities_executed.append("store_answer")
            results.update(store_result)

            logger.info("Customer answers stored successfully")

            # Update state with results
            updated_state = self.state_manager.update_state(
                session_id=session_id,
                updates=results,
                stage_name=self.stage_name
            )

            # Log successful execution
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            self.state_manager.log_stage_execution(
                session_id=session_id,
                stage_id=self.stage_id,
                stage_name=self.stage_name,
                status=StageStatus.COMPLETED,
                abilities_executed=abilities_executed,
                server_used="ATLAS,STATE",
                duration_ms=execution_time,
                output=results
            )
            
            logger.info(f"{self.stage_name} completed successfully")
            logger.info(f"Received responses to {len(extract_result.get('extracted_info', {}))} questions")
            logger.info(f"Response completeness: {extract_result.get('completeness', 0):.2%}")
            
            return updated_state
        
        except Exception as e:
            # Log error
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self.state_manager.log_stage_execution(
                session_id=session_id,
                stage_id=self.stage_id,
                stage_name=self.stage_name,
                status=StageStatus.FAILED,
                abilities_executed=abilities_executed,
                duration_ms=execution_time,
                error_message=str(e)
            )
            
            logger.error(f"{self.stage_name} failed: {str(e)}")
            raise

    async def _extract_answer(
        self, 
        state: AgentState, 
        customer_responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract and validate customer answers.
        Uses ATLAS server for intelligent answer processing.
        """
        
        logger.info("Extracting customer answers...")
        
        # Prepare context for the ability
        context = {
            "questions_asked": state.get("questions_asked", []),
            "customer_responses": customer_responses,
            "original_query": state["query"],
            "customer_name": state["customer_name"]
        }
        
        # Call ATLAS server
        response = await self.mcp_client.execute_ability(
            ability_name="extract_answer",
            parameters={},
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to extract customer answers: {response.error}")
        
        return response.data
    
    def _store_answer(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store customer answers in state format.
        This is internal state management, not an external server call.
        """
        
        logger.info("Storing customer answers...")
        
        return {
            "customer_responses": extracted_data,
            "waiting_for_response": False,
            "responses_received_at": datetime.now().isoformat(),
            "response_completeness": extracted_data.get("completeness", 1.0)
        }
    
    def is_waiting_for_response(self, session_id: str) -> bool:
        """
        Check if this stage is currently waiting for customer response.
        
        Returns:
            True if waiting, False if responses received or not needed
        """
        try:
            current_state = self.state_manager.get_current_state(session_id)
            return current_state.get("waiting_for_response", False)
        except:
            return False
        
    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Wait for and capture human response",
            "mode": "deterministic",
            "abilities": [
                {
                    "name": "extract_answer",
                    "server": "ATLAS",
                    "description": "Capture concise response"
                },
                {
                    "name": "store_answer",
                    "server": "state",
                    "description": "Update payload with response"
                }
            ],
            "execution_order": self.execution_order,
            "required_state": ["clarification_needed", "questions_asked"],
            "next_stage": "RETRIEVE"
        }