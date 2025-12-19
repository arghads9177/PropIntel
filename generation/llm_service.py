"""
LLM Service for PropIntel

This module provides unified interface to multiple LLM providers:
- OpenAI (GPT-4, GPT-3.5)
- Google Gemini
- Groq (LLaMA models)

Includes fallback logic, error handling, and response formatting.
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
import os

from ingestion.config.env_loader import get_config


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"


class LLMService:
    """
    Unified LLM service with multi-provider support.
    
    Features:
    - Multiple provider support
    - Automatic fallback
    - Response caching
    - Error handling
    - Token tracking
    """
    
    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ):
        """
        Initialize LLM service.
        
        Args:
            provider: LLM provider ('openai', 'gemini', 'groq')
            model: Specific model name (uses default if None)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
        """
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        
        # Set provider and model
        self.provider = LLMProvider(provider.lower())
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Set model based on provider
        if model is None:
            self.model = self._get_default_model()
        else:
            self.model = model
        
        # Initialize LLM client with fallback
        self.client = None
        self.fallback_providers = [LLMProvider.OPENAI, LLMProvider.GROQ, LLMProvider.GEMINI]
        self._initialize_client_with_fallback()
        
        # Track statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0
        }
        
        self.logger.info(f"LLMService initialized with {self.provider.value} - {self.model}")
    
    def _get_default_model(self) -> str:
        """Get default model for provider"""
        defaults = {
            LLMProvider.OPENAI: "gpt-3.5-turbo",
            LLMProvider.GEMINI: "gemini-pro",
            LLMProvider.GROQ: "llama-3.3-70b-versatile"  # Updated to current model
        }
        return defaults.get(self.provider, "gpt-3.5-turbo")
    
    def _initialize_client_with_fallback(self):
        """Initialize LLM client with automatic fallback to other providers"""
        # Try requested provider first
        providers_to_try = [self.provider] + [p for p in self.fallback_providers if p != self.provider]
        
        for provider in providers_to_try:
            try:
                self.logger.info(f"Attempting to initialize {provider.value}...")
                original_provider = self.provider
                self.provider = provider
                self.model = self._get_default_model()
                self._initialize_client()
                
                if original_provider != provider:
                    self.logger.warning(f"Using fallback provider: {provider.value} (requested: {original_provider.value})")
                return  # Success!
                
            except Exception as e:
                self.logger.warning(f"Failed to initialize {provider.value}: {e}")
                continue
        
        # All providers failed
        raise RuntimeError("All LLM providers failed to initialize. Please check API keys and credentials.")
    
    def _initialize_client(self):
        """Initialize LLM client based on provider"""
        try:
            if self.provider == LLMProvider.OPENAI:
                self._initialize_openai()
            elif self.provider == LLMProvider.GEMINI:
                self._initialize_gemini()
            elif self.provider == LLMProvider.GROQ:
                self._initialize_groq()
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.provider.value}: {e}")
            raise
    
    def _initialize_openai(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            
            api_key = self.config.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            
            self.client = OpenAI(api_key=api_key)
            self.logger.info("OpenAI client initialized")
            
        except ImportError:
            self.logger.error("OpenAI package not installed. Install with: pip install openai")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing OpenAI: {e}")
            raise
    
    def _initialize_gemini(self):
        """Initialize Google Gemini client"""
        try:
            import google.generativeai as genai
            
            api_key = self.config.get("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)
            self.logger.info("Gemini client initialized")
            
        except ImportError:
            self.logger.error("Google AI package not installed. Install with: pip install google-generativeai")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing Gemini: {e}")
            raise
    
    def _initialize_groq(self):
        """Initialize Groq client"""
        try:
            from groq import Groq
            
            api_key = self.config.get("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not found in environment")
            
            self.client = Groq(api_key=api_key)
            self.logger.info("Groq client initialized")
            
        except ImportError:
            self.logger.error("Groq package not installed. Install with: pip install groq")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing Groq: {e}")
            raise
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response from LLM.
        
        Args:
            prompt: User prompt/query
            system_prompt: System instructions (optional)
            **kwargs: Additional generation parameters
            
        Returns:
            Dictionary with response and metadata
        """
        self.logger.info(f"Generating response with {self.provider.value}")
        self.stats['total_requests'] += 1
        
        try:
            # Override defaults with kwargs
            temperature = kwargs.get('temperature', self.temperature)
            max_tokens = kwargs.get('max_tokens', self.max_tokens)
            
            # Generate based on provider
            if self.provider == LLMProvider.OPENAI:
                response = self._generate_openai(prompt, system_prompt, temperature, max_tokens)
            elif self.provider == LLMProvider.GEMINI:
                response = self._generate_gemini(prompt, system_prompt, temperature, max_tokens)
            elif self.provider == LLMProvider.GROQ:
                response = self._generate_groq(prompt, system_prompt, temperature, max_tokens)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
            
            self.stats['successful_requests'] += 1
            self.stats['total_tokens'] += response.get('tokens_used', 0)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            self.stats['failed_requests'] += 1
            
            return {
                'answer': None,
                'error': str(e),
                'provider': self.provider.value,
                'model': self.model
            }
    
    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Generate response using OpenAI"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return {
            'answer': response.choices[0].message.content,
            'provider': self.provider.value,
            'model': self.model,
            'tokens_used': response.usage.total_tokens,
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'finish_reason': response.choices[0].finish_reason
        }
    
    def _generate_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Generate response using Google Gemini"""
        # Combine system and user prompts
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Configure generation
        generation_config = {
            'temperature': temperature,
            'max_output_tokens': max_tokens,
        }
        
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        return {
            'answer': response.text,
            'provider': self.provider.value,
            'model': self.model,
            'tokens_used': response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0,
            'finish_reason': 'stop'
        }
    
    def _generate_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> Dict[str, Any]:
        """Generate response using Groq"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return {
            'answer': response.choices[0].message.content,
            'provider': self.provider.value,
            'model': self.model,
            'tokens_used': response.usage.total_tokens,
            'prompt_tokens': response.usage.prompt_tokens,
            'completion_tokens': response.usage.completion_tokens,
            'finish_reason': response.choices[0].finish_reason
        }
    
    def generate_with_fallback(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate with automatic fallback to other providers.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            fallback_providers: List of fallback providers to try
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary
        """
        # Try primary provider
        response = self.generate(prompt, system_prompt, **kwargs)
        
        if response.get('answer'):
            return response
        
        # Try fallback providers
        if fallback_providers:
            for provider in fallback_providers:
                self.logger.warning(f"Trying fallback provider: {provider}")
                
                try:
                    # Create temporary service with fallback provider
                    fallback_service = LLMService(
                        provider=provider,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                    
                    response = fallback_service.generate(prompt, system_prompt, **kwargs)
                    
                    if response.get('answer'):
                        self.logger.info(f"Fallback to {provider} successful")
                        return response
                    
                except Exception as e:
                    self.logger.error(f"Fallback to {provider} failed: {e}")
                    continue
        
        # All attempts failed
        return {
            'answer': None,
            'error': 'All providers failed',
            'provider': 'none',
            'model': 'none'
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        stats = self.stats.copy()
        stats['provider'] = self.provider.value
        stats['model'] = self.model
        stats['success_rate'] = (
            self.stats['successful_requests'] / self.stats['total_requests']
            if self.stats['total_requests'] > 0 else 0
        )
        return stats
