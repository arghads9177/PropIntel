"""
Test Retrieval Pipeline - Phase 4B

This script tests the complete retrieval pipeline with various queries
to validate quality, performance, and functionality.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from retrieval.retrieval_orchestrator import RetrievalOrchestrator
from ingestion.config.env_loader import get_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_retrieval():
    """Test basic retrieval functionality"""
    print("\n" + "="*80)
    print("TEST 1: BASIC RETRIEVAL")
    print("="*80)
    
    orchestrator = RetrievalOrchestrator(persist_directory="./data/chromadb")
    
    test_queries = [
        "What are the specializations of Astha?",
        "How can I contact Astha?",
        "What are the office timings?",
        "Where does Astha operate?",
        "Tell me about Astha company",
        "What is the address of Bandel branch?",
        "What is the address of head office?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        response = orchestrator.retrieve(
            query=query,
            n_results=3,
            use_query_expansion=False,
            ranking_strategy='relevance'
        )
        orchestrator.print_results(response, show_metadata=True)


def test_query_expansion():
    """Test query expansion"""
    print("\n" + "="*80)
    print("TEST 2: QUERY EXPANSION")
    print("="*80)
    
    orchestrator = RetrievalOrchestrator(persist_directory="./data/chromadb")
    
    query = "What types of buildings does Astha construct?"
    
    print(f"\nOriginal Query: {query}")
    
    # Without expansion
    print("\n--- WITHOUT EXPANSION ---")
    response1 = orchestrator.retrieve(
        query=query,
        n_results=3,
        use_query_expansion=False,
        ranking_strategy='relevance'
    )
    
    print(f"\nExpanded Queries: None")
    for i, result in enumerate(response1['results'][:3], 1):
        print(f"[{i}] Score: {result['score']:.4f} | {result['content'][:100]}...")
    
    # With expansion
    print("\n--- WITH EXPANSION ---")
    response2 = orchestrator.retrieve(
        query=query,
        n_results=3,
        use_query_expansion=True,
        ranking_strategy='relevance'
    )
    
    print(f"\nExpanded Queries: {response2['processed_query']['expanded_queries']}")
    for i, result in enumerate(response2['results'][:3], 1):
        print(f"[{i}] Score: {result['score']:.4f} | {result['content'][:100]}...")


def test_ranking_strategies():
    """Test different ranking strategies"""
    print("\n" + "="*80)
    print("TEST 3: RANKING STRATEGIES")
    print("="*80)
    
    orchestrator = RetrievalOrchestrator(persist_directory="./data/chromadb")
    
    query = "Tell me about Astha's services and contact information"
    
    strategies = ['relevance', 'diversity', 'hybrid']
    
    for strategy in strategies:
        print(f"\n{'='*80}")
        print(f"STRATEGY: {strategy.upper()}")
        print("="*80)
        
        response = orchestrator.retrieve(
            query=query,
            n_results=5,
            ranking_strategy=strategy,
            use_query_expansion=False
        )
        
        for i, result in enumerate(response['results'], 1):
            final_score = result.get('final_score', result.get('score', 0))
            section = result['metadata'].get('section', 'N/A')
            subsection = result['metadata'].get('subsection', '')
            
            print(f"\n[{i}] Score: {final_score:.4f} | Section: {section}/{subsection}")
            print(f"    Content: {result['content'][:150]}...")


def test_multi_query_retrieval():
    """Test multi-query retrieval"""
    print("\n" + "="*80)
    print("TEST 4: MULTI-QUERY RETRIEVAL")
    print("="*80)
    
    orchestrator = RetrievalOrchestrator(persist_directory="./data/chromadb")
    
    query = "What does Astha specialize in?"
    
    # Single query
    print("\n--- SINGLE QUERY ---")
    response1 = orchestrator.retrieve(
        query=query,
        n_results=3,
        use_multi_query=False,
        ranking_strategy='relevance'
    )
    
    print(f"Results: {len(response1['results'])}")
    for i, result in enumerate(response1['results'], 1):
        print(f"[{i}] {result['content'][:100]}...")
    
    # Multi query
    print("\n--- MULTI-QUERY ---")
    response2 = orchestrator.retrieve(
        query=query,
        n_results=3,
        use_multi_query=True,
        use_query_expansion=True,
        ranking_strategy='relevance'
    )
    
    print(f"Queries used: {[response2['processed_query']['cleaned']] + response2['processed_query']['expanded_queries'][:2]}")
    print(f"Results: {len(response2['results'])}")
    for i, result in enumerate(response2['results'], 1):
        print(f"[{i}] {result['content'][:100]}...")


def test_filtered_retrieval():
    """Test retrieval with filters"""
    print("\n" + "="*80)
    print("TEST 5: FILTERED RETRIEVAL")
    print("="*80)
    
    orchestrator = RetrievalOrchestrator(persist_directory="./data/chromadb")
    
    query = "Tell me about Astha"
    
    sections = ['company_info', 'contact_details', 'social_media']
    
    for section in sections:
        print(f"\n--- FILTER: section={section} ---")
        response = orchestrator.retrieve(
            query=query,
            n_results=3,
            filters={'section': section},
            ranking_strategy='relevance'
        )
        
        print(f"Results: {len(response['results'])}")
        for i, result in enumerate(response['results'], 1):
            print(f"[{i}] {result['metadata'].get('subsection', 'N/A')}: {result['content'][:80]}...")


def test_query_types():
    """Test detection and handling of different query types"""
    print("\n" + "="*80)
    print("TEST 6: QUERY TYPE DETECTION")
    print("="*80)
    
    orchestrator = RetrievalOrchestrator(persist_directory="./data/chromadb")
    
    test_queries = [
        ("What are Astha's specializations?", "specialization"),
        ("How to contact Astha?", "contact"),
        ("Where does Astha operate?", "location"),
        ("Tell me about Astha", "about"),
        ("What are the office timings?", "timing"),
        ("What is Astha's social media?", "social")
    ]
    
    for query, expected_type in test_queries:
        response = orchestrator.retrieve(
            query=query,
            n_results=2,
            use_query_expansion=False,
            ranking_strategy='relevance'
        )
        
        detected_type = response['metadata']['query_type']
        filters = response['metadata']['filters_applied']
        
        print(f"\nQuery: {query}")
        print(f"Expected: {expected_type} | Detected: {detected_type}")
        print(f"Filters: {filters}")
        print(f"Top result section: {response['results'][0]['metadata']['section'] if response['results'] else 'N/A'}")


def test_performance():
    """Test retrieval performance"""
    print("\n" + "="*80)
    print("TEST 7: PERFORMANCE")
    print("="*80)
    
    orchestrator = RetrievalOrchestrator(persist_directory="./data/chromadb")
    
    queries = [
        "What are Astha's specializations?",
        "How to contact Astha?",
        "Where does Astha operate?",
        "What are the office timings?",
        "Tell me about Astha"
    ]
    
    print(f"\nTesting {len(queries)} queries...")
    
    responses = orchestrator.batch_retrieve(
        queries=queries,
        n_results=3,
        ranking_strategy='relevance'
    )
    
    total_duration = sum(r['metadata']['duration_seconds'] for r in responses)
    avg_duration = total_duration / len(responses)
    
    print(f"\nTotal Duration: {total_duration:.2f}s")
    print(f"Average Duration: {avg_duration:.2f}s")
    print(f"Queries per Second: {len(queries) / total_duration:.2f}")
    
    # Show statistics
    stats = orchestrator.get_pipeline_stats()
    print(f"\nPipeline Statistics:")
    print(f"  Total Queries: {stats['orchestrator_stats']['total_queries']}")
    print(f"  Successful: {stats['orchestrator_stats']['successful_queries']}")
    print(f"  Failed: {stats['orchestrator_stats']['failed_queries']}")
    print(f"  Avg Results/Query: {stats['orchestrator_stats']['average_results_per_query']:.2f}")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("PROPINTEL RETRIEVAL PIPELINE TEST SUITE")
    print("="*80)
    
    # Load environment
    config = get_config()
    logger.info("Environment configuration loaded")
    
    tests = [
        ("Basic Retrieval", test_basic_retrieval),
        ("Query Expansion", test_query_expansion),
        ("Ranking Strategies", test_ranking_strategies),
        ("Multi-Query Retrieval", test_multi_query_retrieval),
        ("Filtered Retrieval", test_filtered_retrieval),
        ("Query Type Detection", test_query_types),
        ("Performance", test_performance)
    ]
    
    for test_name, test_func in tests:
        try:
            logger.info(f"Running test: {test_name}")
            test_func()
        except Exception as e:
            logger.error(f"Test '{test_name}' failed: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)


def interactive_mode():
    """Interactive query mode"""
    print("\n" + "="*80)
    print("INTERACTIVE RETRIEVAL MODE")
    print("="*80)
    print("Enter queries to test retrieval. Type 'quit' to exit.")
    print("Commands:")
    print("  /simple <query> - Simple retrieval")
    print("  /advanced <query> - Advanced retrieval with all features")
    print("  /stats - Show statistics")
    print("="*80)
    
    orchestrator = RetrievalOrchestrator(persist_directory="./data/chromadb")
    
    while True:
        try:
            query = input("\n> ").strip()
            
            if not query:
                continue
            
            if query.lower() == 'quit':
                break
            
            if query.startswith('/stats'):
                stats = orchestrator.get_pipeline_stats()
                print(f"\nPipeline Statistics:")
                print(f"  Total Queries: {stats['orchestrator_stats']['total_queries']}")
                print(f"  Successful: {stats['orchestrator_stats']['successful_queries']}")
                print(f"  Average Results: {stats['orchestrator_stats']['average_results_per_query']:.2f}")
                continue
            
            if query.startswith('/simple '):
                query = query[8:]
                response = orchestrator.retrieve(
                    query=query,
                    n_results=3,
                    use_query_expansion=False,
                    ranking_strategy='relevance'
                )
            elif query.startswith('/advanced '):
                query = query[10:]
                response = orchestrator.retrieve_advanced(
                    query=query,
                    n_results=5
                )
            else:
                response = orchestrator.retrieve(
                    query=query,
                    n_results=5,
                    ranking_strategy='hybrid'
                )
            
            orchestrator.print_results(response, show_metadata=True)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
    
    print("\n\nGoodbye!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test PropIntel Retrieval Pipeline")
    parser.add_argument(
        '--mode',
        choices=['all', 'interactive', 'basic', 'expansion', 'ranking', 'multi', 'filter', 'types', 'performance'],
        default='all',
        help='Test mode to run'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        interactive_mode()
    elif args.mode == 'all':
        run_all_tests()
    elif args.mode == 'basic':
        test_basic_retrieval()
    elif args.mode == 'expansion':
        test_query_expansion()
    elif args.mode == 'ranking':
        test_ranking_strategies()
    elif args.mode == 'multi':
        test_multi_query_retrieval()
    elif args.mode == 'filter':
        test_filtered_retrieval()
    elif args.mode == 'types':
        test_query_types()
    elif args.mode == 'performance':
        test_performance()
