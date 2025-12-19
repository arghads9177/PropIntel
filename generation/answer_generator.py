"""
Answer Generator for PropIntel

This module coordinates the complete answer generation pipeline:
1. Retrieve relevant context
2. Format prompts
3. Generate answers with LLM
4. Validate and post-process
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from retrieval.retrieval_orchestrator import RetrievalOrchestrator
from generation.llm_service import LLMService
from generation.prompt_manager import PromptManager


class AnswerGenerator:
    """
    Complete answer generation pipeline.
    
    Workflow:
    1. Retrieve context from vector DB
    2. Build optimized prompt
    3. Generate answer with LLM
    4. Post-process and format
    5. Track quality metrics
    """
    
    def __init__(
        self,
        retrieval_orchestrator: Optional[RetrievalOrchestrator] = None,
        llm_service: Optional[LLMService] = None,
        prompt_manager: Optional[PromptManager] = None,
        llm_provider: str = "openai",  # Primary: OpenAI, falls back to Groq, then Gemini
        llm_model: Optional[str] = None,
        persist_directory: Optional[str] = None
    ):
        """
        Initialize answer generator.
        
        Args:
            retrieval_orchestrator: Retrieval orchestrator instance
            llm_service: LLM service instance
            prompt_manager: Prompt manager instance
            llm_provider: LLM provider if creating new service
            llm_model: LLM model if creating new service
            persist_directory: ChromaDB directory
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.retrieval_orchestrator = retrieval_orchestrator or RetrievalOrchestrator(
            persist_directory=persist_directory or "./data/chromadb"
        )
        
        self.llm_service = llm_service or LLMService(
            provider=llm_provider,
            model=llm_model
        )
        
        self.prompt_manager = prompt_manager or PromptManager()
        
        # Track statistics
        self.stats = {
            'total_queries': 0,
            'successful_answers': 0,
            'failed_answers': 0,
            'average_response_time': 0.0,
            'total_tokens': 0
        }
        
        self.logger.info("AnswerGenerator initialized")
    
    def generate_answer(
        self,
        query: str,
        n_results: int = 5,
        template_name: str = 'default',
        ranking_strategy: str = 'hybrid',
        use_query_expansion: bool = True,
        temperature: float = 0.3,
        max_tokens: int = 500,
        include_sources: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate answer for user query.
        
        Args:
            query: User query
            n_results: Number of retrieval results
            template_name: Prompt template to use
            ranking_strategy: Retrieval ranking strategy
            use_query_expansion: Whether to expand query
            temperature: LLM temperature
            max_tokens: Maximum tokens in answer
            include_sources: Whether to include source citations
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with answer and metadata
        """
        self.logger.info(f"Generating answer for: '{query}'")
        start_time = datetime.now()
        
        self.stats['total_queries'] += 1
        
        try:
            # Step 1: Retrieve context
            retrieval_response = self.retrieval_orchestrator.retrieve(
                query=query,
                n_results=n_results,
                ranking_strategy=ranking_strategy,
                use_query_expansion=use_query_expansion,
                **kwargs
            )
            
            results = retrieval_response['results']
            
            if not results:
                return self._create_no_context_response(query, retrieval_response)
            
            # Step 2: Build prompt
            prompts = self.prompt_manager.build_prompt(
                query=query,
                results=results,
                template_name=template_name,
                max_context_length=2000,
                include_metadata=True
            )
            
            # Step 3: Generate answer
            llm_response = self.llm_service.generate(
                prompt=prompts['user_prompt'],
                system_prompt=prompts['system_prompt'],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Check for LLM errors
            if not llm_response.get('answer'):
                return self._create_error_response(
                    query,
                    llm_response.get('error', 'LLM failed to generate answer'),
                    retrieval_response
                )
            
            # Step 4: Post-process and format
            answer = llm_response['answer']
            
            # Add source citations if requested
            if include_sources:
                sources = self._format_sources(results)
            else:
                sources = []
            
            # Calculate metrics
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            
            # Update statistics
            self.stats['successful_answers'] += 1
            self.stats['total_tokens'] += llm_response.get('tokens_used', 0)
            self._update_average_response_time(response_time)
            
            # Build response
            response = {
                'query': query,
                'answer': answer,
                'sources': sources,
                'metadata': {
                    'num_sources': len(results),
                    'retrieval_strategy': ranking_strategy,
                    'template_used': template_name,
                    'llm_provider': llm_response.get('provider'),
                    'llm_model': llm_response.get('model'),
                    'tokens_used': llm_response.get('tokens_used', 0),
                    'response_time_seconds': response_time,
                    'timestamp': datetime.now().isoformat(),
                    'query_type': retrieval_response.get('processed_query', {}).get('query_type'),
                    'expansion_used': use_query_expansion
                },
                'retrieval_results': results  # Include for transparency
            }
            
            self.logger.info(f"Answer generated successfully in {response_time:.2f}s")
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating answer: {e}")
            self.stats['failed_answers'] += 1
            
            return {
                'query': query,
                'answer': None,
                'error': str(e),
                'sources': [],
                'metadata': {
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    def generate_answer_simple(
        self,
        query: str,
        **kwargs
    ) -> str:
        """
        Generate answer and return just the text.
        
        Args:
            query: User query
            **kwargs: Additional parameters
            
        Returns:
            Answer text or error message
        """
        response = self.generate_answer(query, **kwargs)
        
        if response.get('answer'):
            return response['answer']
        else:
            error = response.get('error', 'Failed to generate answer')
            return f"I'm sorry, I couldn't generate an answer. Error: {error}"
    
    def generate_conversational(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate answer with conversational template.
        
        Args:
            query: User query
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary
        """
        return self.generate_answer(
            query=query,
            template_name='conversational',
            **kwargs
        )
    
    def generate_detailed(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate detailed answer.
        
        Args:
            query: User query
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary
        """
        return self.generate_answer(
            query=query,
            template_name='detailed',
            n_results=7,
            max_tokens=800,
            **kwargs
        )
    
    def generate_concise(
        self,
        query: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate concise answer.
        
        Args:
            query: User query
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary
        """
        return self.generate_answer(
            query=query,
            template_name='concise',
            n_results=3,
            max_tokens=200,
            **kwargs
        )
    
    def batch_generate(
        self,
        queries: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate answers for multiple queries.
        
        Args:
            queries: List of queries
            **kwargs: Parameters for generate_answer
            
        Returns:
            List of response dictionaries
        """
        self.logger.info(f"Batch generating {len(queries)} answers")
        
        responses = []
        for query in queries:
            response = self.generate_answer(query, **kwargs)
            responses.append(response)
        
        return responses
    
    def _create_no_context_response(
        self,
        query: str,
        retrieval_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create response when no context is found"""
        return {
            'query': query,
            'answer': "I don't have enough information to answer that question. The query didn't return any relevant results from the database.",
            'sources': [],
            'metadata': {
                'num_sources': 0,
                'retrieval_response': retrieval_response.get('metadata', {}),
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _create_error_response(
        self,
        query: str,
        error: str,
        retrieval_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create error response"""
        self.stats['failed_answers'] += 1
        
        return {
            'query': query,
            'answer': None,
            'error': error,
            'sources': [],
            'metadata': {
                'num_sources': len(retrieval_response.get('results', [])),
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def _format_sources(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Format source citations"""
        sources = []
        
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            
            source = {
                'id': i,
                'section': metadata.get('section', 'Unknown'),
                'subsection': metadata.get('subsection', ''),
                'score': result.get('final_score', result.get('score', 0)),
                'preview': result.get('content', '')[:100] + '...'
            }
            
            sources.append(source)
        
        return sources
    
    def _update_average_response_time(self, new_time: float):
        """Update running average of response time"""
        n = self.stats['successful_answers']
        current_avg = self.stats['average_response_time']
        
        # Incremental average formula
        self.stats['average_response_time'] = (
            current_avg * (n - 1) + new_time
        ) / n
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        return {
            'generator_stats': self.stats.copy(),
            'retrieval_stats': self.retrieval_orchestrator.get_pipeline_stats(),
            'llm_stats': self.llm_service.get_stats(),
            'prompt_stats': self.prompt_manager.get_stats()
        }
    
    def print_answer(
        self,
        response: Dict[str, Any],
        show_sources: bool = True,
        show_metadata: bool = True
    ):
        """
        Print formatted answer.
        
        Args:
            response: Response dictionary
            show_sources: Whether to show sources
            show_metadata: Whether to show metadata
        """
        print("\n" + "="*80)
        print(f"Question: {response['query']}")
        print("="*80)
        
        if response.get('answer'):
            print(f"\nAnswer:\n{response['answer']}")
        else:
            print(f"\nError: {response.get('error', 'Unknown error')}")
            return
        
        if show_sources and response.get('sources'):
            print("\n" + "-"*80)
            print("Sources:")
            for source in response['sources']:
                print(f"\n[{source['id']}] {source['section']}/{source['subsection']}")
                print(f"    Score: {source['score']:.4f}")
                print(f"    Preview: {source['preview']}")
        
        if show_metadata and response.get('metadata'):
            metadata = response['metadata']
            print("\n" + "-"*80)
            print("Metadata:")
            print(f"  Provider: {metadata.get('llm_provider')} - {metadata.get('llm_model')}")
            print(f"  Sources Used: {metadata.get('num_sources')}")
            print(f"  Tokens: {metadata.get('tokens_used')}")
            print(f"  Response Time: {metadata.get('response_time_seconds', 0):.2f}s")
            print(f"  Query Type: {metadata.get('query_type')}")
        
        print("\n" + "="*80)
