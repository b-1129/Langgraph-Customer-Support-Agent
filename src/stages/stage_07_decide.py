"""
Stage 7: DECIDE
Evaluate solutions and make escalation decisions

This is the CRITICAL non-deterministic stage where the agent makes intelligent
decisions about how to proceed based on solution scores and context.
"""

from typing import Any, Dict, List
from datetime import datetime
import logging

from ..agent.state_manager import AgentState, StateManager, StageStatus
from ..mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)


class DecideStage:
    """
    Stage 7: DECIDE
    
    Responsibilities:
    - Evaluate potential solutions and score them (1-100)
    - Make escalation decision based on scores and business rules
    - Select the best solution or escalate to human agent
    - Record decision reasoning for audit trail
    
    Mode: Non-deterministic (dynamic ability orchestration)
    Key Feature: If solution score < 90, escalate to human agent
    """
    
    def __init__(self, state_manager: StateManager, mcp_client: MCPClient):
        self.state_manager = state_manager
        self.mcp_client = mcp_client
        self.stage_id = 7
        self.stage_name = "DECIDE"
        
        # Business rules for decision making
        self.escalation_threshold = 90  # Score below this triggers escalation
        self.confidence_threshold = 0.8  # Minimum confidence for auto-resolution

    async def execute(self, session_id: str) -> AgentState:
        """
        Execute the DECIDE stage with non-deterministic logic.
        
        This is where the AI agent shows its intelligence - it evaluates
        context and makes decisions about which abilities to use and when.
        
        Args:
            session_id: Current session identifier
            
        Returns:
            Updated AgentState with decision results
        """
        
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting {self.stage_name} stage (non-deterministic)")
            
            # Get current state
            current_state = self.state_manager.get_current_state(session_id)
            
            # Check if we have solutions to evaluate
            if not current_state.get("retrieved_solutions"):
                raise Exception("No solutions found to evaluate")
            
            abilities_executed = []
            results = {}
            
            # Step 1: Always start by evaluating solutions
            logger.info("Evaluating solution quality...")
            solution_evaluation = await self._evaluate_solutions(current_state)
            abilities_executed.append("solution_evaluation")
            results["solution_scores"] = solution_evaluation
            
            # Step 2: Dynamic decision making based on scores
            best_solution, best_score = self._find_best_solution(solution_evaluation)
            
            logger.info(f"Best solution score: {best_score}")
            
            # Step 3: Make escalation decision (dynamic logic!)
            if best_score < self.escalation_threshold:
                logger.info(f"Score {best_score} < {self.escalation_threshold}, evaluating escalation...")
                
                escalation_result = await self._make_escalation_decision(
                    current_state, solution_evaluation, best_score
                )
                abilities_executed.append("escalation_decision")
                results["escalation_decision"] = True
                results["escalation_details"] = escalation_result
                results["selected_solution"] = None
                results["decision_reasoning"] = f"Escalated due to low solution score ({best_score})"
                
                logger.info("Case escalated to human agent")
                
            else:
                logger.info(f"Score {best_score} >= {self.escalation_threshold}, proceeding with auto-resolution")
                
                # No escalation needed - select best solution
                results["escalation_decision"] = False
                results["selected_solution"] = best_solution
                results["decision_reasoning"] = f"Auto-resolved with solution score {best_score}"
            
            # Step 4: Always update payload with decision
            results["decision_timestamp"] = datetime.now().isoformat()
            results["decision_confidence"] = solution_evaluation.get("confidence", 0.5)
            
            abilities_executed.append("update_payload")
            
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
            logger.info(f"Decision: {'Escalated' if results['escalation_decision'] else 'Auto-resolved'}")
            
            return updated_state
            
        except Exception as e:
            # Log error
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            self.state_manager.log_stage_execution(
                session_id=session_id,
                stage_id=self.stage_id,
                stage_name=self.stage_name,
                status=StageStatus.FAILED,
                abilities_executed=abilities_executed if 'abilities_executed' in locals() else [],
                duration_ms=execution_time,
                error_message=str(e)
            )
            
            logger.error(f"{self.stage_name} failed: {str(e)}")
            raise

    async def _evaluate_solutions(self, state: AgentState) -> Dict[str, Any]:
        """
        Evaluate and score all available solutions.
        Uses COMMON server for internal scoring algorithms.
        """
        
        logger.info("Scoring solutions...")
        
        # Prepare context with all relevant information
        context = {
            "retrieved_solutions": state.get("retrieved_solutions", []),
            "customer_tier": state.get("enriched_records", {}).get("customer_tier", "standard"),
            "priority": state["priority"],
            "extracted_entities": state.get("extracted_entities", {}),
            "customer_history": state.get("enriched_records", {})
        }
        
        # Call COMMON server for solution evaluation
        response = await self.mcp_client.execute_ability(
            ability_name="solution_evaluation",
            parameters={
                "scoring_method": "weighted_average",
                "criteria": ["relevance", "complexity", "success_rate", "customer_satisfaction"]
            },
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to evaluate solutions: {response.error}")
        
        return response.data
    
    async def _make_escalation_decision(
        self, 
        state: AgentState, 
        solution_evaluation: Dict[str, Any], 
        best_score: float
    ) -> Dict[str, Any]:
        """
        Make escalation decision using ATLAS server.
        This involves business logic and potentially external system checks.
        """
        
        logger.info("🔄 Making escalation decision...")
        
        # Prepare context for escalation decision
        context = {
            "solution_scores": solution_evaluation,
            "best_score": best_score,
            "escalation_threshold": self.escalation_threshold,
            "customer_tier": state.get("enriched_records", {}).get("customer_tier", "standard"),
            "priority": state["priority"],
            "sla_risk": state.get("calculated_flags", {}).get("sla_risk_score", 50),
            "customer_satisfaction_risk": state.get("calculated_flags", {}).get("customer_satisfaction_risk", "medium")
        }
        
        # Call ATLAS server for escalation decision
        response = await self.mcp_client.execute_ability(
            ability_name="escalation_decision",
            parameters={
                "solution_score": best_score,
                "threshold": self.escalation_threshold
            },
            context=context,
            session_id=state["session_id"]
        )
        
        if not response.success:
            raise Exception(f"Failed to make escalation decision: {response.error}")
        
        return response.data
    
    def _find_best_solution(self, solution_evaluation: Dict[str, Any]) -> tuple[Dict[str, Any], float]:
        """
        Find the highest scoring solution from evaluation results.
        
        Returns:
            Tuple of (best_solution_details, best_score)
        """
        
        solution_scores = solution_evaluation.get("solution_scores", {})
        
        if not solution_scores:
            return {}, 0.0
        
        # Find solution with highest overall score
        best_solution_id = None
        best_score = 0.0
        
        for solution_id, scores in solution_scores.items():
            overall_score = scores.get("overall_score", 0)
            if overall_score > best_score:
                best_score = overall_score
                best_solution_id = solution_id
        
        # Get the recommended solution from evaluation
        recommended_solution_id = solution_evaluation.get("recommended_solution")
        if recommended_solution_id and recommended_solution_id in solution_scores:
            best_solution_id = recommended_solution_id
            best_score = solution_scores[recommended_solution_id]["overall_score"]
        
        # Create best solution details
        best_solution = {
            "solution_id": best_solution_id,
            "score": best_score,
            "details": solution_scores.get(best_solution_id, {})
        }
        
        return best_solution, best_score
    
    def _should_escalate(
        self, 
        score: float, 
        confidence: float, 
        customer_tier: str = "standard"
    ) -> bool:
        """
        Business logic for escalation decisions.
        
        This is where you can customize escalation rules based on:
        - Solution confidence score
        - Customer tier (premium customers might have lower thresholds)
        - Issue complexity
        - SLA requirements
        """
        
        # Basic rule: score below threshold
        if score < self.escalation_threshold:
            return True
        
        # Premium customers: lower threshold
        if customer_tier == "premium" and score < 95:
            return True
        
        # Low confidence: escalate regardless of score
        if confidence < self.confidence_threshold:
            return True
        
        return False
    
    def get_stage_info(self) -> Dict[str, Any]:
        """Get information about this stage"""
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "description": "Evaluate solutions and make escalation decisions",
            "mode": "non_deterministic",
            "abilities": [
                {
                    "name": "solution_evaluation",
                    "server": "COMMON",
                    "description": "Score potential solutions 1-100"
                },
                {
                    "name": "escalation_decision",
                    "server": "ATLAS", 
                    "description": "Assign to human agent if score <90"
                },
                {
                    "name": "update_payload",
                    "server": "state",
                    "description": "Record decision outcomes"
                }
            ],
            "decision_logic": {
                "escalation_threshold": self.escalation_threshold,
                "confidence_threshold": self.confidence_threshold,
                "evaluation_criteria": ["solution_quality", "customer_satisfaction_risk", "complexity"]
            },
            "required_state": ["retrieved_solutions"],
            "next_stage": "UPDATE"
        }

        