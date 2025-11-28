"""
Test script for prompt effectiveness with project queries.

Tests the full RAG pipeline with enhanced prompts for project information.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from retrieval.collection_router import CollectionRouter
from retrieval.retriever import RetrieverService
from retrieval.query_processor import QueryProcessor
from generation.prompt_manager import PromptManager
from generation.llm_service import LLMService


def test_project_queries():
    """Test project-focused queries with enhanced prompts"""
    print("=" * 80)
    print("Test: Project Query RAG Pipeline")
    print("=" * 80)
    
    # Initialize components
    router = CollectionRouter()
    retriever = RetrieverService(collection_name="propintel_knowledge")
    query_processor = QueryProcessor()
    prompt_manager = PromptManager()
    llm_service = LLMService(provider='groq')
    
    test_queries = [
        ("Tell me about Kabi Tirtha project", "default"),
        ("How many floors does Kabi Tirtha have?", "project"),
        ("What upcoming projects are there?", "default"),
        ("List all running projects", "default"),
        ("How many floors in Tower 1 of Urban Residency?", "project"),
    ]
    
    for query, template in test_queries:
        print(f"\n{'─' * 80}")
        print(f"Query: {query}")
        print(f"Template: {template}")
        print(f"{'─' * 80}")
        
        try:
            # Step 1: Route to collection
            routing = router.route_with_confidence(query)
            print(f"Routed to: {routing['collection']} (confidence: {routing['confidence']:.2f})")
            
            # Step 2: Switch collection if needed
            current = retriever.get_current_collection()
            if current != routing['collection']:
                retriever.switch_collection(routing['collection'])
            
            # Step 3: Process query for filters
            query_info = query_processor.process(query)
            filters = query_info.get('suggested_filters')
            
            if filters:
                print(f"Filters: {filters}")
            
            # Step 4: Retrieve context
            results = retriever.retrieve(
                query=query,
                n_results=5,
                filters=filters
            )
            
            if not results:
                print("No results found!")
                continue
            
            print(f"Retrieved: {len(results)} results")
            
            # Step 5: Build prompt
            context_docs = []
            for r in results:
                context_docs.append({
                    'content': r.content,
                    'metadata': r.metadata,
                    'score': r.score
                })
            
            prompt_data = prompt_manager.build_prompt(
                query=query,
                results=context_docs,
                template_name=template
            )
            
            # Step 6: Generate answer
            answer_response = llm_service.generate(
                prompt=prompt_data['user_prompt'],
                system_prompt=prompt_data['system_prompt'],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = answer_response.get('answer', 'No response generated')
            
            # Display answer
            print(f"\nAnswer:\n{answer}")
            
            # Show sources
            print(f"\nSources used: {len(results)}")
            for i, r in enumerate(results[:3], 1):
                metadata = r.metadata
                chunk_type = metadata.get('chunk_type', metadata.get('section', 'N/A'))
                project_name = metadata.get('project_name', metadata.get('company_id', 'N/A'))
                print(f"  [{i}] {project_name} - {chunk_type}")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


def test_company_queries():
    """Test that company queries still work correctly"""
    print("\n\n" + "=" * 80)
    print("Test: Company Query RAG Pipeline")
    print("=" * 80)
    
    # Initialize components
    router = CollectionRouter()
    retriever = RetrieverService(collection_name="propintel_companies")
    query_processor = QueryProcessor()
    prompt_manager = PromptManager()
    llm_service = LLMService(provider='groq')
    
    test_queries = [
        "What does Astha Infra Realty specialize in?",
        "Who are the key people at Poddar Housing?"
    ]
    
    for query in test_queries:
        print(f"\n{'─' * 80}")
        print(f"Query: {query}")
        print(f"{'─' * 80}")
        
        try:
            # Route and retrieve
            routing = router.route_with_confidence(query)
            print(f"Routed to: {routing['collection']} (confidence: {routing['confidence']:.2f})")
            
            current = retriever.get_current_collection()
            if current != routing['collection']:
                retriever.switch_collection(routing['collection'])
            
            results = retriever.retrieve(query=query, n_results=3)
            
            if not results:
                print("No results found!")
                continue
            
            print(f"Retrieved: {len(results)} results")
            
            # Build prompt and generate
            context_docs = [{'content': r.content, 'metadata': r.metadata, 'score': r.score} for r in results]
            query_info = query_processor.process(query)
            
            prompt_data = prompt_manager.build_prompt(
                query=query,
                results=context_docs,
                template_name='default'
            )
            
            answer_response = llm_service.generate(
                prompt=prompt_data['user_prompt'],
                system_prompt=prompt_data['system_prompt'],
                temperature=0.3,
                max_tokens=500
            )
            
            answer = answer_response.get('answer', 'No response generated')
            
            print(f"\nAnswer:\n{answer}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


def test_prompt_formatting():
    """Test that prompt formatting works correctly with different templates"""
    print("\n\n" + "=" * 80)
    print("Test: Prompt Formatting")
    print("=" * 80)
    
    # Initialize components
    retriever = RetrieverService(collection_name="propintel_knowledge")
    prompt_manager = PromptManager()
    
    # Get some sample results
    query = "How many floors does Kabi Tirtha have?"
    results = retriever.retrieve(query=query, n_results=3)
    
    context_docs = [{'content': r.content, 'metadata': r.metadata, 'score': r.score} for r in results]
    
    templates = ['default', 'project', 'detailed']
    
    for template in templates:
        print(f"\n{'─' * 80}")
        print(f"Template: {template}")
        print(f"{'─' * 80}")
        
        prompt_data = prompt_manager.build_prompt(
            query=query,
            results=context_docs,
            template_name=template
        )
        
        print(f"\nSystem Prompt (first 200 chars):")
        print(prompt_data['system_prompt'][:200] + "...")
        
        print(f"\nUser Prompt (first 400 chars):")
        print(prompt_data['user_prompt'][:400] + "...")


if __name__ == "__main__":
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "PROMPT EFFECTIVENESS TEST SUITE" + " " * 27 + "║")
    print("╚" + "═" * 78 + "╝")
    print("\n")
    
    # Run tests
    test_prompt_formatting()
    test_project_queries()
    test_company_queries()
    
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)
