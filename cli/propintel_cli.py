"""
CLI Interface for PropIntel RAG System

This module provides a command-line interface for interacting with the PropIntel
real estate intelligence assistant.
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from generation.answer_generator import AnswerGenerator
from cli.session_manager import SessionManager
from cli.formatter import CLIFormatter
from retrieval.collection_router import get_router


class PropIntelCLI:
    """
    Command-line interface for PropIntel RAG system.
    
    Features:
    - Interactive chat with RAG system
    - Session history management
    - Rich formatted output
    - Command system (/help, /history, etc.)
    - Configuration management
    """
    
    def __init__(self):
        """Initialize CLI interface"""
        self.formatter = CLIFormatter()
        self.session = SessionManager()
        self.generator: Optional[AnswerGenerator] = None
        self.collection_router = get_router()
        self.config = self._load_config()
        self.running = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.WARNING,  # Only show warnings/errors in CLI
            format='%(message)s'
        )
        
    def _load_config(self) -> Dict[str, Any]:
        """Load CLI configuration"""
        config_path = Path(__file__).parent / "config.json"
        
        default_config = {
            "provider": "groq",
            "model": None,
            "template": "default",
            "show_sources": True,
            "show_metadata": True,
            "show_collection": True,
            "collection_mode": "auto",  # auto, company, project
            "verbose": False,
            "max_history": 50
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")
        
        return default_config
    
    def _save_config(self):
        """Save CLI configuration"""
        config_path = Path(__file__).parent / "config.json"
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def initialize_generator(self):
        """Initialize the answer generator"""
        try:
            self.generator = AnswerGenerator(
                llm_provider=self.config['provider'],
                llm_model=self.config.get('model')
            )
            return True
        except Exception as e:
            self.formatter.print_error(f"Failed to initialize generator: {e}")
            return False
    
    def start(self):
        """Start the CLI interface"""
        self.running = True
        self.formatter.print_banner()
        
        # Initialize generator
        if not self.initialize_generator():
            return
        
        self.formatter.print_success("PropIntel is ready! Type your question or /help for commands.")
        print()
        
        # Main loop
        while self.running:
            try:
                # Get user input
                query = self._get_input()
                
                if not query.strip():
                    continue
                
                # Check for commands
                if query.startswith('/'):
                    self._handle_command(query)
                else:
                    self._handle_query(query)
                    
            except KeyboardInterrupt:
                print("\n")
                self._handle_command("/exit")
            except EOFError:
                print("\n")
                self._handle_command("/exit")
            except Exception as e:
                self.formatter.print_error(f"Unexpected error: {e}")
                if self.config.get('verbose'):
                    import traceback
                    traceback.print_exc()
    
    def _get_input(self) -> str:
        """Get user input with prompt"""
        try:
            return input(self.formatter.format_prompt())
        except (KeyboardInterrupt, EOFError):
            raise
    
    def _handle_query(self, query: str):
        """Handle a user query"""
        print()  # Blank line
        
        # Determine collection based on mode
        collection_name = None
        if self.config.get('collection_mode') == 'auto':
            # Use router to auto-detect
            routing_info = self.collection_router.route_with_confidence(query)
            collection_name = routing_info['collection']
            confidence = routing_info['confidence']
            
            # Show collection info if enabled
            if self.config.get('show_collection'):
                collection_type = "Project" if "knowledge" in collection_name else "Company"
                print(f"🔍 Querying {collection_type} data (confidence: {confidence:.0%})")
        elif self.config.get('collection_mode') == 'project':
            collection_name = 'propintel_knowledge'
            if self.config.get('show_collection'):
                print("🔍 Querying Project data")
        elif self.config.get('collection_mode') == 'company':
            collection_name = 'propintel_companies'
            if self.config.get('show_collection'):
                print("🔍 Querying Company data")
        
        # Show thinking indicator
        if not self.config.get('verbose'):
            self.formatter.print_thinking()
        
        try:
            # Set collection in generator's retriever if available
            if collection_name and hasattr(self.generator, 'orchestrator'):
                if hasattr(self.generator.orchestrator, 'retriever'):
                    self.generator.orchestrator.retriever.switch_collection(collection_name)
            
            # Generate answer
            result = self.generator.generate_answer(
                query=query,
                template_name=self.config.get('template', 'default')
            )
            
            # Add collection info to result
            if collection_name:
                if 'metadata' not in result:
                    result['metadata'] = {}
                result['metadata']['collection'] = collection_name
            
            # Clear thinking indicator
            if not self.config.get('verbose'):
                print("\r" + " " * 50 + "\r", end="")
            
            # Save to session
            self.session.add_interaction(query, result)
            
            # Display result
            self._display_result(result)
            
        except Exception as e:
            self.formatter.print_error(f"Error generating answer: {e}")
            if self.config.get('verbose'):
                import traceback
                traceback.print_exc()
    
    def _display_result(self, result: Dict[str, Any]):
        """Display the answer result"""
        if result.get('answer'):
            # Print answer
            self.formatter.print_answer(result['answer'])
            
            # Print sources if enabled
            if self.config.get('show_sources') and result.get('sources'):
                self.formatter.print_sources(result['sources'])
            
            # Print metadata if enabled
            if self.config.get('show_metadata') and result.get('metadata'):
                self.formatter.print_metadata(result['metadata'])
        else:
            self.formatter.print_error(result.get('error', 'Unknown error'))
        
        print()  # Blank line
    
    def _handle_command(self, command: str):
        """Handle a CLI command"""
        cmd = command.lower().strip()
        
        if cmd == '/help':
            self._cmd_help()
        elif cmd == '/history':
            self._cmd_history()
        elif cmd == '/stats':
            self._cmd_stats()
        elif cmd == '/clear':
            self._cmd_clear()
        elif cmd == '/config':
            self._cmd_config()
        elif cmd.startswith('/config '):
            self._cmd_config_set(cmd)
        elif cmd == '/export':
            self._cmd_export()
        elif cmd in ['/exit', '/quit', '/q']:
            self._cmd_exit()
        elif cmd == '/verbose':
            self._cmd_verbose()
        elif cmd.startswith('/template '):
            self._cmd_template(cmd)
        elif cmd.startswith('/provider '):
            self._cmd_provider(cmd)
        elif cmd.startswith('/mode '):
            self._cmd_mode(cmd)
        elif cmd == '/collections':
            self._cmd_collections()
        else:
            self.formatter.print_error(f"Unknown command: {command}")
            print("Type /help for available commands.")
            print()
    
    def _cmd_help(self):
        """Show help message"""
        help_text = """
