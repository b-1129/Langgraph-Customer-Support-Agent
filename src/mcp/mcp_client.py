"""
MCP (Model Context Protocol) client integration

This module provides a unified interface to communicate with:
- ATLAS Server: External system interactions (database, APIs, etc.)
- COMMON Server: Internal processing (text parsing, calculations, etc.)

Think of this as a 'communication layer' that lets our agent talk to external services.
"""

import asyncio
import json
import logging
import httpx
from typing import Any, Dict, Optional, Union, List
from datetime import datetime
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

class MCPServerType(str, Enum):
    """Types of MCP servers we can connect to."""
    ATLAS = "ATLAS" # External system interactions
    COMMON = "COMMON" # Internal processing

class MCPRequest(BaseModel):
    """Standardized request format for MCP servers"""
    ability_name: str
    parameters: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    session_id: str
    timestamp: datetime

class MCPResponse(BaseModel):
    """Standardized response format from MCP servers"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    server_type: MCPServerType

class MCPClient:
    """
    Unified MCP client that can communicate with both Atlas and Common servers.
    
    This acts as a 'translator' - it takes ability requests from our agent
    and sends them to the appropriate server in the correct format.
    """

    def __init__(self, 
                 atlas_url: str = "http://localhost:80001",
                 common_url: str = "http://localhost:80002",
                 timeout: int = 30):
        self.atlas_url = atlas_url
        self.common_url = common_url
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)

        # Track which abilities go to which server
        self.server_mapping = {
            # ATLAS Server - External interactions
            "extract_entities": MCPServerType.ATLAS,
            "enrich_records": MCPServerType.ATLAS, 
            "clarify_question": MCPServerType.ATLAS,
            "extract_answer": MCPServerType.ATLAS,
            "knowledge_base_search": MCPServerType.ATLAS,
            "escalation_decision": MCPServerType.ATLAS,
            "update_ticket": MCPServerType.ATLAS,
            "close_ticket": MCPServerType.ATLAS,
            "execute_api_calls": MCPServerType.ATLAS,
            "trigger_notifications": MCPServerType.ATLAS,

            # COMMON Server - Internal processing
            "parse_request_text": MCPServerType.COMMON,
            "normalize_fields": MCPServerType.COMMON,
            "add_flags_calculations": MCPServerType.COMMON,
            "solution_evaluation": MCPServerType.COMMON,
            "response_generation": MCPServerType.COMMON,
        }

    async def execute_ability(
            self,
            ability_name: str,
            parameters: Dict[str, Any] = None,
            context: Dict[str, Any] = None,
            session_id: str = None
    ) -> MCPResponse:
        """
        Execute an ability on the appropriate MCP server.
        
        This is the main method that stages will call to execute their abilities.
        
        Args:
            ability_name (str): Name of the ability to execute
            parameters: Parameters for the ability
            context: Additional context (current state, etc.)
            session_id: session identifier
            
        Returns:
            MCPResponse with results
        """

        # Determine which server to use
        server_type  = self.server_mapping.get(ability_name)
        if not server_type:
            return MCPResponse(
                success=False,
                error=f"Unknown ability: {ability_name}",
                server_type= None
            )
        
        # prepare request
        request = MCPRequest(
            ability_name=ability_name,
            parameters=parameters or {},
            context=context or {},
            session_id=session_id or "UnknownSession",
            timestamp=datetime.now()
        )

        # Route to appropriate server
        if server_type == MCPServerType.ATLAS:
            return await self._call_atlas_server(request)
        else:
            return await self._call_common_server(request)
        
    async def _call_atlas_server(self, request: MCPRequest) -> MCPResponse:
        """
        Call the Atlas server for external system interactions.
        
        Atlas handles things like:
        - Database queries
        - External API calls
        - File system operations
        - Email sending
        """
        start_time = datetime.now()

        try:
            # In a real implementation, this would be an actual HTTP call
            # For demo purposes, we'll simulate the responses

            logger.info(f"calling ATLAS server for ability: {request.ability_name}")

            # Simulate different response patterns based on ability
            response_data = await self._simulate_atlas_response(request)

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return MCPResponse(
                success=True,
                data=response_data,
                server_type=MCPServerType.ATLAS,
                execution_time_ms=execution_time
            )
        
        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Atlas server error for {request.ability_name} : {str(e)}")

            return MCPResponse(
                success=False,
                error=str(e),
                server_type=MCPServerType.ATLAS,
                execution_time_ms=execution_time 
            )
        
    async def _call_common_server(self, request: MCPRequest) -> MCPResponse:
        """
        Call the Common server for internal processing.
        
        Common handles things like:
        - Text parsing and NLP
        - Calculations and scoring
        - Data transformations
        - Response generation
        """

        start_time = datetime.now()

        try:
            logger.info(f"calling COMMON server for abilirty: {request.ability_name}")

            # Simulate different response patterns based on ability
            response_data = await self._simulate_common_response(request)

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return MCPResponse(
                success=True,
                data = response_data,
                server_type=MCPServerType.COMMON,
                execution_time_ms=execution_time
            )
        except Exception as e:
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            logger.error(f"Common server error for {request.ability_name} : {str(e)}")

            return MCPResponse(
                success=False,
                error=str(e),
                server_type=MCPServerType.COMMON,
                execution_time_ms=execution_time
            )
        
    async def _simulate_atlas_response(self, request: MCPRequest) -> Dict[str, Any]:
        """
        Simulate Atlas server response for demo purposes.
        In a real implementation, this would be replaces with actual HTTP calls.
        """

        ability = request.ability_name
        params = request.parameters
        context = request.context

        # Simulate network delay
        await asyncio.sleep(0.1)

        if ability == "extract_entities":
            # Extract entities from customer query
            query = context.get("query", "")
            return {
                "entities": {
                    "product": "Premium Subscription",
                    "account_id": "ACC-12345",
                    "issue_type": "Billing",
                    "dates_mentioned": ["2024-01-15"],
                    "urgency_keywords": ["urgent", "immediately"]
                },
                "confidence_score": {
                    "product": 0.95,
                    "account_id": 0.88,
                    "issue_type": 0.92
                }
            }
        elif ability == "enrich_records":
            # Add customer history and SLA info
            return {
                "customer_tier": "premium",
                "sla_response_time": "4 hours",
                "previous_tickets": 3,
                "satisfaction_score": 4.2,
                "account_value": "$2,400/year",
                "risk_flags": ["high_value_customer"]
            }
        elif ability == "clarify_question":
            # Generate clasrifying questions
            return {
                "questions needed": True,
                "questions": [
                    "Could you please provide your account ID?",
                    "When did this billing issue first occur?",
                    "What specific error message are you seeing?"
                ],
                "priority": "high"
            }
        elif ability == "extract_answer":
            # Extract customer's response (simulated)
            return {
                "extracted_info": {
                    "account_id": "ACC-12345",
                    "error_date": "2024-01-15",
                    "error_message": "Payment failed - card declined"
                },
                "completeness": 0.85
            }
        elif ability == "knowledge_base_search":
            # Search knowledge base for solutions
            query = context.get("query", "")
            entities = context.get("entities", {})

            return {
                "solutions_found": [
                    {
                        "id": "SOL-001",
                        "title": "Billing Payment Failure Resolution",
                        "relevance_score": 0.92,
                        "steps": [
                            "Verify payment method is valid",
                            "Check account balance",
                            "Update billing information",
                            "Process manual payment if needed"
                        ],
                        "estimated_resolution_time": "15 minutes"
                    },
                    {
                        "id": "SOL-002", 
                        "title": "Card Decline Troubleshooting",
                        "relevance_score": 0.87,
                        "steps": [
                            "Contact bank to verify card status",
                            "Try alternative payment method",
                            "Update card information"
                        ],
                        "estimated_resolution_time": "10 minutes"
                    }
                ],
                "total_results": 2
            }
        elif ability == "escalation_decision":
            # Make escalation decision based on score
            solution_score = params.get("solution_score", 0)
            return {
                "should_escalate": solution_score < 90,
                "escalation_reason": "Solution confidence below threshold" if solution_score < 90 else None,
                "assigned_agent": "senior_agent_001" if solution_score < 90 else None,
                "escalation_priority": "high" if solution_score < 70 else "medium" 
            }
        elif ability == "update_ticket":
            # Update ticket in system
            return {
                "ticket_updated": True,
                "new_status": "In Progress",
                "fields_updated": ["status", "priority", "assigned_agent", "sla_target"],
                "timestamp": datetime.now().isoformat()
            }
        elif ability == "close_ticket":
            # Close the ticket
            return {
                "ticket_closed": True,
                "resolution_code": "resolved_payment_issue",
                "customer_satisfaction_survey_sent": True,
                "timestamp": datetime.now().isoformat()
            }
        elif ability == "execute_api_calls":
            # Execute API calls to external systems
            return {
                "api_calls_executed": [
                    {
                        "system": "billing_system",
                        "action": "update_payment_method",
                        "success": True,
                        "response_code": 200
                    },
                    {
                        "system": "crm_system",
                        "action": "update_customer_record",
                        "success": True,
                        "response_code": 200
                    }
                ],
                "total_calls": 2,
                "failures": 0
            }
        elif ability == "trigger_notifications":
            # Send notifications to customers
            return {
                "notifications_sent": [
                    {
                        "type": "email",
                        "recipient": context.get("email", "customer@example.com"),
                        "subject": "Your support ticket has been resolved",
                        "sent": True,
                        "timestamp": datetime.now().isoformat()
                    },
                    {
                        "type": "sms",
                        "recipient": "+1234567890",
                        "message": "Your billing issue has been resolved. Check your email for details.",
                        "sent": True,
                        "timestamp": datetime.now().isoformat()
                    }
                ],
                "delivery_status": "all_sent"
            }
        else:
            return {"message": f"Atlas ability '{ability}' executed successfully"}
        
    async def _simulate_common_response(self, request: MCPRequest) -> Dict[str, Any]:
        """
        Simulate Common server responses for demo purposes.
        In production, this would make actual HTTP calls to Common server.
        """
        ability = request.ability_name
        params = request.parameters
        context = request.context

        # Simulate processing delay
        await asyncio.sleep(0.05)

        if ability == "parse_request_text":
            # Parse unstructured text into structured format
            query = context.get("query", "")
            return {
                "structured_request": {
                    "category": "Billing",
                    "sub_category": "Payment Issue",
                    "urgency": "High",
                    "customer_sentiment": "Frustrated",
                    "key_phrases": ["payment failed", "card declined", "need help"],
                    "intent": "resolve_billing_issue"
                },
                "parsing_confidence": 0.91
            }
        elif ability == "normalize_fields":
            # Standardize data formats
            return {
                "normalized_data": {
                    "customer_name": "Brijesh Kapadiya", # Proper case
                    "email": "brijesh.kapadiya@example.com", # Lowercase
                    "phone": "+91 1234567890",  # Standard format
                    "priority": "HIGH",  # Uppercase
                    "created_date": "2024-01-15T10:30:00Z",  # ISO format
                    "ticket_id": "TKT-20240115-12345678"  # Standard format
                },
                "normalization_rules_applied": [
                    "name_proper_case",
                    "email_lowercase", 
                    "phone_international_format",
                    "priority_uppercase",
                    "date_iso_format"
                ]
            }
        elif ability == "add_flags_calculations":
            # Calculate priority flags and risk scores
            customer_data = context.get("enriched_records", {})
            return {
                "calculated_flags": {
                    "sla_risk_score": 75,  # Out of 100
                    "customer_value_tier": "premium",
                    "escalation_probability": 0.25,
                    "resolution_complexity": "medium",
                    "customer_satisfaction_risk": "low"
                },
                "priority_adjustments": {
                    "original_priority": "medium",
                    "adjusted_priority": "high",
                    "adjustment_reason": "premium_customer + sla_risk"
                },
                "sla_targets": {
                    "first_response": "4 hours",
                    "resolution": "24 hours",
                    "time_remaining": "3.5 hours"
                }
            }
        elif ability == "solution_evaluation":
            # Score potential solutions
            solutions = context.get("retrieved_solutions", [])
            return {
                "solution_scores": {
                    "SOL-001": {
                        "overall_score": 92,
                        "relevance": 95,
                        "complexity": 20,  # Lower is better
                        "success_rate": 88,
                        "customer_satisfaction_predicted": 4.2
                    },
                    "SOL-002": {
                        "overall_score": 78,
                        "relevance": 85,
                        "complexity": 40,
                        "success_rate": 72,
                        "customer_satisfaction_predicted": 3.8
                    }
                },
                "recommended_solution": "SOL-001",
                "confidence": 0.92,
                "evaluation_criteria": [
                    "relevance_to_issue",
                    "historical_success_rate", 
                    "implementation_complexity",
                    "customer_satisfaction_impact"
                ]
            }
        elif ability == "response_generation":
            # Generate customer response
            solution = context.get("selected_solution", {})
            customer_name = context.get("customer_name", "Valued Customer")
            
            return {
                "generated_response": f"""Dear {customer_name},

