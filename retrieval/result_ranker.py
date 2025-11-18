"""
Result Ranker for PropIntel

This module provides advanced re-ranking algorithms to improve
the quality and relevance of retrieval results. Includes various
ranking strategies and result processing.
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
import re

from retrieval.retriever import RetrievalResult


@dataclass
class RankedResult:
    """Represents a ranked retrieval result with additional scoring"""
    
    retrieval_result: RetrievalResult
    relevance_score: float = 0.0
    diversity_score: float = 0.0
    coverage_score: float = 0.0
    final_score: float = 0.0
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            **self.retrieval_result.to_dict(),
            'relevance_score': self.relevance_score,
            'diversity_score': self.diversity_score,
            'coverage_score': self.coverage_score,
            'final_score': self.final_score,
            'rank': self.rank
        }


class ResultRanker:
    """
    Advanced result ranking and re-ranking.
    
    Features:
    - Relevance-based ranking
    - Diversity-aware ranking
    - Query coverage ranking
    - MMR (Maximal Marginal Relevance)
    - Custom ranking functions
    """
    
    def __init__(self):
        """Initialize the result ranker"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("ResultRanker initialized")
    
    def rank(
        self,
        results: List[RetrievalResult],
        query: str,
        strategy: str = 'relevance',
        **kwargs
    ) -> List[RankedResult]:
        """
        Rank results using specified strategy.
        
        Args:
            results: List of retrieval results
            query: Original query
            strategy: Ranking strategy ('relevance', 'diversity', 'coverage', 'mmr', 'hybrid')
            **kwargs: Additional parameters for ranking strategies
            
        Returns:
            List of ranked results sorted by final score
        """
        self.logger.info(f"Ranking {len(results)} results using strategy: {strategy}")
        
        if not results:
            return []
        
        # Convert to RankedResult objects
        ranked_results = [
            RankedResult(retrieval_result=r) for r in results
        ]
        
        # Apply ranking strategy
        if strategy == 'relevance':
            ranked_results = self._rank_by_relevance(ranked_results)
        
        elif strategy == 'diversity':
            ranked_results = self._rank_by_diversity(ranked_results, query)
        
        elif strategy == 'coverage':
            ranked_results = self._rank_by_coverage(ranked_results, query)
        
        elif strategy == 'mmr':
            lambda_param = kwargs.get('lambda_param', 0.5)
            ranked_results = self._rank_by_mmr(ranked_results, query, lambda_param)
        
        elif strategy == 'hybrid':
            relevance_weight = kwargs.get('relevance_weight', 0.5)
            diversity_weight = kwargs.get('diversity_weight', 0.3)
            coverage_weight = kwargs.get('coverage_weight', 0.2)
            ranked_results = self._rank_hybrid(
                ranked_results, query,
                relevance_weight, diversity_weight, coverage_weight
            )
        
        else:
            self.logger.warning(f"Unknown strategy: {strategy}, using relevance")
            ranked_results = self._rank_by_relevance(ranked_results)
        
        # Assign ranks
        for i, result in enumerate(ranked_results):
            result.rank = i + 1
        
        self.logger.info(f"Ranking complete: top score = {ranked_results[0].final_score:.4f}")
        return ranked_results
    
    def _rank_by_relevance(
        self,
        results: List[RankedResult]
    ) -> List[RankedResult]:
        """
        Rank by relevance score (original retrieval score).
        
        Args:
            results: List of ranked results
            
        Returns:
            Sorted list by relevance
        """
        for result in results:
            result.relevance_score = result.retrieval_result.score
            result.final_score = result.relevance_score
        
        # Sort by final score (descending)
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results
    
    def _rank_by_diversity(
        self,
        results: List[RankedResult],
        query: str
    ) -> List[RankedResult]:
        """
        Rank by diversity (prefer results from different sections/types).
        
        Args:
            results: List of ranked results
            query: Original query
            
        Returns:
            Sorted list promoting diversity
        """
        # Track seen sections and subsections
        seen_sections = set()
        seen_subsections = set()
        
        for result in results:
            metadata = result.retrieval_result.metadata
            section = metadata.get('section', 'unknown')
            subsection = metadata.get('subsection', 'unknown')
            
            # Calculate diversity score
            diversity_score = 1.0
            
            # Penalize if we've seen this section
            if section in seen_sections:
                diversity_score *= 0.7
            
            # Penalize more if we've seen this subsection
            if subsection in seen_subsections:
                diversity_score *= 0.5
            
            result.diversity_score = diversity_score
            result.relevance_score = result.retrieval_result.score
            
            # Combine relevance and diversity
            result.final_score = 0.6 * result.relevance_score + 0.4 * result.diversity_score
            
            # Update seen sets
            seen_sections.add(section)
            seen_subsections.add(subsection)
        
        # Sort by final score (descending)
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results
    
    def _rank_by_coverage(
        self,
        results: List[RankedResult],
        query: str
    ) -> List[RankedResult]:
        """
        Rank by query term coverage.
        
        Args:
            results: List of ranked results
            query: Original query
            
        Returns:
            Sorted list by coverage
        """
        # Extract query terms
        query_terms = set(query.lower().split())
        
        for result in results:
            content = result.retrieval_result.content.lower()
            
            # Calculate coverage (what fraction of query terms appear in result)
            matching_terms = sum(1 for term in query_terms if term in content)
            coverage_score = matching_terms / len(query_terms) if query_terms else 0.0
            
            result.coverage_score = coverage_score
            result.relevance_score = result.retrieval_result.score
            
            # Combine relevance and coverage
            result.final_score = 0.5 * result.relevance_score + 0.5 * result.coverage_score
        
        # Sort by final score (descending)
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results
    
    def _rank_by_mmr(
        self,
        results: List[RankedResult],
        query: str,
        lambda_param: float = 0.5
    ) -> List[RankedResult]:
        """
        Rank using Maximal Marginal Relevance (MMR).
        Balances relevance and diversity.
        
        Args:
            results: List of ranked results
            query: Original query
            lambda_param: Trade-off parameter (0=max diversity, 1=max relevance)
            
        Returns:
            Sorted list using MMR
        """
        if not results:
            return []
        
        # Initialize scores
        for result in results:
            result.relevance_score = result.retrieval_result.score
        
        # MMR selection
        selected = []
        remaining = results.copy()
        
        # Select first result (highest relevance)
        first = max(remaining, key=lambda x: x.relevance_score)
        selected.append(first)
        remaining.remove(first)
        
        # Iteratively select results
        while remaining:
            max_mmr_score = -float('inf')
            max_mmr_result = None
            
            for candidate in remaining:
                # Relevance score
                relevance = candidate.relevance_score
                
                # Diversity score (minimum similarity to selected results)
                max_similarity = max(
                    self._calculate_similarity(candidate, selected_result)
                    for selected_result in selected
                )
                diversity = 1.0 - max_similarity
                
                # MMR score
                mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
                
                if mmr_score > max_mmr_score:
                    max_mmr_score = mmr_score
                    max_mmr_result = candidate
            
            if max_mmr_result:
                max_mmr_result.diversity_score = 1.0 - max_similarity
                max_mmr_result.final_score = max_mmr_score
                selected.append(max_mmr_result)
                remaining.remove(max_mmr_result)
            else:
                break
        
        return selected
    
    def _rank_hybrid(
        self,
        results: List[RankedResult],
        query: str,
        relevance_weight: float = 0.5,
        diversity_weight: float = 0.3,
        coverage_weight: float = 0.2
    ) -> List[RankedResult]:
        """
        Hybrid ranking combining multiple signals.
        
        Args:
            results: List of ranked results
            query: Original query
            relevance_weight: Weight for relevance score
            diversity_weight: Weight for diversity score
            coverage_weight: Weight for coverage score
            
        Returns:
            Sorted list with hybrid scores
        """
        # Extract query terms
        query_terms = set(query.lower().split())
        
        # Track sections for diversity
        seen_sections = set()
        
        for result in results:
            # Relevance score
            result.relevance_score = result.retrieval_result.score
            
            # Coverage score
            content = result.retrieval_result.content.lower()
            matching_terms = sum(1 for term in query_terms if term in content)
            result.coverage_score = matching_terms / len(query_terms) if query_terms else 0.0
            
            # Diversity score
            section = result.retrieval_result.metadata.get('section', 'unknown')
            result.diversity_score = 0.5 if section in seen_sections else 1.0
            seen_sections.add(section)
            
            # Combine scores
            result.final_score = (
                relevance_weight * result.relevance_score +
                diversity_weight * result.diversity_score +
                coverage_weight * result.coverage_score
            )
        
        # Sort by final score (descending)
        results.sort(key=lambda x: x.final_score, reverse=True)
        return results
    
    def _calculate_similarity(
        self,
        result1: RankedResult,
        result2: RankedResult
    ) -> float:
        """
        Calculate similarity between two results.
        
        Args:
            result1: First result
            result2: Second result
            
        Returns:
            Similarity score (0-1)
        """
        # Simple similarity based on section and content overlap
        metadata1 = result1.retrieval_result.metadata
        metadata2 = result2.retrieval_result.metadata
        
        # Section similarity
        section_match = 1.0 if metadata1.get('section') == metadata2.get('section') else 0.0
        
        # Content similarity (Jaccard)
        content1_terms = set(result1.retrieval_result.content.lower().split())
        content2_terms = set(result2.retrieval_result.content.lower().split())
        
        intersection = content1_terms & content2_terms
        union = content1_terms | content2_terms
        
        content_similarity = len(intersection) / len(union) if union else 0.0
        
        # Combine
        return 0.3 * section_match + 0.7 * content_similarity
    
    def filter_results(
        self,
        results: List[RankedResult],
        min_score: float = 0.0,
        max_results: Optional[int] = None,
        required_sections: Optional[List[str]] = None
    ) -> List[RankedResult]:
        """
        Filter results based on criteria.
        
        Args:
            results: List of ranked results
            min_score: Minimum final score threshold
            max_results: Maximum number of results
            required_sections: List of required sections
            
        Returns:
            Filtered results
        """
        filtered = results
        
        # Filter by score
        if min_score > 0:
            filtered = [r for r in filtered if r.final_score >= min_score]
        
        # Filter by sections
        if required_sections:
            filtered = [
                r for r in filtered
                if r.retrieval_result.metadata.get('section') in required_sections
            ]
        
        # Limit results
        if max_results:
            filtered = filtered[:max_results]
        
        self.logger.info(f"Filtered {len(results)} → {len(filtered)} results")
        return filtered
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ranker statistics"""
        return {
            'supported_strategies': ['relevance', 'diversity', 'coverage', 'mmr', 'hybrid'],
            'default_strategy': 'relevance'
        }
