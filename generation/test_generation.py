"""
Test Answer Generation Pipeline - Phase 4C

This script tests the complete answer generation pipeline with various questions.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from generation.answer_generator import AnswerGenerator
from generation.answer_validator import AnswerValidator
from ingestion.config.env_loader import get_config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_generation():
    """Test basic answer generation"""
    print("\n" + "="*80)
    print("TEST 1: BASIC ANSWER GENERATION")
    print("="*80)
    
    generator = AnswerGenerator(
        llm_provider="groq",
        persist_directory="./data/chromadb"
    )
    
    test_queries = [
        "What are the specializations of Astha?",
        "How can I contact Astha?",
        "What are the office timings?",
        "Where does Astha operate?",
        "Tell me about Astha company"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        response = generator.generate_answer(query, n_results=3)
        generator.print_answer(response, show_sources=True, show_metadata=True)


def test_different_templates():
    """Test different prompt templates"""
    print("\n" + "="*80)
    print("TEST 2: DIFFERENT TEMPLATES")
    print("="*80)
    
    generator = AnswerGenerator(llm_provider="groq", persist_directory="./data/chromadb")
    
    query = "What services does Astha provide?"
    
    templates = ['default', 'conversational', 'concise', 'detailed']
    
    for template in templates:
        print(f"\n{'='*80}")
        print(f"TEMPLATE: {template.upper()}")
        print("="*80)
        
        response = generator.generate_answer(
            query=query,
            template_name=template,
            n_results=5
        )
        
        print(f"\nQuestion: {query}")
        print(f"\nAnswer:\n{response.get('answer', 'ERROR: No answer generated')}")
        print(f"\nTokens: {response.get('metadata', {}).get('tokens_used', 0)}")


def test_answer_validation():
    """Test answer validation"""
    print("\n" + "="*80)
    print("TEST 3: ANSWER VALIDATION")
    print("="*80)
    
    generator = AnswerGenerator(llm_provider="groq", persist_directory="./data/chromadb")
    validator = AnswerValidator()
    
    test_queries = [
        "What are Astha's specializations?",
        "How to contact Astha?",
        "What are the office timings?"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print("-"*80)
        
        # Generate answer
        response = generator.generate_answer(query, n_results=5)
        
        if response.get('answer'):
            # Validate answer
            validation = validator.validate(
                answer=response['answer'],
                query=query,
                context_results=response.get('retrieval_results', [])
            )
            
            print(f"\nAnswer: {response['answer']}")
            print(f"\n--- VALIDATION RESULTS ---")
            print(f"Valid: {validation.is_valid}")
            print(f"Confidence: {validation.confidence_score:.2%}")
            
            if validation.issues:
                print(f"\nIssues:")
                for issue in validation.issues:
                    print(f"  - {issue}")
            
            if validation.warnings:
                print(f"\nWarnings:")
                for warning in validation.warnings:
                    print(f"  - {warning}")
            
            print(f"\nMetrics:")
            for metric, value in validation.metrics.items():
                print(f"  {metric}: {value:.2f}")
        else:
            print(f"\nERROR: {response.get('error')}")


def test_batch_generation():
    """Test batch answer generation"""
    print("\n" + "="*80)
    print("TEST 4: BATCH GENERATION")
    print("="*80)
    
    generator = AnswerGenerator(llm_provider="groq", persist_directory="./data/chromadb")
    
    queries = [
        "What does Astha specialize in?",
        "How can I reach Astha?",
        "Where is Astha located?",
        "What are Astha's office hours?",
        "Tell me about Astha's services"
    ]
    
    print(f"\nGenerating answers for {len(queries)} queries...")
    
    responses = generator.batch_generate(queries, template_name='concise', n_results=3)
    
    for i, response in enumerate(responses, 1):
        print(f"\n{'='*80}")
        print(f"[{i}] {response['query']}")
        print("-"*80)
        print(response.get('answer', f"ERROR: {response.get('error')}"))


def test_quality_metrics():
    """Test quality metrics and validation"""
    print("\n" + "="*80)
    print("TEST 5: QUALITY METRICS")
    print("="*80)
    
    generator = AnswerGenerator(llm_provider="groq", persist_directory="./data/chromadb")
    validator = AnswerValidator()
    
    queries = [
        "What are the specializations of Astha?",
        "How can I contact Astha?",
        "What are the office timings?",
        "Where does Astha operate?",
        "What is Astha's social media?"
    ]
    
    # Generate answers
    responses = generator.batch_generate(queries, n_results=5)
    
    # Validate all answers
    validations = validator.validate_batch(responses)
    
    # Get quality report
    report = validator.get_quality_report(validations)
    
    print("\n--- QUALITY REPORT ---")
    print(f"Total Answers: {report['total_answers']}")
    print(f"Valid Answers: {report['valid_answers']}")
    print(f"Validity Rate: {report['validity_rate']:.2%}")
    print(f"Average Confidence: {report['average_confidence']:.2%}")
    print(f"Total Issues: {report['total_issues']}")
    print(f"Total Warnings: {report['total_warnings']}")
    
    if report.get('common_issues'):
        print(f"\nCommon Issues:")
        for item in report['common_issues']:
            print(f"  - {item['item']} ({item['count']}x)")
    
    if report.get('common_warnings'):
        print(f"\nCommon Warnings:")
        for item in report['common_warnings']:
            print(f"  - {item['item']} ({item['count']}x)")
    
    # Show individual results
    print(f"\n--- INDIVIDUAL RESULTS ---")
    for i, (response, validation) in enumerate(zip(responses, validations), 1):
        print(f"\n[{i}] {response['query']}")
        print(f"    Valid: {validation.is_valid} | Confidence: {validation.confidence_score:.2%}")
        if validation.issues:
            print(f"    Issues: {', '.join(validation.issues)}")


def test_different_providers():
    """Test different LLM providers"""
    print("\n" + "="*80)
    print("TEST 6: DIFFERENT LLM PROVIDERS")
    print("="*80)
    
    query = "What are Astha's specializations?"
    
    # Try available providers
    providers = [
        ('groq', 'llama3-8b-8192'),
        # ('openai', 'gpt-3.5-turbo'),  # Uncomment if API key available
        # ('gemini', 'gemini-pro')  # Uncomment if API key available
    ]
    
    for provider, model in providers:
        print(f"\n{'='*80}")
        print(f"PROVIDER: {provider.upper()} - {model}")
        print("="*80)
        
        try:
            generator = AnswerGenerator(
                llm_provider=provider,
                llm_model=model,
                persist_directory="./data/chromadb"
            )
            
            response = generator.generate_answer(query, n_results=3)
            
            print(f"\nQuestion: {query}")
            print(f"\nAnswer:\n{response.get('answer', 'ERROR: No answer')}")
            
            metadata = response.get('metadata', {})
            print(f"\nProvider: {metadata.get('llm_provider')}")
            print(f"Model: {metadata.get('llm_model')}")
            print(f"Tokens: {metadata.get('tokens_used', 0)}")
            print(f"Time: {metadata.get('response_time_seconds', 0):.2f}s")
            
        except Exception as e:
            print(f"\nERROR with {provider}: {e}")


def test_comprehensive():
    """Comprehensive test with various question types"""
    print("\n" + "="*80)
    print("TEST 7: COMPREHENSIVE QUESTION TYPES")
    print("="*80)
    
    generator = AnswerGenerator(llm_provider="groq", persist_directory="./data/chromadb")
    
    test_cases = [
        {
            'query': "What types of properties does Astha develop?",
            'category': 'Specialization'
        },
        {
            'query': "What is the phone number for Astha?",
            'category': 'Contact - Specific'
        },
        {
            'query': "How can I reach Astha's Bandel branch?",
            'category': 'Contact - Branch'
        },
        {
            'query': "When is Astha's office open?",
            'category': 'Timing'
        },
        {
            'query': "Which cities does Astha serve?",
            'category': 'Location'
        },
        {
            'query': "Give me a brief overview of Astha company",
            'category': 'General'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*80}")
        print(f"Category: {test_case['category']}")
        print(f"Query: {test_case['query']}")
        print("-"*80)
        
        response = generator.generate_answer(
            test_case['query'],
            n_results=5,
            template_name='default'
        )
        
        print(f"\nAnswer:\n{response.get('answer', 'ERROR')}")
        
        metadata = response.get('metadata', {})
        print(f"\nMetadata:")
        print(f"  Query Type: {metadata.get('query_type')}")
        print(f"  Sources: {metadata.get('num_sources')}")
        print(f"  Tokens: {metadata.get('tokens_used')}")
        print(f"  Time: {metadata.get('response_time_seconds', 0):.2f}s")


def test_statistics():
    """Test pipeline statistics"""
    print("\n" + "="*80)
    print("TEST 8: PIPELINE STATISTICS")
    print("="*80)
    
    generator = AnswerGenerator(llm_provider="groq", persist_directory="./data/chromadb")
    
    # Generate some answers
    queries = [
        "What does Astha do?",
        "How to contact Astha?",
        "Where is Astha?"
    ]
    
    for query in queries:
        generator.generate_answer(query, n_results=3)
    
    # Get statistics
    stats = generator.get_pipeline_stats()
    
    print("\n--- GENERATOR STATISTICS ---")
    gen_stats = stats['generator_stats']
    print(f"Total Queries: {gen_stats['total_queries']}")
    print(f"Successful: {gen_stats['successful_answers']}")
    print(f"Failed: {gen_stats['failed_answers']}")
    print(f"Average Response Time: {gen_stats['average_response_time']:.2f}s")
    print(f"Total Tokens: {gen_stats['total_tokens']}")
    
    print("\n--- LLM STATISTICS ---")
    llm_stats = stats['llm_stats']
    print(f"Provider: {llm_stats['provider']}")
    print(f"Model: {llm_stats['model']}")
    print(f"Total Requests: {llm_stats['total_requests']}")
    print(f"Success Rate: {llm_stats['success_rate']:.2%}")


def interactive_mode():
    """Interactive question-answering mode"""
    print("\n" + "="*80)
    print("INTERACTIVE Q&A MODE")
    print("="*80)
    print("Ask questions about Astha. Type 'quit' to exit.")
    print("Commands:")
    print("  /concise <question> - Get concise answer")
    print("  /detailed <question> - Get detailed answer")
    print("  /validate - Show validation metrics")
    print("  /stats - Show pipeline statistics")
    print("="*80)
    
    generator = AnswerGenerator(llm_provider="groq", persist_directory="./data/chromadb")
    validator = AnswerValidator()
    show_validation = False
    
    while True:
        try:
            query = input("\n> ").strip()
            
            if not query:
                continue
            
            if query.lower() == 'quit':
                break
            
            if query.startswith('/stats'):
                stats = generator.get_pipeline_stats()
                print(f"\nQueries: {stats['generator_stats']['total_queries']}")
                print(f"Success Rate: {stats['llm_stats']['success_rate']:.2%}")
                continue
            
            if query.startswith('/validate'):
                show_validation = not show_validation
                print(f"\nValidation display: {'ON' if show_validation else 'OFF'}")
                continue
            
            # Determine template
            template = 'default'
            if query.startswith('/concise '):
                query = query[9:]
                template = 'concise'
            elif query.startswith('/detailed '):
                query = query[10:]
                template = 'detailed'
            
            # Generate answer
            response = generator.generate_answer(
                query=query,
                template_name=template,
                n_results=5
            )
            
            print(f"\n{'='*80}")
            print(f"Answer:\n{response.get('answer', 'ERROR')}")
            
            # Show validation if enabled
            if show_validation and response.get('answer'):
                validation = validator.validate(
                    answer=response['answer'],
                    query=query,
                    context_results=response.get('retrieval_results', [])
                )
                
                print(f"\n--- VALIDATION ---")
                print(f"Valid: {validation.is_valid}")
                print(f"Confidence: {validation.confidence_score:.2%}")
                if validation.issues:
                    print(f"Issues: {', '.join(validation.issues)}")
            
            print("="*80)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
    
    print("\n\nGoodbye!")


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("PROPINTEL ANSWER GENERATION TEST SUITE")
    print("="*80)
    
    # Load environment
    config = get_config()
    logger.info("Environment configuration loaded")
    
    tests = [
        ("Basic Generation", test_basic_generation),
        ("Different Templates", test_different_templates),
        ("Answer Validation", test_answer_validation),
        ("Batch Generation", test_batch_generation),
        ("Quality Metrics", test_quality_metrics),
        ("Different Providers", test_different_providers),
        ("Comprehensive Types", test_comprehensive),
        ("Statistics", test_statistics)
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


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test PropIntel Answer Generation")
    parser.add_argument(
        '--mode',
        choices=['all', 'interactive', 'basic', 'templates', 'validation', 'batch', 'quality', 'providers', 'comprehensive', 'stats'],
        default='all',
        help='Test mode to run'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'interactive':
        interactive_mode()
    elif args.mode == 'all':
        run_all_tests()
    elif args.mode == 'basic':
        test_basic_generation()
    elif args.mode == 'templates':
        test_different_templates()
    elif args.mode == 'validation':
        test_answer_validation()
    elif args.mode == 'batch':
        test_batch_generation()
    elif args.mode == 'quality':
        test_quality_metrics()
    elif args.mode == 'providers':
        test_different_providers()
    elif args.mode == 'comprehensive':
        test_comprehensive()
    elif args.mode == 'stats':
        test_statistics()
