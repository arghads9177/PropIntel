"""
Prompt Manager for PropIntel

This module manages prompt templates, context formatting, and prompt engineering
for optimal answer generation from retrieved context.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Represents a prompt template"""
    name: str
    system_prompt: str
    user_template: str
    few_shot_examples: Optional[List[Dict[str, str]]] = None
    
    def format(self, **kwargs) -> str:
        """Format template with variables"""
        return self.user_template.format(**kwargs)


class PromptManager:
    """
    Manage prompts for answer generation.
    
    Features:
    - Template management
    - Context formatting
    - Few-shot examples
    - Dynamic prompt construction
    """
    
    # System prompts for different scenarios
    SYSTEM_PROMPTS = {
        'default': """You are a helpful AI assistant for PropIntel, a real estate information system.
Your role is to provide accurate, concise answers about real estate companies and projects based on the provided context.

Guidelines:
- Only use information from the provided context
- If information is not in the context, say "I don't have that information"
- Be specific and cite relevant details
- Keep answers concise but complete
- Use proper formatting for lists and addresses
- Maintain a professional, helpful tone""",
        
        'detailed': """You are an expert real estate analyst for PropIntel.
Provide comprehensive, detailed answers about real estate companies and projects based on the context.

Guidelines:
- Analyze and synthesize information from the context
- Provide detailed explanations when appropriate
- Include all relevant information (specializations, locations, contact details, project details)
- Structure answers clearly with sections
- Use bullet points for lists
- Only use information from the context - never make up information
- If uncertain or information is missing, explicitly state that""",
        
        'concise': """You are a concise AI assistant for PropIntel.
Provide brief, direct answers about real estate companies and projects.

Guidelines:
- Keep answers short and to the point
- Use 1-2 sentences when possible
- Only include essential information
- Use the context provided
- If information is not available, say so briefly""",
        
        'project_focused': """You are a real estate project information specialist for PropIntel.
Provide detailed, accurate information about real estate projects including tower configurations, floor counts, locations, and developer details.

Guidelines:
- Focus on project-specific information: towers, floors, status, location, developer
- When multiple towers exist, clearly differentiate between them
- Always mention the project status (upcoming/running/completed)
- For floor queries, specify which tower the information relates to
- Use structured formatting for multi-tower projects
- Only use information from the context chunks provided
- Cite the chunk type (overview/tower/location) when relevant for accuracy"""
    }
    
    # Few-shot examples for better performance
    FEW_SHOT_EXAMPLES = [
        # Company-focused examples
        {
            'query': 'What does the company specialize in?',
            'context': 'Specializations: Residential Complexes, Commercial Buildings, Townships',
            'answer': 'The company specializes in Residential Complexes, Commercial Buildings, and Townships.'
        },
        {
            'query': 'How can I contact them?',
            'context': 'Phone: +91-341-7963322, Email: contact@example.com',
            'answer': 'You can contact them by phone at +91-341-7963322 or by email at contact@example.com.'
        },
        {
            'query': 'Where do they operate?',
            'context': 'Service Areas: Asansol, Bandel, Hooghly',
            'answer': 'They operate in Asansol, Bandel, and Hooghly.'
        },
        # Project-focused examples
        {
            'query': 'How many floors does Kabi Tirtha have?',
            'context': 'Project: Kabi Tirtha\nTower 1: G+11\nTower 2: G+10\nTower 3: G+8\nTower 4: G+8',
            'answer': 'Kabi Tirtha has 4 towers with the following floor configurations:\n- Tower 1: G+11 (Ground + 11 floors)\n- Tower 2: G+10 (Ground + 10 floors)\n- Tower 3: G+8 (Ground + 8 floors)\n- Tower 4: G+8 (Ground + 8 floors)'
        },
        {
            'query': 'What upcoming projects are there?',
            'context': 'Project: Deb Apartment, Status: Upcoming, Developer: Incite India Pvt. Ltd.\nProject: Nilachal Apartment, Status: Upcoming, Developer: Astha Finance',
            'answer': 'There are 2 upcoming projects:\n1. Deb Apartment - Developed by Incite India Pvt. Ltd.\n2. Nilachal Apartment - Developed by Astha Finance & Investment Ltd.'
        },
        {
            'query': 'Tell me about Urban Residency project',
            'context': 'Project Name: Urban Residency\nStatus: Running\nDeveloper: Metro Properties\nLocation: New Town, Kolkata\nTowers: 2',
            'answer': 'Urban Residency is a running project being developed by Metro Properties. It is located in New Town, Kolkata and consists of 2 towers.'
        }
    ]
    
    def __init__(self):
        """Initialize prompt manager"""
        self.logger = logging.getLogger(__name__)
        self.templates = {}
        self._initialize_templates()
        self.logger.info("PromptManager initialized")
    
    def _initialize_templates(self):
        """Initialize default prompt templates"""
        # Default RAG template
        self.templates['default'] = PromptTemplate(
            name='default',
            system_prompt=self.SYSTEM_PROMPTS['default'],
            user_template="""Context Information:
{context}

Question: {query}

Please provide a clear, accurate answer based only on the context above."""
        )
        
        # Detailed template
        self.templates['detailed'] = PromptTemplate(
            name='detailed',
            system_prompt=self.SYSTEM_PROMPTS['detailed'],
            user_template="""I will provide you with context about a real estate company and a question.
Please analyze the context and provide a comprehensive answer.

Context:
{context}

Question: {query}

Detailed Answer:"""
        )
        
        # Concise template
        self.templates['concise'] = PromptTemplate(
            name='concise',
            system_prompt=self.SYSTEM_PROMPTS['concise'],
            user_template="""Context: {context}

Question: {query}

Brief Answer:"""
        )
        
        # Conversational template
        self.templates['conversational'] = PromptTemplate(
            name='conversational',
            system_prompt="""You are a friendly, conversational AI assistant for PropIntel.
Provide helpful answers in a natural, conversational tone while staying accurate to the context.""",
            user_template="""Here's what I know about the company:
{context}

User asked: {query}

Let me help you with that:"""
        )
        
        # Project-focused template
        self.templates['project'] = PromptTemplate(
            name='project',
            system_prompt=self.SYSTEM_PROMPTS['project_focused'],
            user_template="""Project Information:
{context}

Question: {query}

Please provide a detailed answer about the project based on the information above. If the project has multiple towers, clearly specify which tower each detail belongs to."""
        )
    
    def format_context(
        self,
        results: List[Dict[str, Any]],
        max_length: int = 2000,
        include_metadata: bool = True
    ) -> str:
        """
        Format retrieval results into context for LLM.
        
        Args:
            results: List of retrieval results
            max_length: Maximum context length in characters
            include_metadata: Whether to include metadata info
            
        Returns:
            Formatted context string
        """
        if not results:
            return "No relevant information found."
        
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(results, 1):
            # Format single result
            part = self._format_single_result(result, i, include_metadata)
            
            # Check length
            if current_length + len(part) > max_length:
                self.logger.warning(f"Context truncated at {i-1} results (max_length={max_length})")
                break
            
            context_parts.append(part)
            current_length += len(part)
        
        return "\n\n".join(context_parts)
    
    def _format_single_result(
        self,
        result: Dict[str, Any],
        index: int,
        include_metadata: bool
    ) -> str:
        """Format a single retrieval result"""
        parts = [f"[Source {index}]"]
        
        # Add metadata if requested
        if include_metadata:
            metadata = result.get('metadata', {})
            
            # Handle both company and project metadata
            if 'section' in metadata:
                # Company data
                section = metadata.get('section', 'N/A')
                subsection = metadata.get('subsection', '')
                
                if subsection:
                    parts.append(f"Section: {section}/{subsection}")
                else:
                    parts.append(f"Section: {section}")
            elif 'chunk_type' in metadata:
                # Project data
                chunk_type = metadata.get('chunk_type', 'N/A')
                project_name = metadata.get('project_name', 'Unknown')
                
                if chunk_type == 'tower':
                    tower_id = metadata.get('tower_id', 'N/A')
                    parts.append(f"Type: Project - {chunk_type.capitalize()} ({tower_id})")
                    parts.append(f"Project: {project_name}")
                else:
                    parts.append(f"Type: Project - {chunk_type.capitalize()}")
                    parts.append(f"Project: {project_name}")
        
        # Add content
        content = result.get('content', '')
        parts.append(content)
        
        return "\n".join(parts)
    
    def build_prompt(
        self,
        query: str,
        results: List[Dict[str, Any]],
        template_name: str = 'default',
        max_context_length: int = 2000,
        include_metadata: bool = True,
        include_few_shot: bool = False
    ) -> Dict[str, str]:
        """
        Build complete prompt from query and results.
        
        Args:
            query: User query
            results: Retrieval results
            template_name: Name of template to use
            max_context_length: Maximum context length
            include_metadata: Whether to include metadata
            include_few_shot: Whether to include few-shot examples
            
        Returns:
            Dictionary with 'system_prompt' and 'user_prompt'
        """
        # Get template
        template = self.templates.get(template_name, self.templates['default'])
        
        # Format context
        context = self.format_context(
            results,
            max_length=max_context_length,
            include_metadata=include_metadata
        )
        
        # Build user prompt
        user_prompt = template.format(query=query, context=context)
        
        # Add few-shot examples if requested
        system_prompt = template.system_prompt
        if include_few_shot:
            examples = self._format_few_shot_examples()
            system_prompt = f"{system_prompt}\n\n{examples}"
        
        return {
            'system_prompt': system_prompt,
            'user_prompt': user_prompt
        }
    
    def _format_few_shot_examples(self) -> str:
        """Format few-shot examples"""
        examples = ["Here are some examples of good answers:\n"]
        
        for i, example in enumerate(self.FEW_SHOT_EXAMPLES, 1):
            examples.append(f"Example {i}:")
            examples.append(f"Context: {example['context']}")
            examples.append(f"Question: {example['query']}")
            examples.append(f"Answer: {example['answer']}")
            examples.append("")
        
        return "\n".join(examples)
    
    def create_custom_template(
        self,
        name: str,
        system_prompt: str,
        user_template: str
    ) -> PromptTemplate:
        """
        Create and register custom prompt template.
        
        Args:
            name: Template name
            system_prompt: System instructions
            user_template: User prompt template with {query} and {context} placeholders
            
        Returns:
            Created PromptTemplate
        """
        template = PromptTemplate(
            name=name,
            system_prompt=system_prompt,
            user_template=user_template
        )
        
        self.templates[name] = template
        self.logger.info(f"Custom template '{name}' created")
        
        return template
    
    def optimize_context_for_tokens(
        self,
        results: List[Dict[str, Any]],
        max_tokens: int = 1500,
        chars_per_token: float = 4.0
    ) -> List[Dict[str, Any]]:
        """
        Optimize context to fit within token limit.
        
        Args:
            results: Retrieval results
            max_tokens: Maximum tokens allowed
            chars_per_token: Approximate characters per token
            
        Returns:
            Truncated results list
        """
        max_chars = int(max_tokens * chars_per_token)
        
        optimized_results = []
        total_chars = 0
        
        for result in results:
            content_length = len(result.get('content', ''))
            
            if total_chars + content_length <= max_chars:
                optimized_results.append(result)
                total_chars += content_length
            else:
                # Truncate last result if it fits partially
                remaining_chars = max_chars - total_chars
                if remaining_chars > 100:  # Only add if meaningful
                    truncated_result = result.copy()
                    truncated_result['content'] = result['content'][:remaining_chars] + "..."
                    optimized_results.append(truncated_result)
                break
        
        self.logger.info(f"Optimized context: {len(results)} → {len(optimized_results)} results")
        return optimized_results
    
    def add_query_context(
        self,
        query: str,
        query_metadata: Dict[str, Any]
    ) -> str:
        """
        Enhance query with detected metadata.
        
        Args:
            query: Original query
            query_metadata: Metadata from query processing
            
        Returns:
            Enhanced query
        """
        query_type = query_metadata.get('query_type')
        
        # Add context based on query type
        enhancements = {
            # Company-related
            'specialization': "Focus on the company's services and areas of expertise.",
            'contact': "Provide all available contact information including phone, email, and address.",
            'location': "Focus on geographic areas and service locations.",
            'about': "Provide a comprehensive overview of the company.",
            'timing': "Focus on office hours and availability.",
            'social': "Provide social media links and online presence.",
            # Project-related
            'project_info': "Focus on project details including name, status, developer, and location.",
            'floors': "Provide floor count information. If multiple towers exist, specify which tower.",
            'towers': "Provide information about all towers in the project.",
            'project_status': "Focus on the project status (upcoming/running/completed) and key details.",
            'tower_info': "Provide detailed information about the specific tower mentioned.",
            'project_details': "Provide comprehensive project information including all available details.",
            'project_list': "List all projects matching the criteria with their key details.",
        }
        
        enhancement = enhancements.get(query_type, "")
        
        if enhancement:
            return f"{query}\n\nNote: {enhancement}"
        
        return query
    
    def get_template_names(self) -> List[str]:
        """Get list of available template names"""
        return list(self.templates.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get prompt manager statistics"""
        return {
            'num_templates': len(self.templates),
            'template_names': self.get_template_names(),
            'num_few_shot_examples': len(self.FEW_SHOT_EXAMPLES)
        }
