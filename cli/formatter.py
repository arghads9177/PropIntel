"""
CLI Formatter for PropIntel

Provides rich formatted output for the command-line interface.
"""

from typing import List, Dict, Any
import sys


class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'


class CLIFormatter:
    """
    Formatter for CLI output with colors and formatting.
    
    Provides methods for printing formatted messages, answers,
    sources, and metadata.
    """
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize formatter.
        
        Args:
            use_colors: Whether to use ANSI colors (disable for non-terminal output)
        """
        self.use_colors = use_colors and sys.stdout.isatty()
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled"""
        if self.use_colors:
            return f"{color}{text}{Colors.RESET}"
        return text
    
    def print_banner(self):
        """Print welcome banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║                     🏡  PropIntel CLI Assistant                          ║
║                                                                          ║
║              Real Estate Intelligence at Your Fingertips                 ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
        print(self._colorize(banner, Colors.BRIGHT_CYAN))
        print(self._colorize("Version 1.0 - Phase 4D: CLI Interface", Colors.DIM))
        print(self._colorize("Powered by RAG (Retrieval-Augmented Generation)", Colors.DIM))
        print()
    
    def format_prompt(self) -> str:
        """Format the input prompt"""
        prompt = "You: "
        return self._colorize(prompt, Colors.BRIGHT_GREEN + Colors.BOLD)
    
    def print_thinking(self):
        """Print thinking indicator"""
        message = "🤔 Thinking..."
        print(self._colorize(message, Colors.BRIGHT_YELLOW), end='\r', flush=True)
    
    def print_answer(self, answer: str):
        """Print the assistant's answer"""
        print(self._colorize("PropIntel:", Colors.BRIGHT_CYAN + Colors.BOLD))
        print()
        
        # Format answer text
        lines = answer.split('\n')
        for line in lines:
            if line.strip().startswith('**') and line.strip().endswith('**'):
                # Bold headers
                print(self._colorize(line, Colors.BOLD))
            elif line.strip().startswith('-') or line.strip().startswith('•'):
                # List items
                print(self._colorize(line, Colors.BRIGHT_WHITE))
            else:
                print(line)
        print()
    
    def print_sources(self, sources: List[Dict[str, Any]]):
        """Print source documents"""
        if not sources:
            return
        
        print(self._colorize("─" * 80, Colors.DIM))
        print(self._colorize("📚 Sources:", Colors.BRIGHT_MAGENTA + Colors.BOLD))
        print()
        
        for i, source in enumerate(sources[:3], 1):  # Show top 3 sources
            section = source.get('metadata', {}).get('section', 'Unknown')
            score = source.get('score', 0)
            content = source.get('content', '')[:100] + "..."
            
            print(self._colorize(f"[{i}] {section}", Colors.BRIGHT_MAGENTA))
            print(f"    Score: {score:.3f}")
            print(self._colorize(f"    {content}", Colors.DIM))
            print()
    
    def print_metadata(self, metadata: Dict[str, Any]):
        """Print response metadata"""
        print(self._colorize("─" * 80, Colors.DIM))
        print(self._colorize("ℹ️  Metadata:", Colors.BRIGHT_BLUE + Colors.BOLD))
        
        provider = metadata.get('provider', 'Unknown')
        response_time = metadata.get('response_time', 0)
        tokens = metadata.get('tokens_used', 0)
        query_type = metadata.get('query_type', 'Unknown')
        
        print(f"  Provider: {self._colorize(provider, Colors.BRIGHT_BLUE)}")
        print(f"  Response Time: {self._colorize(f'{response_time:.2f}s', Colors.BRIGHT_BLUE)}")
        
        if tokens:
            print(f"  Tokens: {self._colorize(str(tokens), Colors.BRIGHT_BLUE)}")
        
        if query_type and query_type != 'None':
            print(f"  Query Type: {self._colorize(query_type, Colors.BRIGHT_BLUE)}")
    
    def print_success(self, message: str):
        """Print success message"""
        icon = "✅"
        print(self._colorize(f"{icon} {message}", Colors.BRIGHT_GREEN))
    
    def print_error(self, message: str):
        """Print error message"""
        icon = "❌"
        print(self._colorize(f"{icon} {message}", Colors.BRIGHT_RED))
    
    def print_warning(self, message: str):
        """Print warning message"""
        icon = "⚠️"
        print(self._colorize(f"{icon} {message}", Colors.BRIGHT_YELLOW))
    
    def print_info(self, message: str):
        """Print info message"""
        icon = "ℹ️"
        print(self._colorize(f"{icon} {message}", Colors.BRIGHT_BLUE))
    
    def print_table(self, headers: List[str], rows: List[List[str]]):
        """Print a formatted table"""
        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Print header
        header_line = " | ".join(
            h.ljust(col_widths[i]) for i, h in enumerate(headers)
        )
        print(self._colorize(header_line, Colors.BOLD))
        
        # Print separator
        separator = "-+-".join("-" * w for w in col_widths)
        print(self._colorize(separator, Colors.DIM))
        
        # Print rows
        for row in rows:
            row_line = " | ".join(
                str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
            )
            print(row_line)
    
    def print_box(self, title: str, content: str, color: str = Colors.BRIGHT_CYAN):
        """Print content in a box"""
        width = 78
        
        # Top border
        print(self._colorize("╔" + "═" * width + "╗", color))
        
        # Title
        padding = (width - len(title)) // 2
        title_line = "║" + " " * padding + title + " " * (width - padding - len(title)) + "║"
        print(self._colorize(title_line, color + Colors.BOLD))
        
        # Separator
        print(self._colorize("╠" + "═" * width + "╣", color))
        
        # Content
        for line in content.split('\n'):
            # Wrap long lines
            while len(line) > width - 2:
                print(self._colorize(f"║ {line[:width-2]} ║", color))
                line = line[width-2:]
            padding_right = width - len(line) - 2
            print(self._colorize(f"║ {line}{' ' * padding_right} ║", color))
        
        # Bottom border
        print(self._colorize("╚" + "═" * width + "╝", color))
