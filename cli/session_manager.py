"""
Session Manager for PropIntel CLI

Handles conversation history, session persistence, and exports.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class SessionManager:
    """
    Manages CLI session state and conversation history.
    
    Features:
    - Track conversation history
    - Session persistence
    - Export to JSON
    - Statistics tracking
    """
    
    def __init__(self, max_history: int = 50):
        """
        Initialize session manager.
        
        Args:
            max_history: Maximum number of interactions to keep
        """
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []
        self.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def add_interaction(self, query: str, result: Dict[str, Any]):
        """
        Add a query-answer interaction to history.
        
        Args:
            query: User query
            result: Answer result from generator
        """
        metadata = result.get('metadata', {})
        provider = metadata.get('provider') or metadata.get('llm_provider')
        response_time = metadata.get('response_time')
        if response_time is None:
            response_time = metadata.get('response_time_seconds')
        tokens_used = metadata.get('tokens_used')
        if tokens_used is None:
            tokens_used = metadata.get('tokens')

        interaction = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'query': query,
            'answer': result.get('answer', ''),
            'success': result.get('success', False),
            'metadata': {
                'provider': provider,
                'response_time': response_time,
                'tokens': tokens_used,
                'sources_count': len(result.get('sources', [])),
                'routing': metadata.get('routing')
            }
        }
        
        self.history.append(interaction)
        
        # Trim history if too long
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            limit: Maximum number of recent interactions to return
            
        Returns:
            List of interactions
        """
        if limit:
            return self.history[-limit:]
        return self.history.copy()
    
    def get_last_interaction(self) -> Optional[Dict[str, Any]]:
        """Get the last interaction"""
        if self.history:
            return self.history[-1]
        return None
    
    def clear(self):
        """Clear conversation history"""
        self.history = []
    
    def export(self, filepath: Optional[str] = None) -> Optional[str]:
        """
        Export session to JSON file.
        
        Args:
            filepath: Optional custom filepath
            
        Returns:
            Filepath where session was saved, or None on error
        """
        if not filepath:
            # Create exports directory if it doesn't exist
            export_dir = Path(__file__).parent.parent / "exports"
            export_dir.mkdir(exist_ok=True)
            
            # Generate filename
            filename = f"propintel_session_{self.session_id}.json"
            filepath = export_dir / filename
        
        try:
            session_data = {
                'session_id': self.session_id,
                'start_time': self.start_time,
                'export_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_interactions': len(self.history),
                'history': self.history
            }
            
            with open(filepath, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            return str(filepath)
            
        except Exception as e:
            print(f"Error exporting session: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.
        
        Returns:
            Dictionary with session stats
        """
        if not self.history:
            return {
                'total_interactions': 0,
                'successful': 0,
                'failed': 0,
                'avg_response_time': 0,
                'total_tokens': 0
            }
        
        successful = sum(1 for i in self.history if i.get('success'))
        failed = len(self.history) - successful
        
        response_times = [
            i['metadata'].get('response_time', 0)
            for i in self.history
            if i['metadata'].get('response_time') is not None
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        total_tokens = sum(
            i['metadata'].get('tokens', 0)
            for i in self.history
            if i['metadata'].get('tokens') is not None
        )
        
        return {
            'total_interactions': len(self.history),
            'successful': successful,
            'failed': failed,
            'avg_response_time': avg_response_time,
            'total_tokens': total_tokens
        }
