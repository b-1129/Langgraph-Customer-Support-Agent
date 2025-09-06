"""
Stage 06: RETRIEVE
Search knowledge base for relevant solutions

This stage searches the knowledge base to find relevant solutions
and information to help resolve the customer's issue.
It's a DETERMINISTIC stage - abilities execute in sequence.
"""

from typing import Dict, Any
from datetime import datetime
import logging
from agent.state_manager import AgentState, StateManager, StageStatus
from mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class RetrieveStage:
    """
    Stage 06: RETRIEVE
    
    Responsibilities:
    - Search knowledge base and FAQ for relevant solutions
    - Filter and rank solutions by relevance
    - Store retrieved information for decision making
    
    Mode: Deterministic (abilities execute in sequence)
    Abilities: knowledge_base_search (ATLAS) -> store_data (state management)
    """

    def __init__(self, state_manager: StateManager, mcp_client: MCPClient):
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.stage_id = 6
        self.stage_name = "RETRIEVE"

        # Define execution order for deterministic mode
        self.execution_order = ["knowledge_base_search", "store_data"]

    async def execute(self, session_id: str) -> AgentState:
        """
        Execute the RETRIEVE stage in deterministic sequence.
        
        Args:
            session_id: Current session identifier
            
        Returns:
            Updated AgentState with retrieved solutions
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting {self.stage_name} stage (deterministic)")

            # Get current state
            current_state = self.state_manager.get_current_state(session_id)

            # Validate that we have necessary information to search
            if not current_state.get("parsed_request"):
                raise Exception("Missing parsed request data for knowledge base search")

            # Execute abilities in predetermined order
            abilities_executed = []
            results = {}

            # Step 1: Search knowledge base (ATLAS server)
            search_result = await self._search_knowledge_base(current_state)
            abilities_executed.append("knowledge_base_search")

            logger.info(f"Knowledge base search completed - found {len(search_result.get('solutions_found', []))} solutions")

            # Step 2: Store retrieved data (state management)
            store_result = self._store_retrieved_data(search_result)
            abilities_executed.append("store_data")
            results.update(store_result)

            logger.info("Retrieved data stored successfully")

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

            # Log solution summary
            solutions = results.get("retrieved_solutions", [])
            if solutions:
                logger.info(f"Top solution: {solutions[0].get('title', 'Unknown')} (relevance: {solutions[0].get('relevance_score', 0):.2f})")
                logger.info(f"Total solutions retrieved: {len(solutions)}")
            else:
                logger.warning("No solutions found in knowledge base")
            
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

    async def _search_knowledge_base(self, state: AgentState) -> Dict[str, Any]:
        """
        Search knowledge base for relevant solutions.
        Uses ATLAS server for external knowledge base access.
        """
        
        logger.info("Searching knowledge base...")
        
        # Prepare search context with all available information
        context = {
            "query": state["query"],
            "customer_name": state["customer_name"],
            "parsed_request": state.get("parsed_request"),
            "extracted_entities": state.get("extracted_entities"),
            "customer_responses": state.get("customer_responses"),
            "enriched_records": state.get("enriched_records"),
            "calculated_flags": state.get("calculated_flags")
        }
        
        # Add search parameters for better results
        parameters = {
            "max_results": 10,
            "min_relevance_score": 0.3,
            "include_related": True,
            "search_categories": self._determine_search_categories(state)
        }
        
        # Call ATLAS server
        response = await self.mcp_client.execute_ability(
            ability_name="knowledge_base_search",
            parameters=parameters,
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to search knowledge base: {response.error}")
        
        return response.data
    
    def _determine_search_categories(self, state: AgentState) -> list[str]:
        """
        Determine appropriate search categories based on parsed request.
        """
        categories = ["general"]
        
        parsed_request = state.get("parsed_request", {})
        structured_req = parsed_request.get("structured_request", {})
        
        if "category" in structured_req:
            categories.append(structured_req["category"].lower())
        
        if "sub_category" in structured_req:
            categories.append(structured_req["sub_category"].lower())
        
        # Add categories based on entities
        entities = state.get("extracted_entities", {}).get("entities", {})
        if "issue_type" in entities:
            categories.append(entities["issue_type"].lower())
        
        return list(set(categories))  # Remove duplicates
    
    def _store_retrieved_data(self, search_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store retrieved knowledge base data in state format.
        This is internal state management, not an external server call.
        """
        
        logger.info("Storing retrieved data...")
        
        solutions = search_result.get("solutions_found", [])
        
        # Sort solutions by relevance score
        sorted_solutions = sorted(
            solutions, 
            key=lambda x: x.get("relevance_score", 0), 
            reverse=True
        )
        
        return {
            "knowledge_base_results": search_result,
            "retrieved_solutions": sorted_solutions,
            "search_metadata": {
                "total_results": search_result.get("total_results", len(solutions)),
                "search_timestamp": datetime.now().isoformat(),
                "has_high_confidence_solution": any(
                    sol.get("relevance_score", 0) > 0.8 for sol in solutions
                )
            }
        }
    
    def get_best_solutions(self, session_id: str, limit: int = 3) -> list[Dict[str, Any]]:
        """
        Get the top N solutions for this session.
        
        Args:
            session_id: Current session identifier
            limit: Maximum number of solutions to return
            
        Returns:
            List of top solutions
        """
        try:
            current_state = self.state_manager.get_current_state(session_id)
            solutions = current_state.get("retrieved_solutions", [])
            return solutions[:limit]
        except:
            return []

    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Search knowledge base for relevant solutions",
            "mode": "deterministic",
            "abilities": [
                {
                    "name": "knowledge_base_search",
                    "server": "ATLAS",
                    "description": "Look up KB or FAQ"
                },
                {
                    "name": "store_data",
                    "server": "state",
                    "description": "Attach retrieved info to payload"
                }
            ],
            "execution_order": self.execution_order,
            "required_state": ["parsed_request"],
            "next_stage": "DECIDE"
        }