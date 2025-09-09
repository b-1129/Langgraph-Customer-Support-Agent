"""
Stage 03: PREPARE
Normalize and enrich data

This stage prepares the data for further processing by normalizing fields,
enriching with additional information, and calculating flags.
It's a DETERMINISTIC stage - abilities executes in a fixed sequence.
"""
from typing import Dict, Any
from datetime import datetime
import logging
from ..agent.state_manager import AgentState, StateManager, StageStatus
from ..mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class PrepareStage:
    """
    Stage 03: PREPARE
    
    Responsibilities:
    - Normalize data fields (dates, codes, IDs)
    - Enrich records with SLA and historical info
    - Calculate priority and risk flags
    
    Mode: Deterministic (abilities execute in sequence)
    Abilities: normalize_fields (COMMON) -> enrich_records (ATLAS) -> and flags_calculations (COMMON)
    """

    def __init__(self, state_manager: StateManager, mcp_client: MCPClient):
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.stage_id = 3
        self.stage_name = "PREPARE"

        # Define execution order for deterministic mode
        self.execution_order = ["normalize_fields", "enrich_records", "add_flags_calculations"]

    async def execute(self, session_id:str) -> AgentState:
        """
        Execute the PREPARE stage in the deterministic sequence.
        
        Args:
            session_id: Current session identifier
            
        Returns:
            Updated agent state with prepared data
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting {self.stage_name} stage (deterministic)")

            # Get current state
            current_state = self.state_manager.get_current_state(session_id)

            # Validate that previous stages completed
            if not current_state.get("parsed_request") or not current_state.get("extracted_entities"):
                raise Exception("Missing required data from UNDERSTAND stage")
            
            # Execute abilities in predetermined order
            abilities_executed = []
            results = {}

            # Step 1: Normalize fields (COMMON server)
            normalize_result = await self._normalize_fields(current_state)
            abilities_executed.append("normalize_fields")
            results["normalize_fields"] = normalize_result

            logger.info("Fields normalized successfully")

            # Step 2: Enrich records (ATLAS server)
            enrich_result = await self._enrich_records(current_state, normalize_result)
            abilities_executed.append("enrich_records")
            results["enrich_records"] = enrich_result

            logger.info("Records enrich successfully")

            # Step 3: Add flags and calculations (COMMON server)
            flags_result = await self._add_flags_calculations(current_state, enrich_result)
            abilities_executed.append("add_flags_calculations")
            results["calculated_flags"] = flags_result

            logger.info("Flags and calculations completed successfully")

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
                server_used="COMMON, ATLAS, COMMON",
                duration_ms=execution_time,
                output=results 
            )

            logger.info(f"{self.stage_name} completed successfully")
            logger.info(f"Customer tier: {enrich_result.get('customer_tier', 'unknown')}")
            logger.info(f"SLA risk score: {flags_result.get('calculated_flags', {}).get('sla_risk_score', 'N/A')}")

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

    async def _normalize_fields(self, state:AgentState) -> Dict[str, Any]:
        """
        Normalize data fields to standard formats.
        Uses COMMON server for internal data processing.
        """
        logger.info("Normalizing fields...")

        # Prepare context for the ability
        context = {
            "customer_name": state["customer_name"],
            "email": state["email"],
            "priority": state["priority"],
            "ticket_id": state["ticket_id"],
            "parsed_request": state.get("parsed_request"),
            "extracted_entities": state.get("extracted_entities")
        }

        # Call COMMON server
        response = await self.mcp_client.execute_ability(
            ability_name="normalize_fields",
            parameters={},
            context=context,
            session_id=state["session_id"]
        )

        if not response.success:
            raise Exception(f"failed to normalize fields: {response.error}")
        
        return response.data
    
    async def _enrich_records(
            self,
            state:AgentState,
            normalized_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich records with SLA and historical information.
        Uses ATLAS server for external data lookup.
        """
        logger.info("Enriching records...")

        # Prepare context for the ability
        context = {
            "customer_name": state["customer_name"],
            "email": state["email"],
            "normalized_fields": normalized_data,
            "extracted_entities": state.get["extracted_entities"],
            "ticket_id": state["ticket_id"]
        }

        # Call ATLAS server
        response = await self.mcp_client.execute_ability(
            ability_name="enrich_records",
            parameters={},
            context=context,
            session_id=state["session_id"]
        )

        if not response.success:
            raise Exception(f"failed to enrich records: {response.error}")
        
        return response.data
    
    async def _add_flags_calculations(
            self,
            state:AgentState,
            enriched_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate priority flags and scores.
        Uses COMMON server for internal calculations.
        """

        logger.info("Adding flags and calculations...")

        # Prepare context for the ability
        context = {
            "customer_name": state["customer_name"],
            "priority": state["priority"],
            "enriched_records": enriched_data,
            "parsed_request": state.get("parsed_request"),
            "extracted_entities": state.get("extracted_entities")
        }

        # Call COMMON server
        response = await self.mcp_client.execute_ability(
            ability_name="add_flags_calculations",
            parameters={},
            context=context,
            session_id=state["session_id"]
        )

        if not response.success:
            raise Exception(f"Failed to add flags and calculations: {response.error}")
        
        return response.data
    
    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Normalize and enrich data",
            "mode": "deterministic",
            "abilities": [
                {
                    "name": "normalize_fields",
                    "server": "COMMON",
                    "description": "Standardize dates, codes, IDs"
                },
                {
                    "name": "enrich_records",
                    "server": "ATLAS", 
                    "description": "Add SLA, historical ticket info"
                },
                {
                    "name": "add_flags_calculations",
                    "server": "COMMON",
                    "description": "Compute priority, SLA risk"
                }
            ],
            "execution_order": self.execution_order,
            "required_state": ["parsed_request", "extracted_entities"],
            "next_stage": "ASK"
        }