Thank you for contacting us regarding your billing issue. I've reviewed your account and identified the problem with your recent payment.

Here's what I've found and resolved:
• Your payment method was declined due to insufficient funds
• I've updated your billing information and processed the payment manually
• Your account is now current and services are fully restored

To prevent this in the future, I recommend:
• Setting up automatic payment notifications
• Adding a backup payment method to your account

Your ticket has been resolved. If you have any other questions, please don't hesitate to reach out.

Best regards,
Customer Support Team
Ticket ID: {context.get('ticket_id', 'N/A')}""",
                
                "response_metadata": {
                    "tone": "professional_friendly",
                    "length": "medium",
                    "personalization_score": 0.85,
                    "clarity_score": 0.92,
                    "completeness_score": 0.88
                }
            }
        
        else:
            return {"message": f"Common ability '{ability}' executed successfully"}
    
    async def health_check(self) -> Dict[str, bool]:
        """Check if both MCP servers are healthy"""
        
        atlas_healthy = await self._check_server_health(self.atlas_url)
        common_healthy = await self._check_server_health(self.common_url)
        
        return {
            "atlas_server": atlas_healthy,
            "common_server": common_healthy,
            "overall": atlas_healthy and common_healthy
        }
    async def _check_server_health(self, url: str) -> bool:
        """Check if a specific server is responding"""
        try:
            response = await self._client.get(f"{url}/health", timeout=5.0)
            return response.status_code == 200
        except:
            # In simulation mode, always return healthy
            return True
        
    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()


# Global MCP client instance
mcp_client = MCPClient()
