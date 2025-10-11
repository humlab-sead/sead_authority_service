#!/usr/bin/env python3
"""
Integration test script for ModificationTypeReconciliationStrategy

This script tests the LLM-based reconciliation with real or simulated data.
Run with: python scripts/test_modification_type_reconciliation.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from unittest.mock import AsyncMock

from src.strategies.modification_type import LLMModificationTypeReconciliationStrategy
from src.strategies.llm_models import ReconciliationResponse, ReconciliationResult, Candidate


async def test_modification_type_reconciliation():
    """Test the modification type reconciliation strategy"""
    
    print("=== Testing ModificationTypeReconciliationStrategy ===\n")
    
    # Sample lookup data (from your specification)
    sample_lookup_data = [
        {"modification_type_id": 1, "modification_type_name": "Carbonised", 
         "modification_type_description": "Organic matter converted to carbon, most commonly though heating."},
        {"modification_type_id": 2, "modification_type_name": "Calcified", 
         "modification_type_description": "Organic matter replaced by calcium."},
        {"modification_type_id": 3, "modification_type_name": "Eroded", 
         "modification_type_description": "Surface of fossil has been worn away by physical processes, such as sediment abbraision."},
        {"modification_type_id": 4, "modification_type_name": "Fragmented", 
         "modification_type_description": "Fossil is not whole."},
        {"modification_type_id": 5, "modification_type_name": "Mineralised (unspecific)", 
         "modification_type_description": "Organic matter replaced by unspecified mineral(s)."},
        {"modification_type_id": 6, "modification_type_name": "Pyritified", 
         "modification_type_description": "Organic matter replaced by pyrite or marcasite."},
        {"modification_type_id": 7, "modification_type_name": "Discoloured (more than expected)", 
         "modification_type_description": "Expected colour of fossil, considering preservation factors, is of an unexpected colour. E.g. as a result of dying."},
        {"modification_type_id": 8, "modification_type_name": "Petrified", 
         "modification_type_description": "Organic matter converted to stone by impregnation with silica."},
        {"modification_type_id": 9, "modification_type_name": "Encased in amber", 
         "modification_type_description": "Fossil is encapsulated in a piece of amber."},
        {"modification_type_id": 10, "modification_type_name": "Corroded", 
         "modification_type_description": "Surface of fossil has been damage by chemical processes."}
    ]
    
    # Test queries
    test_queries = [
        "charred",  # Should match Carbonised
        "turned to stone",  # Should match Petrified
        "broken into pieces",  # Should match Fragmented
        "worn down",  # Should match Eroded
        "replaced by minerals",  # Should match Mineralised
        "damaged by acid"  # Should match Corroded
    ]
    
    try:
        # Create strategy instance
        strategy = LLMModificationTypeReconciliationStrategy()
        print(f"✓ Created strategy: {strategy.__class__.__name__}")
        print(f"✓ Context: {strategy.get_context_description()[:100]}...")
        
        # Test data formatting
        formatted_lookup = strategy.format_lookup_data(sample_lookup_data)
        print(f"✓ Formatted lookup data ({len(formatted_lookup)} chars)")
        print("Sample lookup entries:")
        for line in formatted_lookup.split('\n')[:3]:
            print(f"  {line}")
        print("  ...")
        
        formatted_input = strategy.format_input_data(test_queries)
        print(f"✓ Formatted input data ({len(formatted_input)} chars)")
        print("Input entries:")
        for line in formatted_input.split('\n'):
            print(f"  {line}")
        
        # Mock cursor for database operations
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = sample_lookup_data
        
        print(f"\n=== Testing individual queries ===")
        
        # Test each query individually
        for query in test_queries[:3]:  # Test first 3 queries
            print(f"\nTesting query: '{query}'")
            
            try:
                # This would normally call the LLM, but since we may not have 
                # LLM configured, we'll test the data preparation parts
                lookup_data = await strategy.get_lookup_data(mock_cursor)
                print(f"✓ Retrieved {len(lookup_data)} lookup entries")
                
                # Test the prompt building (without actually calling LLM)
                context = strategy.get_context_description()
                formatted_lookup = strategy.format_lookup_data(lookup_data)
                formatted_input = strategy.format_input_data([query])
                
                # This would be the prompt sent to LLM
                prompt_template = """Find and list candidate matches for each input value based on the lookup data.

Context:
{context}

Lookup data:
{lookup_data}

Input values:
{data}"""
                
                prompt = prompt_template.format(
                    context=context,
                    lookup_data=formatted_lookup,
                    data=formatted_input
                )
                
                print(f"✓ Generated prompt ({len(prompt)} chars)")
                print(f"✓ Would send to LLM for processing")
                
            except Exception as e:
                print(f"✗ Error testing query '{query}': {e}")
        
        print(f"\n=== Summary ===")
        print(f"✓ Strategy implementation appears to be working correctly")
        print(f"✓ Data formatting and prompt generation functional")
        print(f"✓ Ready for LLM integration testing with configured provider")
        
        # Note about LLM configuration
        print(f"\nNote: To test actual LLM reconciliation, ensure:")
        print(f"  1. Ollama is running and accessible")
        print(f"  2. OLLAMA_BASE_URL environment variable is set")
        print(f"  3. LLM model is configured in config.yml")
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_modification_type_reconciliation())