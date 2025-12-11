"""
Retrieval Orchestrator for PropIntel

This module orchestrates the complete retrieval pipeline, coordinating
query processing, retrieval, and ranking to provide high-quality results.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from retrieval.retriever import RetrieverService, RetrievalResult
from retrieval.query_processor import QueryProcessor
from retrieval.result_ranker import ResultRanker, RankedResult
from retrieval.collection_router import CollectionRouter


class RetrievalOrchestrator:
    """
    Orchestrate the complete retrieval pipeline.
    
    Pipeline:
    1. Process query (clean, expand, detect type)
    2. Retrieve relevant documents
    3. Rank and re-rank results
    4. Format and return
    """
    
    def __init__(
        self,
        retriever: Optional[RetrieverService] = None,
        query_processor: Optional[QueryProcessor] = None,
        ranker: Optional[ResultRanker] = None,
        collection_router: Optional[CollectionRouter] = None,
        collection_name: str = "propintel_companies",
        persist_directory: Optional[str] = None,
        auto_route: bool = True
    ):
        """
        Initialize the retrieval orchestrator.
        
        Args:
            retriever: RetrieverService instance (creates new if None)
            query_processor: QueryProcessor instance (creates new if None)
            ranker: ResultRanker instance (creates new if None)
            collection_router: CollectionRouter instance (creates new if None)
            collection_name: ChromaDB collection name (default if auto_route is False)
            persist_directory: ChromaDB persistence directory
            auto_route: Whether to automatically route queries to correct collection
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.retriever = retriever or RetrieverService(
            collection_name=collection_name,
            persist_directory=persist_directory
        )
        self.query_processor = query_processor or QueryProcessor()
        self.ranker = ranker or ResultRanker()
        self.collection_router = collection_router or CollectionRouter()
        self.auto_route = auto_route
        
        # Track statistics
        self.stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_results_returned': 0,
            'average_results_per_query': 0.0
        }
        
        self.logger.info("RetrievalOrchestrator initialized")
    
    def retrieve(
        self,
        query: str,
        n_results: int = 5,
        use_query_expansion: bool = True,
        use_multi_query: bool = False,
        ranking_strategy: str = 'hybrid',
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Complete retrieval pipeline.
        
        Args:
            query: User query
            n_results: Number of results to return
            use_query_expansion: Whether to use query expansion
            use_multi_query: Whether to use multi-query retrieval
            ranking_strategy: Ranking strategy ('relevance', 'diversity', 'coverage', 'mmr', 'hybrid')
            filters: Optional metadata filters
            **kwargs: Additional parameters for ranking
            
        Returns:
            Dictionary with results and metadata
        """
        self.logger.info(f"Processing query: '{query}'")
        start_time = datetime.now()
        
        self.stats['total_queries'] += 1
        
        try:
            # Step 0: Auto-route to correct collection if enabled
            routing_info = None
            if self.auto_route:
                routing_info = self.collection_router.route_with_confidence(query)
                target_collection = routing_info['collection']
                
                # Switch collection if different from current
                current_collection = self.retriever.get_current_collection()
                if current_collection != target_collection:
                    self.logger.info(f"Auto-routing from '{current_collection}' to '{target_collection}' (confidence: {routing_info['confidence']:.2%})")
                    self.retriever.switch_collection(target_collection)
            
            # Step 1: Process query
            processed_query = self.query_processor.process(
                query,
                expand=use_query_expansion,
                clean=True
            )
            
            # Merge filters with suggested filters
            combined_filters = filters or {}
            if processed_query['filters']:
                combined_filters.update(processed_query['filters'])
            
            # Step 2: Retrieve documents
            if use_multi_query and processed_query['expanded_queries']:
                # Multi-query retrieval
                queries = [processed_query['cleaned']] + processed_query['expanded_queries']
                retrieval_results = self.retriever.retrieve_multi_query(
                    queries=queries[:3],  # Limit to 3 queries
                    n_results_per_query=n_results,
                    filters=combined_filters if combined_filters else None,
                    deduplicate=True
                )
            else:
                # Single query retrieval
                retrieval_results = self.retriever.retrieve(
                    query=processed_query['cleaned'],
                    n_results=n_results * 2,  # Get more for better ranking
                    filters=combined_filters if combined_filters else None
                )
            
            # Step 3: Rank results
            ranked_results = self.ranker.rank(
                results=retrieval_results,
                query=query,
                strategy=ranking_strategy,
                **kwargs
            )
            
            # Step 4: Filter and limit results
            final_results = self.ranker.filter_results(
                results=ranked_results,
                max_results=n_results,
                min_score=0.1  # Minimum relevance threshold
            )
            
            # Update statistics
            self.stats['successful_queries'] += 1
            self.stats['total_results_returned'] += len(final_results)
            self.stats['average_results_per_query'] = (
                self.stats['total_results_returned'] / self.stats['successful_queries']
            )
            
            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Format response
            response = {
                'query': query,
                'processed_query': processed_query,
                'results': [r.to_dict() for r in final_results],
                'num_results': len(final_results),
                'metadata': {
                    'query_type': processed_query['query_type'],
                    'expansion_used': use_query_expansion,
                    'multi_query_used': use_multi_query,
                    'ranking_strategy': ranking_strategy,
                    'filters_applied': combined_filters,
                    'duration_seconds': duration,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Add routing info if auto-routing was used
            if routing_info:
                response['metadata']['collection'] = routing_info['collection']
                response['metadata']['routing_confidence'] = routing_info['confidence']
            
            self.logger.info(f"Retrieved {len(final_results)} results in {duration:.2f}s")
            return response
            
        except Exception as e:
            self.logger.error(f"Error during retrieval: {e}")
            self.stats['failed_queries'] += 1
            
            return {
                'query': query,
                'results': [],
                'num_results': 0,
                'error': str(e),
                'metadata': {
                    'timestamp': datetime.now().isoformat()
                }
            }
    
    def retrieve_simple(
        self,
        query: str,
        n_results: int = 5
    ) -> List[RankedResult]:
        """
        Simple retrieval without advanced features.
        
        Args:
            query: User query
            n_results: Number of results to return
            
        Returns:
            List of ranked results
        """
        response = self.retrieve(
            query=query,
            n_results=n_results,
            use_query_expansion=False,
            use_multi_query=False,
            ranking_strategy='relevance'
        )
        
        # Convert back to RankedResult objects
        results = []
        for result_dict in response['results']:
            # This is a simplified conversion
            # In practice, you might want to reconstruct full objects
            results.append(result_dict)
        
        return results
    
    def retrieve_advanced(
        self,
        query: str,
        n_results: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Advanced retrieval with all features enabled.
        
        Args:
            query: User query
            n_results: Number of results to return
            **kwargs: Additional parameters
            
        Returns:
            Complete response dictionary
        """
        return self.retrieve(
            query=query,
            n_results=n_results,
            use_query_expansion=True,
            use_multi_query=True,
            ranking_strategy='hybrid',
            **kwargs
        )
    
    def retrieve_by_type(
        self,
        query: str,
        query_type: str,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve based on explicit query type.
        
        Args:
            query: User query
            query_type: Query type ('specialization', 'contact', 'location', 'about', etc.)
            n_results: Number of results to return
            
        Returns:
            Response dictionary
        """
        # Map query types to sections
        section_map = {
            'specialization': 'company_info',
            'location': 'company_info',
            'about': 'company_info',
            'contact': 'contact_details',
            'timing': 'contact_details',
            'social': 'social_media'
        }
        
        filters = {}
        if query_type in section_map:
            filters['section'] = section_map[query_type]
        
        return self.retrieve(
            query=query,
            n_results=n_results,
            filters=filters,
            ranking_strategy='relevance'
        )
    
    def batch_retrieve(
        self,
        queries: List[str],
        n_results: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Process multiple queries in batch.
        
        Args:
            queries: List of queries
            n_results: Number of results per query
            **kwargs: Additional parameters for retrieve()
            
        Returns:
            List of response dictionaries
        """
        self.logger.info(f"Batch processing {len(queries)} queries")
        
        responses = []
        for query in queries:
            response = self.retrieve(
                query=query,
                n_results=n_results,
                **kwargs
            )
            responses.append(response)
        
        return responses
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        
        return {
            'orchestrator_stats': self.stats.copy(),
            'retriever_stats': self.retriever.get_stats(),
            'query_processor_stats': self.query_processor.get_stats(),
            'ranker_stats': self.ranker.get_stats()
        }
    
    def print_results(
        self,
        response: Dict[str, Any],
        show_metadata: bool = True,
        max_content_length: int = 200
    ):
        """
        Print formatted results.
        
        Args:
            response: Response dictionary from retrieve()
            show_metadata: Whether to show metadata
            max_content_length: Maximum content length to display
        """
        print("\n" + "="*80)
        print(f"Query: {response['query']}")
        print("="*80)
        
        if show_metadata:
            metadata = response['metadata']
            print(f"\nQuery Type: {metadata.get('query_type', 'N/A')}")
            print(f"Strategy: {metadata.get('ranking_strategy', 'N/A')}")
            print(f"Duration: {metadata.get('duration_seconds', 0):.2f}s")
            print(f"Results: {response['num_results']}")
        
        print("\n" + "-"*80)
        print("RESULTS")
        print("-"*80)
        
        for i, result in enumerate(response['results'], 1):
            print(f"\n[{i}] Score: {result.get('final_score', result.get('score', 0)):.4f}")
            print(f"    Section: {result['metadata'].get('section', 'N/A')}")
            
            if result['metadata'].get('subsection'):
                print(f"    Subsection: {result['metadata'].get('subsection')}")
            
            content = result['content']
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            print(f"    Content: {content}")
        
        print("\n" + "="*80)
