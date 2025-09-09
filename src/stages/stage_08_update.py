"""
Stage 08: UPDATE
Update ticket system

This stage updates the ticket system with the decision made in the DECIDE stage,
including status changes and resolution information.
It's a DETERMINISTIC stage - abilities execute in sequence.
"""

from typing import Dict, Any
from datetime import datetime
import logging
from ..agent.state_manager import AgentState, StateManager, StageStatus
from ..mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class UpdateStage:
    """
    Stage 08: UPDATE
    
    Responsibilities:
    - Update ticket status and fields based on decision
    - Close ticket if resolution is complete
    - Record resolution details and timing
    
    Mode: Deterministic (abilities execute in sequence)
    Abilities: update_ticket (ATLAS) -> close_ticket (ATLAS)
    """

    def __init__(self, state_manager: StateManager, mcp_client: MCPClient):
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.stage_id = 8
        self.stage_name = "UPDATE"

        # Define execution order for deterministic mode
        self.execution_order = ["update_ticket", "close_ticket"]

    async def execute(self, session_id: str) -> AgentState:
        """
        Execute the UPDATE stage in deterministic sequence.
        
        Args:
            session_id: Current session identifier
            
        Returns:
            Updated AgentState with ticket system changes
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting {self.stage_name} stage (deterministic)")

            # Get current state
            current_state = self.state_manager.get_current_state(session_id)

            # Validate that we have decision information
            if not current_state.get("escalation_decision") and not current_state.get("selected_solution"):
                raise Exception("Missing decision information from DECIDE stage")

            # Execute abilities in predetermined order
            abilities_executed = []
            results = {}

            # Step 1: Update ticket (ATLAS server)
            update_result = await self._update_ticket(current_state)
            abilities_executed.append("update_ticket")
            results["ticket_updates"] = update_result

            logger.info("Ticket updated successfully")

            # Step 2: Close ticket if appropriate (ATLAS server)
            close_result = None
            if self._should_close_ticket(current_state):
                close_result = await self._close_ticket(current_state)
                abilities_executed.append("close_ticket")
                results["ticket_status"] = "closed"
                logger.info("Ticket closed successfully")
            else:
                results["ticket_status"] = update_result.get("new_status", "in_progress")
                logger.info(f"Ticket status updated to: {results['ticket_status']}")

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
            
            logger.info(f"{self.stage_name} completed successfully")
            logger.info(f"Final ticket status: {results['ticket_status']}")
            
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

    async def _update_ticket(self, state: AgentState) -> Dict[str, Any]:
        """
        Update ticket in the system.
        Uses ATLAS server for external system interaction.
        """
        
        logger.info("Updating ticket...")
        
        # Prepare context for the ability
        context = {
            "ticket_id": state["ticket_id"],
            "customer_name": state["customer_name"],
            "escalation_decision": state.get("escalation_decision"),
            "selected_solution": state.get("selected_solution"),
            "decision_reasoning": state.get("decision_reasoning"),
            "solution_scores": state.get("solution_scores"),
            "enriched_records": state.get("enriched_records"),
            "calculated_flags": state.get("calculated_flags")
        }
        
        # Determine new status and priority based on decision
        parameters = self._prepare_update_parameters(state)
        
        # Call ATLAS server
        response = await self.mcp_client.execute_ability(
            ability_name="update_ticket",
            parameters=parameters,
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to update ticket: {response.error}")
        
        return response.data

    async def _close_ticket(self, state: AgentState) -> Dict[str, Any]:
        """
        Close the ticket if resolution is complete.
        Uses ATLAS server for external system interaction.
        """
        
        logger.info("Closing ticket...")
        
        # Prepare context for the ability
        context = {
            "ticket_id": state["ticket_id"],
            "customer_name": state["customer_name"],
            "selected_solution": state.get("selected_solution"),
            "resolution_summary": self._generate_resolution_summary(state)
        }
        
        # Prepare closure parameters
        parameters = {
            "resolution_code": self._determine_resolution_code(state),
            "customer_satisfaction_survey": True,
            "follow_up_required": False
        }
        
        # Call ATLAS server
        response = await self.mcp_client.execute_ability(
            ability_name="close_ticket",
            parameters=parameters,
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to close ticket: {response.error}")
        
        return response.data

    def _should_close_ticket(self, state: AgentState) -> bool:
        """
        Determine if the ticket should be closed based on current state.
        
        Returns:
            True if ticket should be closed, False if it should remain open
        """
        
        # Don't close if escalated
        if state.get("escalation_decision", False):
            return False
        
        # Close if we have a selected solution with high confidence
        selected_solution = state.get("selected_solution")
        if selected_solution:
            solution_scores = state.get("solution_scores", {})
            solution_id = selected_solution.get("id")
            if solution_id and solution_scores.get(solution_id, {}).get("overall_score", 0) >= 85:
                return True
        
        return False

    def _prepare_update_parameters(self, state: AgentState) -> Dict[str, Any]:
        """
        Prepare parameters for ticket update based on current state.
        """
        
        parameters = {
            "fields_to_update": []
        }
        
        # Determine new status
        if state.get("escalation_decision", False):
            parameters["new_status"] = "escalated"
            parameters["assigned_agent"] = "human_agent"
            parameters["priority"] = "high"
            parameters["fields_to_update"].extend(["new_status", "assigned_agent", "priority"])
        else:
            parameters["new_status"] = "in_progress"
            parameters["fields_to_update"].append("new_status")
        
        # Add resolution information if available
        selected_solution = state.get("selected_solution")
        if selected_solution:
            parameters["resolution_approach"] = selected_solution.get("title")
            parameters["estimated_resolution_time"] = selected_solution.get("estimated_resolution_time")
            parameters["fields_to_update"].extend(["resolution_approach", "estimated_resolution_time"])
        
        # Update SLA information
        calculated_flags = state.get("calculated_flags", {})
        if "sla_targets" in calculated_flags:
            parameters["sla_target"] = calculated_flags["sla_targets"]["resolution"]
            parameters["fields_to_update"].append("sla_target")
        
        return parameters

    def _determine_resolution_code(self, state: AgentState) -> str:
        """
        Determine the appropriate resolution code based on the solution.
        """
        
        selected_solution = state.get("selected_solution", {})
        solution_title = selected_solution.get("title", "").lower()
        
        if "billing" in solution_title or "payment" in solution_title:
            return "resolved_billing_issue"
        elif "account" in solution_title or "login" in solution_title:
            return "resolved_account_issue"
        elif "technical" in solution_title or "bug" in solution_title:
            return "resolved_technical_issue"
        else:
            return "resolved_general_inquiry"

    def _generate_resolution_summary(self, state: AgentState) -> str:
        """
        Generate a summary of the resolution for record keeping.
        """
        
        selected_solution = state.get("selected_solution", {})
        customer_name = state.get("customer_name", "Customer")
        
        summary = f"Issue resolved for {customer_name} using solution: {selected_solution.get('title', 'Standard Resolution')}. "
        
        if "steps" in selected_solution:
            summary += f"Resolution involved {len(selected_solution['steps'])} steps. "
        
        decision_reasoning = state.get("decision_reasoning")
        if decision_reasoning:
            summary += f"Decision rationale: {decision_reasoning}"
        
        return summary

    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Update ticket system",
            "mode": "deterministic",
            "abilities": [
                {
                    "name": "update_ticket",
                    "server": "ATLAS",
                    "description": "Modify status, fields, priority"
                },
                {
                    "name": "close_ticket",
                    "server": "ATLAS",
                    "description": "Mark issue resolved"
                }
            ],
            "execution_order": self.execution_order,
            "required_state": ["escalation_decision", "selected_solution"],
            "next_stage": "CREATE"
        }