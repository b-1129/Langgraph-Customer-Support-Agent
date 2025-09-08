"""
Stage 11: COMPLETE
Output final structured payload

This is the final stage that compiles all information from the workflow
into a comprehensive output payload for logging, monitoring, and handoff.
It's a PAYLOAD_ONLY stage - no external server calls.
"""

from typing import Dict, Any
from datetime import datetime
import logging
from agent.state_manager import AgentState, StateManager, StageStatus

logger = logging.getLogger(__name__)

class CompleteStage:
    """
    Stage 11: COMPLETE
    
    Responsibilities:
    - Compile final structured payload with all workflow results
    - Generate execution summary and metrics
    - Prepare data for external systems or reporting
    - Mark workflow as completed
    
    Mode: Payload only (no external server calls)
    Abilities: output_payload (internal processing)
    """

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.stage_id = 11
        self.stage_name = "COMPLETE"

    async def execute(self, session_id: str) -> AgentState:
        """
        Execute the COMPLETE stage.
        
        Args:
            session_id: Current session identifier
            
        Returns:
            Final AgentState with complete payload
        """
        start_time = datetime.now()

        try:
            logger.info(f"Starting {self.stage_name} stage (payload only)")

            # Get current state
            current_state = self.state_manager.get_current_state(session_id)

            # Generate final payload
            final_payload = self._generate_final_payload(current_state)
            
            abilities_executed = ["output_payload"]
            results = {
                "final_payload": final_payload,
                "workflow_completed": True,
                "completion_timestamp": datetime.now().isoformat()
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
                server_used=None,  # No external server used
                duration_ms=execution_time,
                output=results
            )
            
            logger.info(f"{self.stage_name} completed successfully")
            logger.info(f"Workflow completed for ticket: {current_state['ticket_id']}")
            
            # Log final metrics
            metrics = final_payload.get("workflow_metrics", {})
            logger.info(f"Total execution time: {metrics.get('total_execution_time_ms', 0)}ms")
            logger.info(f"Stages completed: {metrics.get('stages_completed', 0)}/11")
            logger.info(f"Final status: {final_payload.get('status', 'unknown')}")
            
            return updated_state
        
        except Exception as e:
            # Log error
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self.state_manager.log_stage_execution(
                session_id=session_id,
                stage_id=self.stage_id,
                stage_name=self.stage_name,
                status=StageStatus.FAILED,
                abilities_executed=["output_payload"],
                duration_ms=execution_time,
                error_message=str(e)
            )
            
            logger.error(f"{self.stage_name} failed: {str(e)}")
            raise

    def _generate_final_payload(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate the comprehensive final payload with all workflow results.
        """
        
        logger.info("Generating final payload...")
        
        # Calculate workflow metrics
        workflow_metrics = self._calculate_workflow_metrics(state)
        
        # Determine final status
        final_status = self._determine_final_status(state)
        
        # Build comprehensive payload
        final_payload = {
            # Basic Information
            "ticket_id": state["ticket_id"],
            "session_id": state["session_id"],
            "customer_name": state["customer_name"],
            "email": state["email"],
            "original_query": state["query"],
            "priority": state["priority"],
            
            # Workflow Results
            "status": final_status,
            "escalated": state.get("escalation_decision", False),
            "resolution": self._generate_resolution_summary(state),
            "response_generated": state.get("generated_response"),
            
            # Stage Outputs
            "understanding": {
                "parsed_request": state.get("parsed_request"),
                "extracted_entities": state.get("extracted_entities")
            },
            
            "preparation": {
                "normalized_fields": state.get("normalized_fields"),
                "enriched_records": state.get("enriched_records"),
                "calculated_flags": state.get("calculated_flags")
            },
            
            "interaction": {
                "clarification_needed": state.get("clarification_needed", False),
                "questions_asked": state.get("questions_asked", []),
                "customer_responses": state.get("customer_responses")
            },
            
            "knowledge_retrieval": {
                "solutions_found": len(state.get("retrieved_solutions", [])),
                "best_solution": self._get_best_solution_summary(state)
            },
            
            "decision": {
                "solution_scores": state.get("solution_scores"),
                "selected_solution": state.get("selected_solution"),
                "decision_reasoning": state.get("decision_reasoning"),
                "escalation_decision": state.get("escalation_decision")
            },
            
            "execution": {
                "ticket_status": state.get("ticket_status"),
                "api_calls_executed": len(state.get("api_calls_executed", [])),
                "notifications_sent": len(state.get("notifications_sent", [])),
                "actions_successful": self._count_successful_actions(state)
            },
            
            # Metadata and Metrics
            "workflow_metrics": workflow_metrics,
            "execution_log": [log.dict() for log in state.get("execution_log", [])],
            "errors": state.get("errors", []),
            "created_at": state.get("created_at"),
            "completed_at": datetime.now(),
            
            # Quality Metrics
            "quality_scores": self._calculate_quality_scores(state),
            
            # Compliance and Audit
            "compliance_info": {
                "data_processed": True,
                "customer_consent": True,  # Assumed for demo
                "retention_period": "7 years",
                "processing_lawful_basis": "legitimate_interest"
            }
        }
        
        return final_payload

    def _calculate_workflow_metrics(self, state: AgentState) -> Dict[str, Any]:
        """Calculate comprehensive workflow execution metrics."""
        
        execution_log = state.get("execution_log", [])
        
        # Time calculations
        start_time = state.get("created_at")
        end_time = datetime.now()
        total_time_ms = 0
        
        if start_time:
            total_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Stage completion analysis
        completed_stages = [log for log in execution_log if log.status == StageStatus.COMPLETED]
        failed_stages = [log for log in execution_log if log.status == StageStatus.FAILED]
        
        # Server usage analysis
        server_usage = {}
        for log in execution_log:
            if log.server_used:
                for server in log.server_used.split(','):
                    server = server.strip()
                    server_usage[server] = server_usage.get(server, 0) + 1
        
        return {
            "total_execution_time_ms": total_time_ms,
            "stages_completed": len(completed_stages),
            "stages_failed": len(failed_stages),
            "total_stages": 11,
            "completion_rate": len(completed_stages) / 11,
            "server_usage": server_usage,
            "abilities_executed": sum(len(log.abilities_executed) for log in execution_log),
            "average_stage_time_ms": sum(log.duration_ms or 0 for log in execution_log) / max(len(execution_log), 1)
        }

    def _determine_final_status(self, state: AgentState) -> str:
        """Determine the final workflow status."""
        
        if state.get("errors"):
            return "completed_with_errors"
        elif state.get("escalation_decision", False):
            return "escalated"
        elif state.get("ticket_status") == "closed":
            return "resolved"
        else:
            return "completed"

    def _generate_resolution_summary(self, state: AgentState) -> str:
        """Generate a human-readable resolution summary."""
        
        if state.get("escalation_decision", False):
            return "Issue escalated to human agent for further assistance."
        
        selected_solution = state.get("selected_solution")
        if selected_solution:
            return f"Issue resolved using: {selected_solution.get('title', 'Standard Resolution')}. Customer response generated and notifications sent."
        
        return "Workflow completed successfully."

    def _get_best_solution_summary(self, state: AgentState) -> Dict[str, Any]:
        """Get summary of the best solution found."""
        
        solutions = state.get("retrieved_solutions", [])
        if not solutions:
            return {"message": "No solutions found"}
        
        best_solution = solutions[0]  # Solutions are sorted by relevance
        return {
            "id": best_solution.get("id"),
            "title": best_solution.get("title"),
            "relevance_score": best_solution.get("relevance_score"),
            "estimated_resolution_time": best_solution.get("estimated_resolution_time")
        }

    def _count_successful_actions(self, state: AgentState) -> Dict[str, int]:
        """Count successful actions in execution stage."""
        
        api_calls = state.get("api_calls_executed", [])
        notifications = state.get("notifications_sent", [])
        
        return {
            "successful_api_calls": sum(1 for call in api_calls if call.get("success", False)),
            "successful_notifications": sum(1 for notif in notifications if notif.get("sent", False)),
            "total_actions": len(api_calls) + len(notifications)
        }

    def _calculate_quality_scores(self, state: AgentState) -> Dict[str, float]:
        """Calculate overall quality scores for the workflow."""
        
        scores = {
            "understanding_accuracy": 0.0,
            "solution_relevance": 0.0,
            "response_quality": 0.0,
            "execution_success": 0.0,
            "overall_quality": 0.0
        }
        
        # Understanding accuracy (based on entity extraction confidence)
        entities = state.get("extracted_entities", {})
        if "confidence_score" in entities:
            confidence_scores = entities["confidence_score"]
            scores["understanding_accuracy"] = sum(confidence_scores.values()) / max(len(confidence_scores), 1)
        
        # Solution relevance (based on best solution score)
        solutions = state.get("retrieved_solutions", [])
        if solutions:
            scores["solution_relevance"] = solutions[0].get("relevance_score", 0.0)
        
        # Response quality (from response metadata)
        response_metadata = state.get("response_metadata", {})
        if response_metadata:
            quality_metrics = ["personalization_score", "clarity_score", "completeness_score"]
            response_scores = [response_metadata.get(metric, 0.0) for metric in quality_metrics]
            scores["response_quality"] = sum(response_scores) / len(response_scores)
        
        # Execution success (based on successful actions)
        action_counts = self._count_successful_actions(state)
        total_actions = action_counts["total_actions"]
        successful_actions = action_counts["successful_api_calls"] + action_counts["successful_notifications"]
        if total_actions > 0:
            scores["execution_success"] = successful_actions / total_actions
        
        # Overall quality (weighted average)
        weights = [0.2, 0.3, 0.3, 0.2]  # understanding, solution, response, execution
        quality_values = [scores["understanding_accuracy"], scores["solution_relevance"], 
                         scores["response_quality"], scores["execution_success"]]
        scores["overall_quality"] = sum(w * v for w, v in zip(weights, quality_values))
        
        return scores

    def get_final_payload(self, session_id: str) -> Dict[str, Any]:
        """
        Get the final payload for external use.
        
        Returns:
            Final structured payload
        """
        try:
            current_state = self.state_manager.get_current_state(session_id)
            return current_state.get("final_payload", {})
        except:
            return {"error": "Final payload not available"}

    def export_for_reporting(self, session_id: str) -> Dict[str, Any]:
        """
        Export data in format suitable for reporting systems.
        
        Returns:
            Reporting-friendly data structure
        """
        payload = self.get_final_payload(session_id)
        
        if "error" in payload:
            return payload
        
        return {
            "ticket_id": payload.get("ticket_id"),
            "customer_email": payload.get("email"),
            "resolution_status": payload.get("status"),
            "escalated": payload.get("escalated", False),
            "total_time_ms": payload.get("workflow_metrics", {}).get("total_execution_time_ms", 0),
            "stages_completed": payload.get("workflow_metrics", {}).get("stages_completed", 0),
            "quality_score": payload.get("quality_scores", {}).get("overall_quality", 0.0),
            "created_at": payload.get("created_at"),
            "completed_at": payload.get("completed_at")
        }

    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Output final structured payload",
            "mode": "payload_only",
            "abilities": ["output_payload"],
            "server": None,
            "next_stage": None,
            "is_final": True
        }