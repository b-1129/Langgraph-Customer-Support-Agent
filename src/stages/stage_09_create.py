"""
Stage 09: CREATE
Generate customer response

This stage creates a personalized response for the customer based on
the selected solution and resolution approach.
It's a DETERMINISTIC stage with a single ability.
"""

from typing import Dict, Any
from datetime import datetime
import logging
from agent.state_manager import AgentState, StateManager, StageStatus
from mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class CreateStage:
    """
    Stage 09: CREATE
    
    Responsibilities:
    - Generate personalized customer response
    - Include resolution steps and next actions
    - Ensure appropriate tone and completeness
    
    Mode: Deterministic (single ability)
    Abilities: response_generation (COMMON)
    """

    def __init__(self, state_manager: StateManager, mcp_client: MCPClient):
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.stage_id = 9
        self.stage_name = "CREATE"

    async def execute(self, session_id: str) -> AgentState:
        """
        Execute the CREATE stage.
        
        Args:
            session_id: Current session identifier
            
        Returns:
            Updated AgentState with generated response
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting {self.stage_name} stage (deterministic)")

            # Get current state
            current_state = self.state_manager.get_current_state(session_id)

            # Validate that we have necessary information
            if not current_state.get("ticket_updates") and not current_state.get("escalation_decision"):
                raise Exception("Missing ticket update information from UPDATE stage")

            # Generate customer response
            response_result = await self._generate_response(current_state)
            
            abilities_executed = ["response_generation"]
            results = {
                "generated_response": response_result.get("generated_response"),
                "response_metadata": response_result.get("response_metadata", {})
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
                server_used="COMMON",
                duration_ms=execution_time,
                output=results
            )
            
            logger.info(f"{self.stage_name} completed successfully")
            
            # Log response metadata
            metadata = results.get("response_metadata", {})
            logger.info(f"Response tone: {metadata.get('tone', 'standard')}")
            logger.info(f"Response length: {metadata.get('length', 'unknown')}")
            logger.info(f"Personalization score: {metadata.get('personalization_score', 0):.2f}")
            
            return updated_state
        
        except Exception as e:
            # Log error
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self.state_manager.log_stage_execution(
                session_id=session_id,
                stage_id=self.stage_id,
                stage_name=self.stage_name,
                status=StageStatus.FAILED,
                abilities_executed=["response_generation"],
                duration_ms=execution_time,
                error_message=str(e)
            )
            
            logger.error(f"{self.stage_name} failed: {str(e)}")
            raise

    async def _generate_response(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate personalized customer response.
        Uses COMMON server for internal response generation.
        """
        
        logger.info("Generating customer response...")
        
        # Prepare comprehensive context for response generation
        context = {
            "customer_name": state["customer_name"],
            "email": state["email"],
            "original_query": state["query"],
            "ticket_id": state["ticket_id"],
            "selected_solution": state.get("selected_solution"),
            "escalation_decision": state.get("escalation_decision"),
            "ticket_status": state.get("ticket_status"),
            "enriched_records": state.get("enriched_records"),
            "response_tone": self._determine_response_tone(state)
        }
        
        # Add response parameters
        parameters = {
            "include_next_steps": True,
            "include_contact_info": True,
            "personalization_level": "high",
            "max_length": 500,  # words
            "format": "email"
        }
        
        # Call COMMON server
        response = await self.mcp_client.execute_ability(
            ability_name="response_generation",
            parameters=parameters,
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to generate response: {response.error}")
        
        return response.data

    def _determine_response_tone(self, state: AgentState) -> str:
        """
        Determine appropriate tone based on customer situation and resolution.
        """
        
        # Check if escalated
        if state.get("escalation_decision", False):
            return "apologetic_professional"
        
        # Check customer sentiment from parsing
        parsed_request = state.get("parsed_request", {})
        sentiment = parsed_request.get("structured_request", {}).get("customer_sentiment", "").lower()
        
        if sentiment == "frustrated":
            return "empathetic_professional"
        elif sentiment == "angry":
            return "calming_professional"
        else:
            return "professional_friendly"

    def get_response_preview(self, session_id: str, max_chars: int = 200) -> str:
        """
        Get a preview of the generated response.
        
        Args:
            session_id: Current session identifier
            max_chars: Maximum characters to return
            
        Returns:
            Preview of the generated response
        """
        try:
            current_state = self.state_manager.get_current_state(session_id)
            response = current_state.get("generated_response", "")
            
            if len(response) <= max_chars:
                return response
            else:
                return response[:max_chars] + "..."
        except:
            return "Response not available"

    def get_response_quality_score(self, session_id: str) -> Dict[str, float]:
        """
        Get quality scores for the generated response.
        
        Returns:
            Dictionary with quality metrics
        """
        try:
            current_state = self.state_manager.get_current_state(session_id)
            metadata = current_state.get("response_metadata", {})
            
            return {
                "personalization_score": metadata.get("personalization_score", 0.0),
                "clarity_score": metadata.get("clarity_score", 0.0),
                "completeness_score": metadata.get("completeness_score", 0.0),
                "tone_appropriateness": metadata.get("tone_appropriateness", 0.0)
            }
        except:
            return {"error": "Quality scores not available"}

    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Generate customer response",
            "mode": "deterministic",
            "abilities": [
                {
                    "name": "response_generation",
                    "server": "COMMON",
                    "description": "Draft customer reply"
                }
            ],
            "required_state": ["ticket_updates", "customer_name"],
            "next_stage": "DO"
        }