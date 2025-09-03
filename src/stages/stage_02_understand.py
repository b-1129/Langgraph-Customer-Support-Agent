"""
Stage 2: UNDERSTAND
Parse request text and extract entities

This stage analyzes the customer's query to understand what they need.
It's a DETERMINISTIC stage - abilities execute in a fixed sequence.
"""

from typing import Dict, Any
from datetime import datetime
import logging
from agent.state_manager import AgentState, StateManager, StageStatus
from mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class UnderstandStage:
    """
    Stage 2: UNDERSTAND
    
    Responsibilities:
    - Parse unstructured customer query into structured data
    - Extract entities (products, accounts, dates, etc.)
    - Identify intent and sentiment
    
    Mode: Deterministic (abilities execute in sequence)
    Abilities: parse_request_text (COMMON) -> extract_entities (ATLAS)
    """

    def __init__(self, state_manager: StateManager, mcp_client: MCPClient):
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.stage_id = 2
        self.stage_name = "UNDERSTAND"

        # Define execution order for deterministic mode
        self.execution_order = ["parse_request_text", "extract_entities"]

    async def execute(self, session_id: str) -> AgentState:
        """
        Execute the UNDERSTAND stage in deterministic sequence.
        
        Args:
            session_id: Current session identifier
            
        Returns:
            Updated AgentState with understanding results
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting {self.stage_name} stage (deterministic)")

            # Get current state
            current_state = self.state_manager.get_current_state(session_id)

            # Execute abilities in predetermined order
            abilities_executed = []
            results = {}

            # Step 1: Parse request text (COMMON server)
            parse_result = await self._parse_request_text(current_state)
            abilities_executed.append("parse_request_text")
            results["parsed_request"] = parse_result

            logger.info("Request text parsed successfully")

            # Step 2: Extract entities (ATLAS server)
            entities_result = await self._extract_entities(current_state, parse_result)
            abilities_executed.append("extract_entities")
            results["extracted_entities"] = entities_result

            logger.info("Entities extracted successfully")

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
                server_used="COMMON,ATLAS",
                duration_ms=execution_time,
                output=results
            )
            
            logger.info(f"{self.stage_name} completed successfully")
            logger.info(f"Identified intent: {parse_result.get('structured_request', {}).get('intent', 'unknown')}")
            logger.info(f"Extracted entities: {list(entities_result.get('entities', {}).keys())}")
            
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
            
    async def _parse_request_text(self, state: AgentState) -> Dict[str, Any]:
        """
        Parse unstructured customer query into structured format.
        Uses COMMON server for internal text processing.
        """
        
        logger.info("Parsing request text...")
        
        # Prepare context for the ability
        context = {
            "query": state["query"],
            "customer_name": state["customer_name"],
            "priority": state["priority"]
        }
        
        # Call COMMON server
        response = await self.mcp_client.execute_ability(
            ability_name="parse_request_text",
            parameters={},
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to parse request text: {response.error}")
        
        return response.data
    
    async def _extract_entities(
        self, 
        state: AgentState, 
        parsed_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract entities from the parsed request.
        Uses ATLAS server for external NLP/entity extraction.
        """
        
        logger.info("Extracting entities...")
        
        # Prepare context for the ability
        context = {
            "query": state["query"],
            "parsed_request": parsed_request,
            "customer_name": state["customer_name"],
            "email": state["email"]
        }
        
        # Call ATLAS server
        response = await self.mcp_client.execute_ability(
            ability_name="extract_entities",
            parameters={},
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to extract entities: {response.error}")
        
        return response.data
    
    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Parse request text and extract entities",
            "mode": "deterministic",
            "abilities": [
                {
                    "name": "parse_request_text",
                    "server": "COMMON",
                    "description": "Convert unstructured request to structured data"
                },
                {
                    "name": "extract_entities", 
                    "server": "ATLAS",
                    "description": "Identify product, account, dates"
                }
            ],
            "execution_order": self.execution_order,
            "required_state": ["query", "customer_name"],
            "next_stage": "PREPARE"
        }

