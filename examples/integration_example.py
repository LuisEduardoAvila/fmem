#!/usr/bin/env python3
"""
fmem Integration Usage Example

This example demonstrates how to use fmem with OpenClaw integration
for automatic memory recall during conversations.
"""

import sys
import os

# Add src to path to import fmem integration
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fmem_integration import auto_recall, should_search, format_results

def test_integration():
    """Test the integration features."""
    print("=== fmem Integration Usage Example ===")
    
    # Test messages that should trigger memory search
    test_messages = [
        "What were my preferences for the agent setup?",
        "Look up my recent interactions with Luis",
        "Find information about the workspace configuration",
        "Tell me about the workspace project structure",
        "Hello, how are you?"  # This should not trigger search
    ]
    
    for message in test_messages:
        print(f"\nMessage: '{message}'")
        
        # Check if search should be triggered
        should_trigger = should_search(message)
        print(f"Should search: {should_trigger}")
        
        if should_trigger:
            # Perform automatic recall
            results = auto_recall(message, top_k=2)
            print(f"Found {len(results)} results:")
            
            # Format results
            formatted = format_results(results)
            if formatted:
                print("Formatted context:")
                print(formatted)
            else:
                print("No relevant memories found")
        else:
            print("No memory search triggered")
    
    print("\n=== Integration Example Complete ===")

if __name__ == "__main__":
    test_integration()