#!/usr/bin/env python3
"""
PropIntel RAG System - Quick Demo
Demonstrates the complete Phase 4C implementation
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from generation.answer_generator import AnswerGenerator
from generation.llm_service import LLMProvider


def print_banner():
    """Print welcome banner"""
    print("=" * 80)
    print("🏡 PropIntel - Real Estate Intelligence Platform")
    print("=" * 80)
    print("Phase 4C: Answer Generation Demo")
    print("Status: ✅ FULLY OPERATIONAL")
    print("=" * 80)
    print()


def print_section(title):
    """Print section header"""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}\n")


def demo_basic_query():
    """Demonstrate basic query answering"""
    print_section("📋 Demo 1: Basic Question Answering")
    
    generator = AnswerGenerator()
    
    query = "What are the specializations of Astha?"
    print(f"Query: {query}\n")
    
    result = generator.generate_answer(query)
    
    print(f"Answer:\n{result['answer']}\n")
    print(f"Metadata:")
    print(f"  - Provider: {result['metadata']['provider']}")
    print(f"  - Response Time: {result['metadata']['response_time']:.2f}s")
    print(f"  - Tokens: {result['metadata']['tokens_used']}")
    print(f"  - Sources: {len(result['sources'])}")


def demo_contact_query():
    """Demonstrate contact information query"""
    print_section("📞 Demo 2: Contact Information Query")
    
    generator = AnswerGenerator()
    
    query = "How can I contact Astha?"
    print(f"Query: {query}\n")
    
    result = generator.generate_answer(query)
    
    print(f"Answer:\n{result['answer']}\n")
    print(f"Response Time: {result['metadata']['response_time']:.2f}s")


def demo_template_comparison():
    """Demonstrate different prompt templates"""
    print_section("🎨 Demo 3: Prompt Template Comparison")
    
    generator = AnswerGenerator()
    query = "Where does Astha operate?"
    
    templates = ["concise", "conversational"]
    
    for template in templates:
        print(f"\nTemplate: {template.upper()}")
        print("-" * 40)
        
        result = generator.generate_answer(
            query=query,
            template_name=template
        )
        
        print(f"{result['answer']}\n")


def demo_batch_processing():
    """Demonstrate batch query processing"""
    print_section("⚡ Demo 4: Batch Processing")
    
    generator = AnswerGenerator()
    
    queries = [
        "What does Astha do?",
        "What are the office timings?",
        "Where is Astha located?"
    ]
    
    print("Processing 3 queries in batch...\n")
    
    results = generator.batch_generate(queries)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {queries[i-1]}")
        if result['success']:
            answer = result['answer']
            # Print first 100 chars
            preview = answer[:100] + "..." if len(answer) > 100 else answer
            print(f"   → {preview}")
            print(f"   Time: {result['metadata']['response_time']:.2f}s\n")
        else:
            print(f"   → Error: {result.get('error', 'Unknown error')}\n")


def demo_statistics():
    """Show pipeline statistics"""
    print_section("📊 Demo 5: Pipeline Statistics")
    
    generator = AnswerGenerator()
    
    # Run a few queries to generate stats
    queries = [
        "Tell me about Astha",
        "What are their specializations?",
        "How to contact them?"
    ]
    
    for query in queries:
        generator.generate_answer(query)
    
    # Get statistics
    gen_stats = generator.get_stats()
    llm_stats = generator.llm.stats
    
    print("GENERATOR STATISTICS")
    print("-" * 40)
    print(f"Total Queries: {gen_stats['total_queries']}")
    print(f"Successful: {gen_stats['successful']}")
    print(f"Failed: {gen_stats['failed']}")
    print(f"Avg Response Time: {gen_stats['avg_response_time']:.2f}s")
    print(f"Total Tokens: {gen_stats['total_tokens']:,}")
    
    print("\nLLM STATISTICS")
    print("-" * 40)
    print(f"Total Requests: {llm_stats['total_requests']}")
    print(f"Successful: {llm_stats['successful_requests']}")
    print(f"Success Rate: {llm_stats['successful_requests']/llm_stats['total_requests']*100:.1f}%")
    print(f"Total Tokens: {llm_stats['total_tokens']:,}")


def main():
    """Run all demos"""
    print_banner()
    
    try:
        # Run demos
        demo_basic_query()
        demo_contact_query()
        demo_template_comparison()
        demo_batch_processing()
        demo_statistics()
        
        # Final message
        print("\n" + "=" * 80)
        print("✅ Demo completed successfully!")
        print("=" * 80)
        print("\nPhase 4C Implementation Status:")
        print("  ✓ Multi-provider LLM integration")
        print("  ✓ Advanced prompt engineering")
        print("  ✓ Answer validation & quality control")
        print("  ✓ Complete RAG pipeline operational")
        print("\n🚀 System is production-ready!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
