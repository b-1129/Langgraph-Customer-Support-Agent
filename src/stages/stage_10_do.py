"""
Stage 10: DO
Execute actions and notifications

This stage executes the actual actions needed to resolve the customer issue
and sends notifications to inform the customer.
It's a DETERMINISTIC stage - abilities execute in sequence.
"""

from typing import Dict, Any
from datetime import datetime
import logging
from agent.state_manager import AgentState, StateManager, StageStatus
from mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

class DoStage:
    """
    Stage 10: DO
    
    Responsibilities:
    - Execute API calls to external systems (CRM, billing, etc.)
    - Send notifications to customer (email, SMS, etc.)
    - Perform any required system actions
    
    Mode: Deterministic (abilities execute in sequence)
    Abilities: execute_api_calls (ATLAS) -> trigger_notifications (ATLAS)
    """

    def __init__(self, state_manager: StateManager, mcp_client: MCPClient):
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.stage_id = 10
        self.stage_name = "DO"

        # Define execution order for deterministic mode
        self.execution_order = ["execute_api_calls", "trigger_notifications"]

    async def execute(self, session_id: str) -> AgentState:
        """
        Execute the DO stage in deterministic sequence.
        
        Args:
            session_id: Current session identifier
            
        Returns:
            Updated AgentState with execution results
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting {self.stage_name} stage (deterministic)")

            # Get current state
            current_state = self.state_manager.get_current_state(session_id)

            # Validate that we have necessary information
            if not current_state.get("generated_response") and not current_state.get("selected_solution"):
                raise Exception("Missing response or solution information from previous stages")

            # Execute abilities in predetermined order
            abilities_executed = []
            results = {}

            # Step 1: Execute API calls (ATLAS server)
            api_result = await self._execute_api_calls(current_state)
            abilities_executed.append("execute_api_calls")
            results["api_calls_executed"] = api_result.get("api_calls_executed", [])

            logger.info(f"API calls executed successfully: {len(results['api_calls_executed'])} calls")

            # Step 2: Trigger notifications (ATLAS server)
            notification_result = await self._trigger_notifications(current_state)
            abilities_executed.append("trigger_notifications")
            results["notifications_sent"] = notification_result.get("notifications_sent", [])

            logger.info(f"Notifications sent successfully: {len(results['notifications_sent'])} notifications")

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
                server_used="ATLAS,ATLAS",
                duration_ms=execution_time,
                output=results
            )
            
            logger.info(f"{self.stage_name} completed successfully")
            
            # Log execution summary
            api_calls = results.get("api_calls_executed", [])
            notifications = results.get("notifications_sent", [])
            
            successful_apis = sum(1 for call in api_calls if call.get("success", False))
            successful_notifications = sum(1 for notif in notifications if notif.get("sent", False))
            
            logger.info(f"Successful API calls: {successful_apis}/{len(api_calls)}")
            logger.info(f"Successful notifications: {successful_notifications}/{len(notifications)}")
            
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

    async def _execute_api_calls(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute API calls to external systems.
        Uses ATLAS server for external system integration.
        """
        
        logger.info("Executing API calls...")
        
        # Prepare context for the ability
        context = {
            "customer_name": state["customer_name"],
            "email": state["email"],
            "ticket_id": state["ticket_id"],
            "selected_solution": state.get("selected_solution"),
            "customer_responses": state.get("customer_responses"),
            "enriched_records": state.get("enriched_records"),
            "api_actions": self._determine_required_api_calls(state)
        }
        
        # Prepare parameters for API execution
        parameters = {
            "timeout_seconds": 30,
            "retry_attempts": 3,
            "parallel_execution": True
        }
        
        # Call ATLAS server
        response = await self.mcp_client.execute_ability(
            ability_name="execute_api_calls",
            parameters=parameters,
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to execute API calls: {response.error}")
        
        return response.data

    async def _trigger_notifications(self, state: AgentState) -> Dict[str, Any]:
        """
        Send notifications to customer and relevant parties.
        Uses ATLAS server for external notification services.
        """
        
        logger.info("Triggering notifications...")
        
        # Prepare context for the ability
        context = {
            "customer_name": state["customer_name"],
            "email": state["email"],
            "ticket_id": state["ticket_id"],
            "generated_response": state.get("generated_response"),
            "ticket_status": state.get("ticket_status"),
            "escalation_decision": state.get("escalation_decision"),
            "notification_preferences": self._get_notification_preferences(state)
        }
        
        # Prepare notification parameters
        parameters = {
            "send_email": True,
            "send_sms": False,  # Only if customer prefers SMS
            "send_push": False,
            "include_survey": state.get("ticket_status") == "closed",
            "priority": self._determine_notification_priority(state)
        }
        
        # Call ATLAS server
        response = await self.mcp_client.execute_ability(
            ability_name="trigger_notifications",
            parameters=parameters,
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to trigger notifications: {response.error}")
        
        return response.data

    def _determine_required_api_calls(self, state: AgentState) -> list[Dict[str, Any]]:
        """
        Determine what API calls are needed based on the solution and customer data.
        """
        
        api_actions = []
        selected_solution = state.get("selected_solution", {})
        solution_title = selected_solution.get("title", "").lower()
        
        # Billing-related API calls
        if "billing" in solution_title or "payment" in solution_title:
            api_actions.extend([
                {
                    "system": "billing_system",
                    "action": "update_payment_method",
                    "endpoint": "/billing/update_payment",
                    "data": {
                        "customer_id": state.get("enriched_records", {}).get("account_id"),
                        "ticket_id": state["ticket_id"]
                    }
                },
                {
                    "system": "crm_system",
                    "action": "update_customer_record",
                    "endpoint": "/crm/customer/update",
                    "data": {
                        "customer_email": state["email"],
                        "last_interaction": datetime.now().isoformat(),
                        "interaction_type": "billing_resolution"
                    }
                }
            ])
        
        # Account-related API calls
        elif "account" in solution_title or "login" in solution_title:
            api_actions.extend([
                {
                    "system": "auth_system",
                    "action": "reset_account_flags",
                    "endpoint": "/auth/account/reset_flags",
                    "data": {
                        "email": state["email"],
                        "ticket_id": state["ticket_id"]
                    }
                },
                {
                    "system": "crm_system",
                    "action": "update_customer_record",
                    "endpoint": "/crm/customer/update",
                    "data": {
                        "customer_email": state["email"],
                        "last_interaction": datetime.now().isoformat(),
                        "interaction_type": "account_resolution"
                    }
                }
            ])
        
        # Technical issue API calls
        elif "technical" in solution_title or "bug" in solution_title:
            api_actions.extend([
                {
                    "system": "support_system",
                    "action": "create_bug_report",
                    "endpoint": "/support/bugs/create",
                    "data": {
                        "customer_email": state["email"],
                        "issue_description": state["query"],
                        "ticket_id": state["ticket_id"]
                    }
                }
            ])
        
        # Always update CRM with interaction
        api_actions.append({
            "system": "crm_system",
            "action": "log_interaction",
            "endpoint": "/crm/interactions/log",
            "data": {
                "customer_email": state["email"],
                "ticket_id": state["ticket_id"],
                "interaction_type": "automated_resolution",
                "resolution": selected_solution.get("title", "Standard Resolution"),
                "timestamp": datetime.now().isoformat()
            }
        })
        
        return api_actions

    def _get_notification_preferences(self, state: AgentState) -> Dict[str, Any]:
        """
        Get customer notification preferences from enriched records.
        """
        
        enriched_records = state.get("enriched_records", {})
        
        # Default preferences
        preferences = {
            "email": True,
            "sms": False,
            "push": False,
            "language": "en",
            "timezone": "UTC"
        }
        
        # Override with customer preferences if available
        customer_prefs = enriched_records.get("notification_preferences", {})
        preferences.update(customer_prefs)
        
        return preferences

    def _determine_notification_priority(self, state: AgentState) -> str:
        """
        Determine notification priority based on ticket status and customer tier.
        """
        
        # High priority for escalated tickets
        if state.get("escalation_decision", False):
            return "high"
        
        # High priority for premium customers
        enriched_records = state.get("enriched_records", {})
        if enriched_records.get("customer_tier") == "premium":
            return "high"
        
        # Medium priority for urgent tickets
        if state.get("priority") == "urgent":
            return "medium"
        
        return "normal"

    def get_execution_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of what was executed in this stage.
        
        Returns:
            Summary of API calls and notifications
        """
        try:
            current_state = self.state_manager.get_current_state(session_id)
            
            api_calls = current_state.get("api_calls_executed", [])
            notifications = current_state.get("notifications_sent", [])
            
            return {
                "total_api_calls": len(api_calls),
                "successful_api_calls": sum(1 for call in api_calls if call.get("success", False)),
                "failed_api_calls": sum(1 for call in api_calls if not call.get("success", True)),
                "total_notifications": len(notifications),
                "successful_notifications": sum(1 for notif in notifications if notif.get("sent", False)),
                "failed_notifications": sum(1 for notif in notifications if not notif.get("sent", True)),
                "systems_contacted": list(set(call.get("system", "unknown") for call in api_calls))
            }
        except:
            return {"error": "Execution summary not available"}

    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Execute actions and notifications",
            "mode": "deterministic",
            "abilities": [
                {
                    "name": "execute_api_calls",
                    "server": "ATLAS",
                    "description": "Trigger CRM/order system actions"
                },
                {
                    "name": "trigger_notifications",
                    "server": "ATLAS",
                    "description": "Notify customer"
                }
            ],
            "execution_order": self.execution_order,
            "required_state": ["generated_response", "selected_solution"],
            "next_stage": "COMPLETE"
        }