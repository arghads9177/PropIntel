"""
Answer Validator for PropIntel

This module validates generated answers for quality, accuracy, and safety.
Includes hallucination detection, fact checking, and confidence scoring.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Validation result with detailed metrics"""
    is_valid: bool
    confidence_score: float
    issues: List[str]
    warnings: List[str]
    metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_valid': self.is_valid,
            'confidence_score': self.confidence_score,
            'issues': self.issues,
            'warnings': self.warnings,
            'metrics': self.metrics
        }


class AnswerValidator:
    """
    Validate generated answers for quality and accuracy.
    
    Features:
    - Hallucination detection
    - Fact verification against context
    - Confidence scoring
    - Quality checks
    - Safety filters
    """
    
    # Phrases indicating uncertainty or lack of information
    UNCERTAINTY_PHRASES = [
        "i don't have",
        "not available",
        "no information",
        "cannot find",
        "unclear",
        "uncertain",
        "not sure",
        "don't know",
        "unable to find"
    ]
    
    # Phrases indicating potential hallucination
    HALLUCINATION_INDICATORS = [
        "might be",
        "could be",
        "possibly",
        "perhaps",
        "probably",
        "i think",
        "i believe",
        "it seems"
    ]
    
    def __init__(self):
        """Initialize answer validator"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("AnswerValidator initialized")
    
    def validate(
        self,
        answer: str,
        query: str,
        context_results: List[Dict[str, Any]],
        strict: bool = False
    ) -> ValidationResult:
        """
        Validate generated answer.
        
        Args:
            answer: Generated answer text
            query: Original query
            context_results: Retrieval results used as context
            strict: Whether to use strict validation
            
        Returns:
            ValidationResult with validation details
        """
        self.logger.info(f"Validating answer (strict={strict})")
        
        issues = []
        warnings = []
        metrics = {}
        
        # 1. Basic quality checks
        quality_score, quality_issues = self._check_quality(answer)
        issues.extend(quality_issues)
        metrics['quality_score'] = quality_score
        
        # 2. Check for uncertainty
        uncertainty_score, uncertainty_warnings = self._check_uncertainty(answer)
        warnings.extend(uncertainty_warnings)
        metrics['uncertainty_score'] = uncertainty_score
        
        # 3. Check for hallucinations
        hallucination_score, hall_warnings = self._check_hallucinations(answer)
        warnings.extend(hall_warnings)
        metrics['hallucination_score'] = hallucination_score
        
        # 4. Verify facts against context
        fact_score, fact_issues = self._verify_facts(answer, context_results)
        if fact_score < 0.5:
            issues.append(f"Low fact verification score: {fact_score:.2f}")
        metrics['fact_verification_score'] = fact_score
        
        # 5. Check relevance to query
        relevance_score = self._check_relevance(answer, query)
        if relevance_score < 0.3:
            issues.append(f"Answer may not be relevant to query (score: {relevance_score:.2f})")
        metrics['relevance_score'] = relevance_score
        
        # 6. Check completeness
        completeness_score = self._check_completeness(answer, query)
        metrics['completeness_score'] = completeness_score
        
        # Calculate overall confidence
        confidence_score = self._calculate_confidence(metrics)
        
        # Determine validity
        is_valid = self._determine_validity(
            confidence_score,
            issues,
            strict
        )
        
        return ValidationResult(
            is_valid=is_valid,
            confidence_score=confidence_score,
            issues=issues,
            warnings=warnings,
            metrics=metrics
        )
    
    def _check_quality(self, answer: str) -> Tuple[float, List[str]]:
        """Check basic answer quality"""
        issues = []
        score = 1.0
        
        # Check length
        if len(answer) < 10:
            issues.append("Answer is too short")
            score *= 0.3
        elif len(answer) < 20:
            issues.append("Answer may be too brief")
            score *= 0.7
        
        # Check for empty or whitespace-only
        if not answer.strip():
            issues.append("Answer is empty")
            score = 0.0
        
        # Check for complete sentences
        if not any(answer.endswith(p) for p in ['.', '!', '?']):
            issues.append("Answer doesn't end with proper punctuation")
            score *= 0.9
        
        return score, issues
    
    def _check_uncertainty(self, answer: str) -> Tuple[float, List[str]]:
        """Check for uncertainty in answer"""
        warnings = []
        answer_lower = answer.lower()
        
        # Count uncertainty phrases
        uncertainty_count = sum(
            1 for phrase in self.UNCERTAINTY_PHRASES
            if phrase in answer_lower
        )
        
        if uncertainty_count > 0:
            warnings.append(f"Answer contains {uncertainty_count} uncertainty phrase(s)")
        
        # Calculate uncertainty score (inverse - higher is better)
        uncertainty_score = max(0.0, 1.0 - (uncertainty_count * 0.3))
        
        return uncertainty_score, warnings
    
    def _check_hallucinations(self, answer: str) -> Tuple[float, List[str]]:
        """Check for potential hallucinations"""
        warnings = []
        answer_lower = answer.lower()
        
        # Count hallucination indicators
        hall_count = sum(
            1 for phrase in self.HALLUCINATION_INDICATORS
            if phrase in answer_lower
        )
        
        if hall_count > 0:
            warnings.append(f"Answer contains {hall_count} uncertain phrase(s)")
        
        # Calculate score (inverse)
        hall_score = max(0.0, 1.0 - (hall_count * 0.2))
        
        return hall_score, warnings
    
    def _verify_facts(
        self,
        answer: str,
        context_results: List[Dict[str, Any]]
    ) -> Tuple[float, List[str]]:
        """Verify factual claims against context"""
        issues = []
        
        if not context_results:
            issues.append("No context available for fact verification")
            return 0.5, issues
        
        # Extract key information from answer
        answer_tokens = set(self._extract_key_terms(answer))
        
        # Extract information from context
        context_text = " ".join(
            result.get('content', '') for result in context_results
        )
        context_tokens = set(self._extract_key_terms(context_text))
        
        # Calculate overlap
        if not answer_tokens:
            return 0.5, issues
        
        overlap = answer_tokens & context_tokens
        fact_score = len(overlap) / len(answer_tokens) if answer_tokens else 0.0
        
        if fact_score < 0.3:
            issues.append("Many facts in answer not found in context")
        elif fact_score < 0.5:
            issues.append("Some facts in answer may not be from context")
        
        return fact_score, issues
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text"""
        # Remove common words and extract meaningful terms
        text_lower = text.lower()
        
        # Simple tokenization - extract words, numbers, and some special patterns
        tokens = re.findall(r'\b\w+\b', text_lower)
        
        # Filter out very common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
            'she', 'it', 'we', 'they', 'what', 'which', 'who', 'where', 'when',
            'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
            'other', 'some', 'such', 'than', 'too', 'very', 'with', 'by', 'about'
        }
        
        key_terms = [t for t in tokens if t not in stop_words and len(t) > 2]
        
        return key_terms
    
    def _check_relevance(self, answer: str, query: str) -> float:
        """Check if answer is relevant to query"""
        # Extract key terms from both
        answer_terms = set(self._extract_key_terms(answer))
        query_terms = set(self._extract_key_terms(query))
        
        if not query_terms:
            return 0.5
        
        # Calculate overlap
        overlap = answer_terms & query_terms
        relevance_score = len(overlap) / len(query_terms)
        
        return relevance_score
    
    def _check_completeness(self, answer: str, query: str) -> float:
        """Check if answer is complete"""
        # Simple heuristic based on length and structure
        score = 1.0
        
        # Minimum length
        if len(answer) < 30:
            score *= 0.6
        elif len(answer) < 50:
            score *= 0.8
        
        # Check for list items if query asks for multiple things
        if any(word in query.lower() for word in ['what are', 'list', 'all']):
            # Look for list patterns
            has_bullets = bool(re.search(r'[-•*]\s', answer))
            has_numbers = bool(re.search(r'\d+[\.\)]\s', answer))
            has_commas = ',' in answer
            
            if not (has_bullets or has_numbers or has_commas):
                score *= 0.7
        
        return score
    
    def _calculate_confidence(self, metrics: Dict[str, float]) -> float:
        """Calculate overall confidence score"""
        # Weighted average of metrics
        weights = {
            'quality_score': 0.25,
            'uncertainty_score': 0.15,
            'hallucination_score': 0.15,
            'fact_verification_score': 0.30,
            'relevance_score': 0.10,
            'completeness_score': 0.05
        }
        
        confidence = 0.0
        for metric, weight in weights.items():
            confidence += metrics.get(metric, 0.5) * weight
        
        return confidence
    
    def _determine_validity(
        self,
        confidence_score: float,
        issues: List[str],
        strict: bool
    ) -> bool:
        """Determine if answer is valid"""
        if strict:
            # Strict: high confidence and no major issues
            return confidence_score >= 0.7 and len(issues) == 0
        else:
            # Lenient: moderate confidence and no critical issues
            critical_issues = [
                issue for issue in issues
                if any(word in issue.lower() for word in ['empty', 'invalid', 'critical'])
            ]
            return confidence_score >= 0.4 and len(critical_issues) == 0
    
    def validate_batch(
        self,
        responses: List[Dict[str, Any]],
        strict: bool = False
    ) -> List[ValidationResult]:
        """
        Validate multiple answers.
        
        Args:
            responses: List of answer generation responses
            strict: Whether to use strict validation
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        
        for response in responses:
            if response.get('answer'):
                result = self.validate(
                    answer=response['answer'],
                    query=response['query'],
                    context_results=response.get('retrieval_results', []),
                    strict=strict
                )
            else:
                # Invalid response
                result = ValidationResult(
                    is_valid=False,
                    confidence_score=0.0,
                    issues=['No answer generated'],
                    warnings=[],
                    metrics={}
                )
            
            results.append(result)
        
        return results
    
    def get_quality_report(
        self,
        validation_results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """
        Generate quality report from validation results.
        
        Args:
            validation_results: List of validation results
            
        Returns:
            Quality metrics report
        """
        if not validation_results:
            return {}
        
        valid_count = sum(1 for r in validation_results if r.is_valid)
        total_count = len(validation_results)
        
        avg_confidence = sum(r.confidence_score for r in validation_results) / total_count
        
        all_issues = []
        all_warnings = []
        
        for result in validation_results:
            all_issues.extend(result.issues)
            all_warnings.extend(result.warnings)
        
        return {
            'total_answers': total_count,
            'valid_answers': valid_count,
            'invalid_answers': total_count - valid_count,
            'validity_rate': valid_count / total_count if total_count > 0 else 0,
            'average_confidence': avg_confidence,
            'total_issues': len(all_issues),
            'total_warnings': len(all_warnings),
            'common_issues': self._get_common_items(all_issues),
            'common_warnings': self._get_common_items(all_warnings)
        }
    
    def _get_common_items(self, items: List[str], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get most common items from list"""
        from collections import Counter
        
        if not items:
            return []
        
        counter = Counter(items)
        common = counter.most_common(top_n)
        
        return [
            {'item': item, 'count': count}
            for item, count in common
        ]
