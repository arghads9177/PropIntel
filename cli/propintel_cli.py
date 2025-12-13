"""
CLI Interface for PropIntel RAG System

This module provides a command-line interface for interacting with the PropIntel
real estate intelligence assistant.
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from generation.answer_generator import AnswerGenerator
from cli.session_manager import SessionManager
from cli.formatter import CLIFormatter
from retrieval.collection_router import get_router
from agentic.workflow.orchestrator import build_agentic_graph, create_initial_state
from agentic.workflow.state import AgentResponse
from agentic.agents import build_rag_agent


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
        self.config = self._load_config()
        self.session = SessionManager(max_history=self.config.get("max_history", 50))
        self.collection_router = get_router()
        self.rag_generator: Optional[AnswerGenerator] = None
        self.workflow = None
        self.workflow_memory: Dict[str, Any] = {}
        self._workflow_config: Dict[str, Any] | None = None
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
    
    def initialize_workflow(self) -> bool:
        """Initialize the LangGraph workflow executor."""
        try:
            self.rag_generator = AnswerGenerator(
                llm_provider=self.config.get('provider', 'groq'),
                llm_model=self.config.get('model')
            )
            rag_agent = build_rag_agent(answer_generator=self.rag_generator)
            self.workflow = build_agentic_graph(rag_agent=rag_agent)
            self.workflow_memory = {}
            self._workflow_config = {
                "configurable": {
                    "thread_id": self.session.session_id,
                }
            }
            return True
        except Exception as e:
            self.formatter.print_error(f"Failed to initialize workflow: {e}")
            if self.config.get('verbose'):
                import traceback

                traceback.print_exc()
            return False
    
    def start(self):
        """Start the CLI interface"""
        self.running = True
        self.formatter.print_banner()
        
        # Initialize LangGraph workflow
        if not self.initialize_workflow():
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

    def _get_workflow_config(self) -> Dict[str, Any]:
        if not self._workflow_config:
            self._workflow_config = {
                "configurable": {
                    "thread_id": self.session.session_id,
                }
            }
        return self._workflow_config

    def _invoke_workflow(self, query: str, collection_name: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Run the LangGraph workflow and return response plus routing info."""
        if not self.workflow:
            raise RuntimeError("Workflow not initialized")

        state = create_initial_state(query=query, memory=self.workflow_memory)
        state.context.update(
            {
                "template": self.config.get("template", "default"),
                "collection": collection_name,
                "flags": {
                    "show_sources": self.config.get("show_sources", True),
                    "show_metadata": self.config.get("show_metadata", True),
                },
            }
        )

        result_state = self.workflow.invoke(state, config=self._get_workflow_config())

        memory = getattr(result_state, "memory", None)
        if memory is None and isinstance(result_state, dict):
            memory = result_state.get("memory", {})
        self.workflow_memory = memory or {}

        routing = getattr(result_state, "routing", None)
        if routing is None and isinstance(result_state, dict):
            routing = result_state.get("routing", {})
        routing = routing or {}

        final_response = getattr(result_state, "final_response", None)
        if final_response is None and isinstance(result_state, dict):
            payload = result_state.get("final_response")
            if isinstance(payload, AgentResponse):
                final_response = payload
            else:
                payload = payload or {}
                final_response = AgentResponse(
                    answer=payload.get("answer"),
                    metadata=payload.get("metadata", {}),
                    sources=payload.get("sources", []),
                )

        if final_response is None:
            final_response = AgentResponse(
                answer=None,
                metadata={"agent": "orchestrator", "error": "missing_final_response"},
                sources=[],
            )

        metadata = dict(final_response.metadata or {})
        metadata.setdefault("provider", self.config.get("provider", "groq"))
        metadata["routing"] = routing

        result = {
            "answer": final_response.answer,
            "sources": final_response.sources or [],
            "metadata": metadata,
            "success": bool(final_response.answer),
        }

        return result, routing
    
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
            result, routing_info = self._invoke_workflow(query, collection_name)

            # Add collection info to result metadata
            if collection_name:
                result.setdefault('metadata', {})['collection'] = collection_name

            # Clear thinking indicator
            if not self.config.get('verbose'):
                print("\r" + " " * 50 + "\r", end="")
            
            # Save to session
            self.session.add_interaction(query, result)
            
            # Display result
            self._display_result(result, routing_info)
            
        except Exception as e:
            self.formatter.print_error(f"Error generating answer: {e}")
            if self.config.get('verbose'):
                import traceback
                traceback.print_exc()
    
    def _display_result(self, result: Dict[str, Any], routing_info: Optional[Dict[str, Any]] = None):
        """Display the answer result"""
        if routing_info:
            self._print_routing_summary(routing_info)

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

    def _print_routing_summary(self, routing_info: Dict[str, Any]):
        """Display which agents handled the request."""
        target = routing_info.get('target', 'rag')
        confidence = routing_info.get('confidence')

        if target == 'both':
            summary = 'Combined response from RAG + API agents'
        elif target == 'api':
            summary = 'Handled by API Agent'
        else:
            summary = 'Handled by RAG Agent'

        if isinstance(confidence, (int, float)):
            summary += f" (confidence: {confidence:.0%})"

        self.formatter.print_info(summary)

        intents = routing_info.get('intents') or []
        if intents:
            print(f"🔎 Detected intents: {', '.join(intents)}")

        rationale = routing_info.get('rationale')
        if rationale:
            print(f"🧠 Router note: {rationale}")
        print()
    
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
        stats = self.session.get_stats()
        
        print("\n" + "═" * 80)
        print("📊 PIPELINE STATISTICS")
        print("═" * 80 + "\n")
        
        print("SESSION OVERVIEW")
        print("-" * 40)
        print(f"Interactions:        {stats['total_interactions']}")
        print(f"Successful:          {stats['successful']}")
        print(f"Failed:              {stats['failed']}")
        if stats['total_interactions']:
            print(f"Avg Response Time:   {stats['avg_response_time']:.2f}s")
            print(f"Total Tokens:        {stats['total_tokens']:,}")
        print(f"Session Started:     {self.session.start_time}")

        print("\nRAG PIPELINE")
        print("-" * 40)
        if self.rag_generator:
            gen_stats = self.rag_generator.stats
            print(f"Total Queries:       {gen_stats['total_queries']}")
            print(f"Successful Answers:  {gen_stats['successful_answers']}")
            print(f"Failed Answers:      {gen_stats['failed_answers']}")
            print(f"Avg Response Time:   {gen_stats['average_response_time']:.2f}s")
            print(f"Total Tokens:        {gen_stats['total_tokens']:,}")

            llm_stats = getattr(self.rag_generator.llm_service, 'stats', {})
            if llm_stats:
                total_requests = llm_stats.get('total_requests', 0)
                success = llm_stats.get('successful_requests', 0)
                success_rate = (success / total_requests * 100) if total_requests else 0
                print(f"Provider:            {self.config.get('provider', 'groq')}")
                print(f"LLM Requests:        {total_requests}")
                print(f"LLM Success Rate:    {success_rate:.1f}%")
        else:
            print("Workflow not initialized")
        
        print("\nWORKFLOW STATE")
        print("-" * 40)
        workflow_status = "ready" if self.workflow else "not initialized"
        print(f"Executor:            {workflow_status}")
        last_routed = self.workflow_memory.get('history', [])[-2:] if self.workflow_memory else []
        if last_routed:
            print("Recent Turns:        " + " | ".join(item.get('content', '') for item in last_routed[-2:]))
        facts = (self.workflow_memory or {}).get('facts', {})
        if facts:
            for key, value in facts.items():
                print(f"Known {key.replace('_', ' ').title()}: {value}")
        
        print("\n" + "═" * 80 + "\n")
    
    def _cmd_clear(self):
        """Clear conversation history"""
        self.session.clear()
        self.workflow_memory = {}
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
        
        # Reinitialize workflow with new provider
        print("Reinitializing with new provider...")
        if self.initialize_workflow():
            self.formatter.print_success(f"Provider set to: {provider}")
        else:
            self.formatter.print_error(f"Failed to initialize workflow for {provider}")
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
        if not self.rag_generator:
            self.formatter.print_error("Workflow not initialized")
            return
        
        print("\n" + "═" * 80)
        print("📚 AVAILABLE COLLECTIONS")
        print("═" * 80 + "\n")
        
        try:
            retriever = getattr(self.rag_generator, 'retrieval_orchestrator', None)
            if not retriever or not hasattr(retriever, 'retriever'):
                self.formatter.print_error("Retriever not available")
                return

            retriever = retriever.retriever
            collections = retriever.list_available_collections()

            for col_name in collections:
                info = retriever.db_manager.get_collection_info(col_name)

                col_type = "Project" if "knowledge" in col_name else "Company"

                print(f"📁 {col_name}")
                print(f"   Type:      {col_type} Data")
                print(f"   Documents: {info.get('count', 0)}")
                print(f"   Status:    {'✓ Active' if info.get('has_documents') else '✗ Empty'}")
                print()

            current_mode = self.config.get('collection_mode', 'auto')
            print(f"Current Mode: {current_mode}")
            print(f"Use /mode <auto|company|project> to change")
        
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