╔══════════════════════════════════════════════════════════════════════════╗
║                         PROPINTEL CLI COMMANDS                           ║
╚══════════════════════════════════════════════════════════════════════════╝

BASIC USAGE:
  Just type your question and press Enter
  Example: What are the specializations of Astha?

COMMANDS:
  /help              Show this help message
  /history           Show conversation history
  /stats             Show pipeline statistics
  /collections       Show available collections and their info
  /clear             Clear conversation history
  /export            Export session to file
  /verbose           Toggle verbose mode
  /exit, /quit, /q   Exit the application

CONFIGURATION:
  /config                      Show current configuration
  /config <key> <value>        Set configuration value
  /template <name>             Set prompt template (default/detailed/concise/conversational)
  /provider <name>             Set LLM provider (groq/openai/gemini)
  /mode <type>                 Set collection mode (auto/company/project)

CONFIGURATION KEYS:
  show_sources      Show source documents (true/false)
  show_metadata     Show response metadata (true/false)
  show_collection   Show which collection is queried (true/false)
  collection_mode   Collection routing mode (auto/company/project)
  verbose           Show detailed logs (true/false)

EXAMPLES:
  What does Astha specialize in?
  Tell me about Kabi Tirtha project
  How many floors in Urban Residency?
  What upcoming projects are there?
  /mode project
  /collections
  /template detailed
  /config show_sources false
  /history

TIPS:
  • Press Ctrl+C or Ctrl+D to exit
  • Use /clear to start a fresh conversation
  • Use /stats to see performance metrics
  • Try different templates for varied responses

