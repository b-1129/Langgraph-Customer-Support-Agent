
"""
LangGraph Customer Support Agent

This is the main orchestrator that manages the 11-stage workflow using LangGraph.
It handles both deterministic and non-deterministic stages, state persistence,
and MCP client integration.
"""

import json
import yaml
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
from pathlib import Path

from langgraph.graph import StateGraph, END

from .state_manager import AgentState, StateManager, StageStatus, state_manager
from ..mcp.mcp_client import MCPClient, mcp_client

# Import all stage implementations
from ..stages.stage_01_intake import IntakeStage
from ..stages.stage_02_understand import UnderstandStage
from ..stages.stage_03_prepare import PrepareStage
from ..stages.stage_04_ask import AskStage
from ..stages.stage_05_wait import WaitStage
from ..stages.stage_06_retrieve import RetrieveStage
from ..stages.stage_07_decide import DecideStage
from ..stages.stage_08_update import UpdateStage
from ..stages.stage_09_create import CreateStage
from ..stages.stage_10_do import DoStage
from ..stages.stage_11_complete import CompleteStage

logger = logging.getLogger(__name__)

class LangGraphCustomerSupportAgent:
    """
    Clara - A structured and logical LangGraph Agent for customer support.
    
    This agent:
    - Thinks in stages: each node represents a clear phase of the workflow
    - Carries forward state variables from one stage to the next  
    - Knows whether to execute sequentially or choose dynamically
    - Orchestrates MCP clients to call either Atlas or Common servers
    - Logs every decision clearly and outputs final structured payload
    """

    def __init__(self, config_path: str = "config/agent_config.yaml"):
        self.config = self._load_config(config_path)
        self.stages_config = self._load_stages_config("config/stages_config.json")

        # Initialize dependencies
        self.state_manager = state_manager
        self.mcp_client = mcp_client

        # Initialize all stage handlers
        self.stages = self._initialize_stages()

        # Build the LangGraph workflow
        self.workflow = self._build_langgraph_workflow()

        logger.info("Clara - Customer Support Agent initialized")
        logger.info(f"Loaded {len(self.stages)} stages")

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load agent configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
        
    def _load_stages_config(self, config_path: str) -> Dict[str, Any]:
        """Load stages configuration from JSON file"""
        with open(config_path, 'r') as f:
            return json.load(f)

    def _initialize_stages(self) -> Dict[str, Any]:
        """Initialize all stage handlers"""

        stages = {}

        # Initialize each stage with proper dependencies
        stages["INTAKE"] = IntakeStage(self.state_manager)
        stages["UNDERSTAND"] = UnderstandStage(self.state_manager, self.mcp_client)
        stages["PREPARE"] = PrepareStage(self.state_manager, self.mcp_client)
        stages["ASK"] = AskStage(self.state_manager, self.mcp_client)
        stages["WAIT"] = WaitStage(self.state_manager, self.mcp_client)
        stages["RETRIEVE"] = RetrieveStage(self.state_manager, self.mcp_client)
        stages["DECIDE"] = DecideStage(self.state_manager, self.mcp_client)
        stages["UPDATE"] = UpdateStage(self.state_manager, self.mcp_client)
        stages["CREATE"] = CreateStage(self.state_manager, self.mcp_client)
        stages["DO"] = DoStage(self.state_manager, self.mcp_client)
        stages["COMPLETE"] = CompleteStage(self.state_manager)

        return stages

    def _build_langgraph_workflow(self) -> StateGraph:
        """
        Build the LangGraph workflow with all 11 stages.
        
        This creates the graph structure that defines how stages connect
        and how state flows between them.
        """

        workflow = StateGraph(AgentState)

        # Add all nodes (stages) to the graph
        workflow.add_node("intake", self._execute_intake_stage)
        workflow.add_node("understand", self._execute_understand_stage)
        workflow.add_node("prepare", self._execute_prepare_stage)
        workflow.add_node("ask", self._execute_ask_stage)
        workflow.add_node("wait", self._execute_wait_stage)
        workflow.add_node("retrieve", self._execute_retrieve_stage)
        workflow.add_node("decide", self._execute_decide_stage)
        workflow.add_node("update", self._execute_update_stage)
        workflow.add_node("create", self._execute_create_stage)
        workflow.add_node("do", self._execute_do_stage)
        workflow.add_node("complete", self._execute_complete_stage)

        # Define the workflow flow (stage connections)
        workflow.add_edge("intake", "understand")
        workflow.add_edge("understand", "prepare")
        workflow.add_edge("prepare", "ask")
        workflow.add_edge("ask", "wait")
        workflow.add_edge("wait", "retrieve")
        workflow.add_edge("retrieve", "decide")

        # Conditional routing from DECIDE stage based on escalation decision
        workflow.add_conditional_edges(
            "decide",
            self._decide_next_stage,
            {
                "update": "update", 
                "escalate": END
            }
        )

        workflow.add_edge("update", "create")
        workflow.add_edge("create", "do")
        workflow.add_edge("do", "complete")
        workflow.add_edge("complete", END)

        # Set entry point
        workflow.set_entry_point("intake")

        # Compile the workflow
        return workflow.compile()
    
    async def process_customer_request(self, input_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point to process a customer support request.
        
        Args:
            input_payload: Customer request data
            
        Returns:
            Final processed payload with resolution
        """
        
        logger.info("Starting customer support workflow")
        logger.info(f"Customer: {input_payload.get('customer_name', 'Unknown')}")
        logger.info(f"Email: {input_payload.get('email', 'Unknown')}")
        logger.info(f"Query: {input_payload.get('query', 'Unknown')[:100]}...")
        
        try:
            # Execute the LangGraph workflow
            result = await self.workflow.ainvoke(input_payload)
            
            # Extract final results
            final_payload = {
                "ticket_id": result.get("ticket_id"),
                "status": result.get("ticket_status", "processed"),
                "resolution": result.get("generated_response"),
                "escalated": result.get("escalation_decision", False),
                "execution_log": result.get("execution_log", []),
                "session_id": result.get("session_id"),
                "processing_time": self._calculate_processing_time(result),
                "stages_completed": len([log for log in result.get("execution_log", []) 
                                       if log.status == StageStatus.COMPLETED])
            }
            
            logger.info("Workflow completed successfully")
            logger.info(f"Ticket ID: {final_payload['ticket_id']}")
            logger.info(f"Status: {final_payload['status']}")
            logger.info(f"Processing time: {final_payload['processing_time']}ms")
            
            return final_payload
            
        except Exception as e:
            logger.error(f"Workflow failed: {str(e)}")
            raise

    # Stage execution methods (called by LangGraph nodes)

    async def _execute_intake_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 1: INTAKE"""
        logger.info("Executing INTAKE stage")
        return await self.stages["INTAKE"].execute(state)
    
    async def _execute_understand_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 2: UNDERSTAND"""
        logger.info("Executing UNDERSTAND stage")
        return await self.stages["UNDERSTAND"].execute(state["session_id"])
    
    async def _execute_prepare_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 3: PREPARE"""
        logger.info("Executing PREPARE stage")
        # Placeholder for PREPARE stage implementation
        return self._simulate_stage_execution(state, "PREPARE", 3)
    
    async def _execute_ask_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 4: ASK"""
        logger.info("Executing ASK stage")
        # Placeholder for ASK stage implementation
        return self._simulate_stage_execution(state, "ASK", 4)
    
    async def _execute_wait_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 5: WAIT"""
        logger.info("Executing WAIT stage")
        # Placeholder for WAIT stage implementation
        return self._simulate_stage_execution(state, "WAIT", 5)
    
    async def _execute_retrieve_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 6: RETRIEVE"""
        logger.info("Executing RETRIEVE stage")
        # Simulate knowledge base retrieval
        simulated_solutions = [
            {
                "id": "SOL-001",
                "title": "Billing Payment Failure Resolution",
                "relevance_score": 0.92,
                "steps": ["Verify payment method", "Check account balance", "Update billing info"]
            }
        ]
        
        updated_state = self.state_manager.update_state(
            session_id=state["session_id"],
            updates={"retrieved_solutions": simulated_solutions},
            stage_name="RETRIEVE"
        )
        
        return updated_state
    
    async def _execute_decide_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 7: DECIDE (Critical non-deterministic stage)"""
        logger.info("Executing DECIDE stage")
        return await self.stages["DECIDE"].execute(state["session_id"])
    
    async def _execute_update_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 8: UPDATE"""
        logger.info("Executing UPDATE stage")
        return self._simulate_stage_execution(state, "UPDATE", 8)
    
    async def _execute_create_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 9: CREATE"""
        logger.info("Executing CREATE stage")
        return self._simulate_stage_execution(state, "CREATE", 9)
    
    async def _execute_do_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 10: DO"""
        logger.info("Executing DO stage")
        return self._simulate_stage_execution(state, "DO", 10)
    
    async def _execute_complete_stage(self, state: AgentState) -> AgentState:
        """Execute Stage 11: COMPLETE"""
        logger.info("Executing COMPLETE stage")

        # Create final payload
        final_payload = {
            "ticket_id": state["ticket_id"],
            "customer_name": state["customer_name"],
            "email": state["email"],
            "status": "resolved",
            "resolution": state.get("generated_response", "Issue resolved successfully"),
            "escalated": state.get("escalation_decision", False),
            "processing_summary": {
                "total_stages": 11,
                "stages_executed": len(state["execution_log"]),
                "total_time": self._calculate_processing_time(state)
            }
        }

        updated_state = self.state_manager.update_state(
            session_id=state["session_id"],
            updates={"final_payload": final_payload},
            stage_name="COMPLETE"
        )

        return updated_state
    
    def _decide_next_stage(self, state: AgentState) -> str:
        """
        Conditional routing logic for DECIDE stage.
        
        This determines whether to continue with auto-resolution (UPDATE)
        or escalate to human agent (END workflow).
        """
        
        escalation_decision = state.get("escalation_decision", False)
        
        if escalation_decision:
            logger.info("Routing to escalation (ending workflow)")
            return "escalate"
        else:
            logger.info("Routing to auto-resolution (UPDATE stage)")
            return "update"
        
    def _simulate_stage_execution(
        self, 
        state: AgentState, 
        stage_name: str, 
        stage_id: int
    ) -> AgentState:
        """
        Simulate stage execution for stages not fully implemented.
        This is useful for testing the overall workflow.
        """
        
        # Log simulated execution
        self.state_manager.log_stage_execution(
            session_id=state["session_id"],
            stage_id=stage_id,
            stage_name=stage_name,
            status=StageStatus.COMPLETED,
            abilities_executed=[f"simulated_{stage_name.lower()}"],
            server_used="SIMULATED",
            duration_ms=100,
            output={"simulated": True, "stage": stage_name}
        )
        
        # Add some simulated data based on stage
        updates = {}
        if stage_name == "CREATE":
            updates["generated_response"] = f"Dear {state['customer_name']}, your issue has been resolved successfully."
        
        return self.state_manager.update_state(
            session_id=state["session_id"],
            updates=updates,
            stage_name=stage_name
        )
    
    def _calculate_processing_time(self, state: AgentState) -> int:
        """Calculate total processing time from execution log"""
        total_time = 0
        for log_entry in state.get("execution_log", []):
            if hasattr(log_entry, 'duration_ms') and log_entry.duration_ms:
                total_time += log_entry.duration_ms
        return total_time
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent configuration"""
        return {
            "agent_name": self.config["agent"]["name"],
            "version": self.config["agent"]["version"],
            "total_stages": len(self.stages_config["stages"]),
            "stages_implemented": len(self.stages),
            "personality": self.config["personality"],
            "mcp_servers": self.config["mcp_servers"]
        }
    
customer_support_agent = LangGraphCustomerSupportAgent()