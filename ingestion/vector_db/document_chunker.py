"""
Document Chunker for PropIntel

This module provides intelligent document chunking capabilities for real estate data.
It splits structured company information into semantic chunks optimized for RAG retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class DocumentChunk:
    """Represents a chunk of document with metadata"""
    
    content: str
    metadata: Dict[str, Any]
    chunk_id: str
    chunk_type: str  # 'company_info', 'contact', 'address', 'social_media', etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary"""
        return {
            'content': self.content,
            'metadata': self.metadata,
            'chunk_id': self.chunk_id,
            'chunk_type': self.chunk_type
        }


class DocumentChunker:
    """
    Intelligent document chunker for real estate company data.
    
    Splits structured JSON data into semantic chunks optimized for retrieval.
    Preserves metadata and context for each chunk.
    """
    
    def __init__(self, max_chunk_size: int = 500, overlap: int = 50):
        """
        Initialize the document chunker.
        
        Args:
            max_chunk_size: Maximum number of characters per chunk
            overlap: Number of overlapping characters between chunks
        """
        self.logger = logging.getLogger(__name__)
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        
        self.logger.info(f"DocumentChunker initialized with max_chunk_size={max_chunk_size}, overlap={overlap}")
    
    def chunk_company_data(self, data: Dict[str, Any], company_id: str = "unknown") -> List[DocumentChunk]:
        """
        Chunk company data into semantic units.
        
        Args:
            data: Clean company data from Phase 3
            company_id: Identifier for the company
            
        Returns:
            List of DocumentChunk objects
        """
        self.logger.info(f"Starting chunking process for company: {company_id}")
        
        chunks = []
        
        # Chunk company information
        if 'company_info' in data:
            company_chunks = self._chunk_company_info(data['company_info'], company_id)
            chunks.extend(company_chunks)
            self.logger.info(f"Created {len(company_chunks)} chunks from company_info")
        
        # Chunk contact details
        if 'contact_details' in data:
            contact_chunks = self._chunk_contact_details(data['contact_details'], company_id)
            chunks.extend(contact_chunks)
            self.logger.info(f"Created {len(contact_chunks)} chunks from contact_details")
        
        # Chunk social media (include website if present)
        if 'social_media' in data or 'website' in data:
            social_data = data.get('social_media', {})
            website = data.get('website')
            social_chunks = self._chunk_social_media(social_data, company_id, website)
            chunks.extend(social_chunks)
            self.logger.info(f"Created {len(social_chunks)} chunks from social_media")
        
        self.logger.info(f"Total chunks created: {len(chunks)}")
        
        return chunks
    
    def _chunk_company_info(self, company_info: Dict[str, Any], company_id: str) -> List[DocumentChunk]:
        """Chunk company information section"""
        
        chunks = []
        
        # Chunk 1: Company overview with name, tagline, and welcome message
        overview_content = self._build_company_overview(company_info)
        if overview_content:
            chunks.append(DocumentChunk(
                content=overview_content,
                metadata={
                    'company_id': company_id,
                    'section': 'company_info',
                    'subsection': 'overview',
                    'name': company_info.get('name', ''),
                    'experience_years': company_info.get('experience_years', 0)
                },
                chunk_id=f"{company_id}_company_overview",
                chunk_type='company_info'
            ))
        
        # Chunk 2: Specializations
        if 'specializations' in company_info and company_info['specializations']:
            specializations_content = self._build_specializations(company_info)
            chunks.append(DocumentChunk(
                content=specializations_content,
                metadata={
                    'company_id': company_id,
                    'section': 'company_info',
                    'subsection': 'specializations',
                    'specializations': ', '.join(company_info['specializations'])
                },
                chunk_id=f"{company_id}_specializations",
                chunk_type='company_info'
            ))
        
        # Chunk 3: Service areas
        if 'service_areas' in company_info and company_info['service_areas']:
            service_areas_content = self._build_service_areas(company_info)
            chunks.append(DocumentChunk(
                content=service_areas_content,
                metadata={
                    'company_id': company_id,
                    'section': 'company_info',
                    'subsection': 'service_areas',
                    'service_areas': ', '.join(company_info['service_areas'])
                },
                chunk_id=f"{company_id}_service_areas",
                chunk_type='company_info'
            ))
        
        return chunks
    
    def _chunk_contact_details(self, contact_details: Dict[str, Any], company_id: str) -> List[DocumentChunk]:
        """Chunk contact details section"""
        
        chunks = []
        
        # Chunk 1: Office timing
        if 'office_timing' in contact_details:
            timing_content = self._build_office_timing(contact_details['office_timing'])
            chunks.append(DocumentChunk(
                content=timing_content,
                metadata={
                    'company_id': company_id,
                    'section': 'contact_details',
                    'subsection': 'office_timing',
                    'days': contact_details['office_timing'].get('days', ''),
                    'hours': contact_details['office_timing'].get('hours', '')
                },
                chunk_id=f"{company_id}_office_timing",
                chunk_type='contact'
            ))
        
        # Chunk 2: Head office
        if 'head_office' in contact_details:
            head_office_content = self._build_head_office(contact_details['head_office'])
            head_office = contact_details['head_office']
            chunks.append(DocumentChunk(
                content=head_office_content,
                metadata={
                    'company_id': company_id,
                    'section': 'contact_details',
                    'subsection': 'head_office',
                    'phones': ', '.join(head_office.get('phones', [])),
                    'emails': ', '.join(head_office.get('emails', []))
                },
                chunk_id=f"{company_id}_head_office",
                chunk_type='address'
            ))
        
        # Chunk 3+: Each branch as a separate chunk
        if 'branches' in contact_details and contact_details['branches']:
            for idx, branch in enumerate(contact_details['branches']):
                branch_content = self._build_branch(branch, idx)
                chunks.append(DocumentChunk(
                    content=branch_content,
                    metadata={
                        'company_id': company_id,
                        'section': 'contact_details',
                        'subsection': 'branch',
                        'branch_name': branch.get('name', f'Branch {idx+1}'),
                        'phones': ', '.join(branch.get('phones', []))
                    },
                    chunk_id=f"{company_id}_branch_{idx}",
                    chunk_type='address'
                ))
        
        return chunks
    
    def _chunk_social_media(self, social_media: Dict[str, Any], company_id: str, website: Optional[str] = None) -> List[DocumentChunk]:
        """Chunk social media section"""
        
        if not social_media and not website:
            return []
        
        social_content = self._build_social_media(social_media, website)
        
        platforms = list(social_media.keys()) if social_media else []
        if website:
            platforms.append('website')
        
        return [DocumentChunk(
            content=social_content,
            metadata={
                'company_id': company_id,
                'section': 'social_media',
                'platforms': ', '.join(platforms)
            },
            chunk_id=f"{company_id}_social_media",
            chunk_type='social_media'
        )]
    
    def _build_company_overview(self, company_info: Dict[str, Any]) -> str:
        """Build company overview content"""
        
        parts = []
        
        # Company name
        if 'name' in company_info:
            parts.append(f"Company Name: {company_info['name']}")
        
        # Tagline
        if 'tagline' in company_info:
            parts.append(f"Tagline: {company_info['tagline']}")
        
        # Welcome message / About
        if 'welcome_message' in company_info:
            parts.append(f"About: {company_info['welcome_message']}")
        
        # Experience
        if 'experience_years' in company_info:
            parts.append(f"Years of Experience: {company_info['experience_years']} years")
        
        return "\n\n".join(parts)
    
    def _build_specializations(self, company_info: Dict[str, Any]) -> str:
        """Build specializations content"""
        
        specializations = company_info.get('specializations', [])
        
        content = f"Specializations and Services offered by {company_info.get('name', 'the company')}:\n"
        content += "\n".join(f"- {spec}" for spec in specializations)
        
        return content
    
    def _build_service_areas(self, company_info: Dict[str, Any]) -> str:
        """Build service areas content"""
        
        service_areas = company_info.get('service_areas', [])
        
        content = f"Service Areas where {company_info.get('name', 'the company')} operates:\n"
        content += "\n".join(f"- {area}" for area in service_areas)
        
        return content
    
    def _build_office_timing(self, timing: Dict[str, str]) -> str:
        """Build office timing content"""
        
        content = "Office Timing:\n"
        content += f"Days: {timing.get('days', 'Not specified')}\n"
        content += f"Hours: {timing.get('hours', 'Not specified')}"
        
        if 'hours_24' in timing:
            content += f" ({timing['hours_24']} 24-hour format)"
        
        return content
    
    def _build_head_office(self, head_office: Dict[str, Any]) -> str:
        """Build head office content"""
        
        parts = [f"Head Office - {head_office.get('name', 'Main Office')}"]
        
        # Address
        if 'address' in head_office:
            addr = head_office['address']
            if isinstance(addr, dict):
                address_str = addr.get('full_address', '')
                if not address_str:
                    # Build from components
                    components = []
                    for key in ['building', 'street', 'area', 'city', 'district', 'state', 'pin_code']:
                        if key in addr and addr[key]:
                            components.append(str(addr[key]))
                    address_str = ', '.join(components)
                parts.append(f"Address: {address_str}")
        
        # Phones
        if 'phones' in head_office and head_office['phones']:
            phones_str = ', '.join(head_office['phones'])
            parts.append(f"Phone: {phones_str}")
        
        # Emails
        if 'emails' in head_office and head_office['emails']:
            emails_str = ', '.join(head_office['emails'])
            parts.append(f"Email: {emails_str}")
        
        return "\n".join(parts)
    
    def _build_branch(self, branch: Dict[str, Any], idx: int) -> str:
        """Build branch content"""
        
        branch_name = branch.get('name', f'Branch Office {idx+1}')
        parts = [branch_name]
        
        # Address
        if 'address' in branch:
            addr = branch['address']
            if isinstance(addr, dict):
                components = []
                for key in ['building', 'street', 'area', 'city', 'district', 'state', 'pin_code']:
                    if key in addr and addr[key]:
                        components.append(str(addr[key]))
                address_str = ', '.join(components)
                parts.append(f"Address: {address_str}")
        
        # Phones
        if 'phones' in branch and branch['phones']:
            phones_str = ', '.join(branch['phones'])
            parts.append(f"Phone: {phones_str}")
        
        return "\n".join(parts)
    
    def _build_social_media(self, social_media: Dict[str, str], website: Optional[str] = None) -> str:
        """Build social media content"""
        
        parts = []
        
        # Add website first if present
        if website:
            parts.append(f"Website: {website}")
        
        # Add social media platforms
        if social_media:
            parts.append("\nSocial Media Presence:")
            for platform, url in social_media.items():
                parts.append(f"- {platform.capitalize()}: {url}")
        
        return "\n".join(parts).strip()
    
    def get_chunk_stats(self, chunks: Optional[List[DocumentChunk]] = None) -> Dict[str, Any]:
        """
        Get statistics about the chunks.
        
        Args:
            chunks: Optional list of chunks to analyze. If None, returns basic config stats.
            
        Returns:
            Dictionary with chunk statistics
        """
        if chunks is None:
            # Return basic configuration stats when no chunks provided
            return {
                'max_chunk_size': self.max_chunk_size,
                'overlap': self.overlap,
                'status': 'ready'
            }
        
        total_chunks = len(chunks)
        chunk_types = {}
        total_chars = 0
        
        for chunk in chunks:
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1
            total_chars += len(chunk.content)
        
        avg_chunk_size = total_chars / total_chunks if total_chunks > 0 else 0
        
        return {
            'total_chunks': total_chunks,
            'chunk_types': chunk_types,
            'total_characters': total_chars,
            'average_chunk_size': avg_chunk_size
        }