╚══════════════════════════════════════════════════════════════════════════╝
"""
        print(help_text)
    
    def _cmd_history(self):
        """Show conversation history"""
        history = self.session.get_history()
        
        if not history:
            print("\n📝 No conversation history yet.\n")
            return
        
        print("\n" + "═" * 80)
        print("📝 CONVERSATION HISTORY")
        print("═" * 80 + "\n")
        
        for i, interaction in enumerate(history, 1):
            print(f"[{i}] {interaction['timestamp']}")
            print(f"Q: {interaction['query']}")
            if interaction.get('answer'):
                preview = interaction['answer'][:100]
                if len(interaction['answer']) > 100:
                    preview += "..."
                print(f"A: {preview}")
            print()
    
    def _cmd_stats(self):
        """Show pipeline statistics"""
        if not self.generator:
            self.formatter.print_error("Generator not initialized")
            return
        
        gen_stats = self.generator.get_stats()
        llm_stats = self.generator.llm.stats
        
        print("\n" + "═" * 80)
        print("📊 PIPELINE STATISTICS")
        print("═" * 80 + "\n")
        
        print("GENERATOR STATISTICS")
        print("-" * 40)
        print(f"Total Queries:       {gen_stats['total_queries']}")
        print(f"Successful:          {gen_stats['successful']}")
        print(f"Failed:              {gen_stats['failed']}")
        if gen_stats['total_queries'] > 0:
            print(f"Avg Response Time:   {gen_stats['avg_response_time']:.2f}s")
            print(f"Total Tokens:        {gen_stats['total_tokens']:,}")
        
        print("\nLLM STATISTICS")
        print("-" * 40)
        print(f"Provider:            {self.config['provider']}")
        print(f"Total Requests:      {llm_stats['total_requests']}")
        print(f"Successful:          {llm_stats['successful_requests']}")
        if llm_stats['total_requests'] > 0:
            success_rate = llm_stats['successful_requests'] / llm_stats['total_requests'] * 100
            print(f"Success Rate:        {success_rate:.1f}%")
            print(f"Total Tokens:        {llm_stats['total_tokens']:,}")
        
        print("\nSESSION STATISTICS")
        print("-" * 40)
        print(f"Interactions:        {len(self.session.get_history())}")
        print(f"Session Started:     {self.session.start_time}")
        
        print("\n" + "═" * 80 + "\n")
    
    def _cmd_clear(self):
        """Clear conversation history"""
        self.session.clear()
        self.formatter.print_success("Conversation history cleared!")
        print()
    
    def _cmd_config(self):
        """Show current configuration"""
        print("\n" + "═" * 80)
        print("⚙️  CURRENT CONFIGURATION")
        print("═" * 80 + "\n")
        
        for key, value in self.config.items():
            print(f"{key:20} : {value}")
        
        print("\n" + "═" * 80 + "\n")
    
    def _cmd_config_set(self, command: str):
        """Set configuration value"""
        parts = command.split(maxsplit=2)
        if len(parts) < 3:
            self.formatter.print_error("Usage: /config <key> <value>")
            return
        
        key = parts[1]
        value = parts[2]
        
        # Convert value type
        if value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        elif value.isdigit():
            value = int(value)
        
        self.config[key] = value
        self._save_config()
        self.formatter.print_success(f"Configuration updated: {key} = {value}")
        print()
    
    def _cmd_export(self):
        """Export session to file"""
        filename = self.session.export()
        if filename:
            self.formatter.print_success(f"Session exported to: {filename}")
        else:
            self.formatter.print_error("Failed to export session")
        print()
    
    def _cmd_verbose(self):
        """Toggle verbose mode"""
        self.config['verbose'] = not self.config.get('verbose', False)
        self._save_config()
        status = "enabled" if self.config['verbose'] else "disabled"
        self.formatter.print_success(f"Verbose mode {status}")
        print()
    
    def _cmd_template(self, command: str):
        """Set prompt template"""
        parts = command.split()
        if len(parts) < 2:
            self.formatter.print_error("Usage: /template <name>")
            print("Available: default, detailed, concise, conversational")
            return
        
        template = parts[1]
        valid_templates = ['default', 'detailed', 'concise', 'conversational']
        
        if template not in valid_templates:
            self.formatter.print_error(f"Invalid template: {template}")
            print(f"Available: {', '.join(valid_templates)}")
            return
        
        self.config['template'] = template
        self._save_config()
        self.formatter.print_success(f"Template set to: {template}")
        print()
    
    def _cmd_provider(self, command: str):
        """Set LLM provider"""
        parts = command.split()
        if len(parts) < 2:
            self.formatter.print_error("Usage: /provider <name>")
            print("Available: groq, openai, gemini")
            return
        
        provider = parts[1].lower()
        valid_providers = ['groq', 'openai', 'gemini']
        
        if provider not in valid_providers:
            self.formatter.print_error(f"Invalid provider: {provider}")
            print(f"Available: {', '.join(valid_providers)}")
            return
        
        self.config['provider'] = provider
        self._save_config()
        
        # Reinitialize generator with new provider
        print("Reinitializing with new provider...")
        if self.initialize_generator():
            self.formatter.print_success(f"Provider set to: {provider}")
        else:
            self.formatter.print_error(f"Failed to initialize {provider}")
        print()
    
    def _cmd_exit(self):
        """Exit the application"""
        print()
        self.formatter.print_success("Thank you for using PropIntel! Goodbye! 👋")
        print()
        self.running = False
    
    def _cmd_mode(self, command: str):
        """Set collection mode"""
        parts = command.split()
        if len(parts) < 2:
            self.formatter.print_error("Usage: /mode <type>")
            print("Available modes: auto, company, project")
            return
        
        mode = parts[1].lower()
        valid_modes = ['auto', 'company', 'project']
        
        if mode not in valid_modes:
            self.formatter.print_error(f"Invalid mode: {mode}")
            print(f"Available: {', '.join(valid_modes)}")
            return
        
        self.config['collection_mode'] = mode
        self._save_config()
        
        mode_desc = {
            'auto': 'Auto-detect (company or project based on query)',
            'company': 'Always query company data',
            'project': 'Always query project data'
        }
        
        self.formatter.print_success(f"Collection mode: {mode}")
        print(f"  → {mode_desc[mode]}")
        print()
    
    def _cmd_collections(self):
        """Show available collections and their information"""
        if not self.generator:
            self.formatter.print_error("Generator not initialized")
            return
        
        print("\n" + "═" * 80)
        print("📚 AVAILABLE COLLECTIONS")
        print("═" * 80 + "\n")
        
        try:
            # Get collections info from retriever
            if hasattr(self.generator, 'orchestrator'):
                if hasattr(self.generator.orchestrator, 'retriever'):
                    retriever = self.generator.orchestrator.retriever
                    collections = retriever.list_available_collections()
                    
                    for col_name in collections:
                        info = retriever.db_manager.get_collection_info(col_name)
                        
                        # Determine collection type
                        col_type = "Project" if "knowledge" in col_name else "Company"
                        
                        print(f"📁 {col_name}")
                        print(f"   Type:      {col_type} Data")
                        print(f"   Documents: {info.get('count', 0)}")
                        print(f"   Status:    {'✓ Active' if info.get('has_documents') else '✗ Empty'}")
                        print()
                    
                    # Show current mode
                    current_mode = self.config.get('collection_mode', 'auto')
                    print(f"Current Mode: {current_mode}")
                    print(f"Use /mode <auto|company|project> to change")
                else:
                    self.formatter.print_error("Retriever not available")
            else:
                self.formatter.print_error("Orchestrator not available")
        
        except Exception as e:
            self.formatter.print_error(f"Error getting collections: {e}")
            if self.config.get('verbose'):
                import traceback
                traceback.print_exc()
        
        print("\n" + "═" * 80 + "\n")


def main():
    """Main entry point"""
    cli = PropIntelCLI()
    cli.start()


if __name__ == "__main__":
    main()
