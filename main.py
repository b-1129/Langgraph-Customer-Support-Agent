"""
LangGraph Customer Support Agent - Main Execution

This is the main entry point for running the customer support agent.
It demonstrates the complete workflow with sample data and detailed logging.
"""
import os
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.agent.langgraph_agent import customer_support_agent

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/agent.log', mode='a', encoding="utf-8")
        ]
    )
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

async def run_demo():
    """
    Run a complete demo of the customer support agent.
    
    This demonstrates:
    1. Stage modeling
    2. State persistence  
    3. Sample query execution flow
    4. MCP server integration
    5. Decision making logic
    """
    
    logger = logging.getLogger(__name__)
    
    print("Clara - Customer Support Agent Demo")
    print("=" * 50)

    # Sample customer request
    sample_input = {
        "customer_name": "Brijesh Kapadiya",
        "email": "brijesh.kapadiya@example.com",
        "query": "Hi, I'm having trouble with my premium subscription. My payment failed yesterday and now I can't access my account. This is urgent as I need it for work. My account ID is ACC-12345.",
        "priority": "high",
        "ticket_id": None  # Will be auto-generated
    }

    print("Sample Customer Request:")
    print(f"Customer: {sample_input['customer_name']}")
    print(f"Email: {sample_input['email']}")
    print(f"Priority: {sample_input['priority']}")
    print(f"Query: {sample_input['query'][:100]}...")
    print()

    try:
        # Get agent info
        agent_info = customer_support_agent.get_agent_info()
        print(f"Agent: {agent_info['agent_name']} v{agent_info['version']}")
        print(f"Stages: {agent_info['stages_implemented']}/{agent_info['total_stages']} implemented")
        print()
        
        # Process the request
        print("Processing customer request...")
        print("─" * 30)
        
        start_time = datetime.now()
        result = await customer_support_agent.process_customer_request(sample_input)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds() * 1000
        
        print("─" * 30)
        print("Processing Complete!")
        print()

        # Display results
        print("EXECUTION RESULTS:")
        print("=" * 30)
        print(f"Ticket ID: {result['ticket_id']}")
        print(f"Status: {result['status']}")
        print(f"Escalated: {'Yes' if result['escalated'] else 'No'}")
        print(f"Stages Completed: {result['stages_completed']}")
        print(f"Processing Time: {processing_time:.0f}ms")
        print()

        # Display resolution
        if result.get('resolution'):
            print("GENERATED RESPONSE:")
            print("─" * 20)
            print(result['resolution'])
            print()

        # Display execution log
        print("EXECUTION LOG:")
        print("─" * 15)
        for i, log_entry in enumerate(result['execution_log'], 1):
            status_emoji = "✅" if log_entry.status == "completed" else "❌"
            print(f"{i:2d}. {status_emoji} {log_entry.stage_name}")
            print(f"{log_entry.duration_ms}ms | {', '.join(log_entry.abilities_executed)}")
            if log_entry.server_used:
                print(f"Server: {log_entry.server_used}")
            if log_entry.error_message:
                print(f"Error: {log_entry.error_message}")
            print()

        # Save results to file
        output_file = f"examples/demo_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("examples", exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"Results saved to: {output_file}")
        
        return result
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        print(f"Demo failed: {str(e)}")
        raise

async def run_custom_request():
    """Run the agent with custom input"""
    
    print("Custom Request Mode")
    print("Enter customer details:")
    
    customer_name = input("Customer Name: ").strip()
    email = input("Email: ").strip()
    priority = input("Priority (low/medium/high/urgent): ").strip() or "medium"
    query = input("Query: ").strip()
    
    custom_input = {
        "customer_name": customer_name,
        "email": email,
        "query": query,
        "priority": priority
    }
    
    print("\nProcessing custom request...")
    result = await customer_support_agent.process_customer_request(custom_input)
    
    print(f"\nResult: {result['status']}")
    if result.get('resolution'):
        print(f"Response: {result['resolution']}")


async def main():
    """Main entry point"""
    
    setup_logging()
    
    print("Welcome to Clara - Clear Answers, Caring Support")
    print("═" * 60)
    print()
    
    while True:
        print("Choose an option:")
        print("1. Run Demo with Sample Data")
        print("2. Run Custom Request")
        print("3. Show Agent Info")
        print("4. Exit")
        print()

        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            print("\n" + "="*50)
            await run_demo()

        elif choice == "2":
            print("\n" + "="*50)
            await run_custom_request()

        elif choice == "3":
            print("\n" + "="*50)
            agent_info = customer_support_agent.get_agent_info()
            print("AGENT INFORMATION:")
            print("=" * 30)
            print(f"Name: {agent_info['agent_name']}")
            print(f"Version: {agent_info['version']}")
            print(f"Stages: {agent_info['stages_implemented']}/{agent_info['total_stages']}")
            print("\nPersonality:")
            for trait in agent_info['personality']:
                print(f" - {trait}")
            print("\nMCP Servers:")
            for server, config in agent_info['mcp_servers'].items():
                print(f"  - {server.upper()}: {config['url']} ({config['description']})")

        elif choice == "4":
            print("\nGoodbye! Thank you for using Clara.")
            break
            
        else:
            print("Invalid choice. Please enter 1-4.")
        
        print("\n" + "-"*50 + "\n")

if __name__ == "__main__":
    asyncio.run(main())