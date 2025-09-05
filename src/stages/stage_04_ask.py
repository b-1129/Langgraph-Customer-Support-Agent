"""
Stage 04: ASK
Request missing information from human

This stage handles human-in-the-loop interactions when additional
information is needed from the customer.
It's a HUMAN interactions stage - pauses for human input.
"""

from typing import Dict, Any
from datetime import datetime
import logging
from agent.state_manager import AgentState, StateManager, StageStatus
from mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class AskStage:
    """
    Stage 04: ASK
    
    Responsibilities:
    - Identify missing information needed to resolve the issue
    - Generate clarifying questions for the customer
    - Determine if human interaction is required

    Mode: Human-in-the-loop (requires human input)
    Abilities: clarify_question (ATLAS)
    """

    def __init__(self, state_manager:StateManager, mcp_client:MCPClient):
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.stage_id = 4
        self.stage_name = "ASK"

    async def execute(self, session_id:str) -> AgentState:
        """
        Execute the ASK stage.
        
        Args:
            session_id: Current session identifier
            
        Returns:
            Updated AgentState with clarification questions or skip marker
        """

        start_time = datetime.now()

        try:
            logger.info(f"Starting {self.stage_name} stage (human-in-loop)")

            # Get current state
            current_state = self.state_manager.get_current_state(session_id)

            # Validate that previous stages completed
            required_fields = ["parsed_request", "extracted_entities", "calculated_flags"]
            for field in required_fields:
                if not current_state.get(field):
                    raise Exception(f"Missing required data from previous stages: {field}")
                
            # Check if clarification is needed
            clarification_result = await self._assess_clarification_needs(current_state)

            abilities_executed = ["clarify_question"]
            results = {
                "clarification_needed": clarification_result.get("questions_needed", False),
                "questions_asked": clarification_result.get("questions", [])
            }

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
                server_used="ATLAS",
                duration_ms=execution_time,
                output=results
            )

            if results["clarification_needed"]:
                logger.info(f"{self.stage_name} completed - Questions generated for customer")
                logger.info(f"Question to ask: {len(results['questions_asked'])}")
                for i, question in enumerate(results["questions_asked"], 1):
                    logger.info(f" Q{i}: {question}")
            else:
                logger.info(f"{self.stage_name} completed - No clarification needed")

            return updated_state
        
        except Exception as e:
            # Log error
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            self.state_manager.log_stage_execution(
                session_id=session_id,
                stage_id=self.stage_id,
                stage_name=self.stage_name,
                status=StageStatus.FAILED,
                abilities_executed=["clarify_question"],
                duration_ms=execution_time,
                error_message=str(e)
            )
            logger.error(f"{self.stage_name} failed: {str(e)}")
            raise

    async def _assess_clarification_needs(self, state:AgentState) -> Dict[str, Any]:
        """
        Assess if clarification is needed and generate questions.
        Uses ATLAS server for intelligent question generation.
        """

        logger.info("Assessing clarification needs...")

        # Prepare context for the ability
        context = {
            "customer_name": state["customer_name"],
            "email": state["email"],
            "query": state["query"],
            "parsed_request": state.get("parsed_request"),
            "extracted_entities": state.get("extracted_entities"),
            "enriched_records": state.get("enriched_records"),
            "calculated_flags": state.get("calculated_flags")
        }

        # Call ATLAS server to generate clarifying questions
        response = await self.mcp_client.execute_ability(
            ability_name="clarify_question",
            parameters={},
            context=context,
            session_id=state["session_id"]
        )

        if not response.success:
            raise Exception(f"Failed to assess clarification needs: {response.error}")
        
        return response.data
    
    def requires_human_input(self, session_id: str) -> bool:
        """
        Check if this stage requires human input based on current state.
        
        Returns:
            True if human input is needed, False to skip to next stage
        """
        try:
            current_state = self.state_manager.get_current_state(session_id)
            return current_state.get("clarification_needed", False)
        except:
            return False
        
    def get_questions_for_customer(self, session_id: str) -> list[str]:
        """
        Get the list of questions to present to the customer.
        
        Returns:
            List of questions to ask the customer
        """
        try:
            current_state = self.state_manager.get_current_state(session_id)
            return current_state.get("questions_asked", [])
        except:
            return []
        
    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Request missing information from human",
            "mode": "human_in_the_loop",
            "abilities": [
                {
                    "name": "clarify_question",
                    "server": "ATLAS",
                    "description": "Request missing information"
                }
            ],
            "requires_human": True,
            "required_state": ["parsed_request", "extracted_entities", "calculated_flags"],
            "next_stage": "WAIT"
        }
    



