# PropIntel CLI - User Guide

## Overview

The PropIntel CLI (Command-Line Interface) provides an interactive terminal-based interface for querying the PropIntel RAG system. It offers a rich, user-friendly experience with colored output, conversation history, and extensive configuration options.

---

## Quick Start

### Installation

No additional installation needed if you have the PropIntel project set up.

### Launch the CLI

```bash
# From project root
python propintel.py

# Or directly
python -m cli.propintel_cli
```

### First Query

Once the CLI starts, simply type your question:

```
You: What are the specializations of Astha?
```

Press Enter and wait for the response!

---

## Features

### ✨ Interactive Chat
- Natural conversation flow
- Context-aware responses
- Real-time answer generation

### 🎨 Rich Formatting
- Color-coded output
- Structured answer display
- Clear source attribution
- Metadata visualization

### 📝 Session Management
- Automatic conversation history
- Session persistence
- Export functionality

### ⚙️ Configurable
- Multiple LLM providers
- Different prompt templates
- Customizable output verbosity
- Persistent configuration

---

## Command Reference

### Basic Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message with all commands |
| `/exit`, `/quit`, `/q` | Exit the application |
| `/clear` | Clear conversation history |

### Information Commands

| Command | Description |
|---------|-------------|
| `/history` | Show conversation history |
| `/stats` | Show pipeline statistics |
| `/config` | Show current configuration |

### Configuration Commands

| Command | Example | Description |
|---------|---------|-------------|
| `/template <name>` | `/template detailed` | Set prompt template |
| `/provider <name>` | `/provider openai` | Set LLM provider |
| `/config <key> <value>` | `/config show_sources false` | Set config value |
| `/verbose` | `/verbose` | Toggle verbose mode |

### Data Commands

| Command | Description |
|---------|-------------|
| `/export` | Export session to JSON file |

---

## Prompt Templates

Choose different templates for varied response styles:

### 1. **default** (Balanced)
Professional, informative responses with good detail.

**Example:**
```
/template default
What does Astha do?
```

### 2. **detailed** (Comprehensive)
In-depth answers with extensive information and context.

**Example:**
```
/template detailed
Tell me about Astha company
```

### 3. **concise** (Brief)
Short, to-the-point answers without extra detail.

**Example:**
```
/template concise
Where does Astha operate?
```

### 4. **conversational** (Friendly)
Natural, friendly tone for casual queries.

**Example:**
```
/template conversational
How can I contact Astha?
```

---

## LLM Providers

Switch between different AI providers:

### 1. **groq** (Default - Fastest)
- Model: llama-3.3-70b-versatile
- Speed: ~1.5 seconds
- Best for: Quick responses

**Usage:**
```
/provider groq
```

### 2. **openai** (Highest Quality)
- Model: gpt-3.5-turbo (configurable)
- Speed: ~2.8 seconds
- Best for: High-quality answers

**Usage:**
```
/provider openai
```

### 3. **gemini** (Balanced)
- Model: gemini-pro
- Speed: ~2.2 seconds  
- Best for: Balance of speed and quality

**Usage:**
```
/provider gemini
```

---

## Configuration Options

### View Configuration
```
/config
```

Output:
```
⚙️  CURRENT CONFIGURATION
provider             : groq
model                : None
template             : default
show_sources         : True
show_metadata        : True
verbose              : False
max_history          : 50
```

### Set Configuration

**Syntax:**
```
/config <key> <value>
```

**Examples:**
```
/config show_sources false      # Hide sources
/config show_metadata true      # Show metadata
/config verbose true            # Enable verbose mode
/config max_history 100         # Increase history limit
```

### Available Config Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `provider` | string | groq | LLM provider (groq/openai/gemini) |
| `model` | string | None | Specific model (optional) |
| `template` | string | default | Prompt template |
| `show_sources` | boolean | true | Show source documents |
| `show_metadata` | boolean | true | Show response metadata |
| `verbose` | boolean | false | Show detailed logs |
| `max_history` | integer | 50 | Max history entries |

---

## Example Sessions

### Session 1: Basic Information Query

```
You: What are the specializations of Astha?

PropIntel:

According to the context, the specializations of Astha Infra Realty Ltd. are:
1. Residential Complexes
2. Commercial Buildings
3. Townships
4. Apartment Buildings
5. Shopping Malls
6. Office Buildings
7. Hospitality & Clubs

────────────────────────────────────────────────────────────────────────────────
📚 Sources:

[1] company_info/specializations
    Score: 0.640
    Preview: Specializations and Services offered by Astha Infra Realty Ltd.:
    - Residential Complexes...

────────────────────────────────────────────────────────────────────────────────
ℹ️  Metadata:
  Provider: groq - llama-3.3-70b-versatile
  Response Time: 2.94s
  Tokens: 455
  Query Type: specialization
```

### Session 2: Using Different Template

```
You: /template concise

✅ Template set to: concise

You: Where does Astha operate?

PropIntel:

Astha Infra Realty Ltd. operates in:
- Asansol
- Bandel
- Hooghly
```

### Session 3: Configuration and Stats

```
You: /config show_metadata false

✅ Configuration updated: show_metadata = False

You: /stats

📊 PIPELINE STATISTICS

GENERATOR STATISTICS
────────────────────────────────────────────────
Total Queries:       5
Successful:          5
Failed:              0
Avg Response Time:   1.87s
Total Tokens:        1,471

LLM STATISTICS
────────────────────────────────────────────────
Provider:            groq
Total Requests:      5
Successful:          5
Success Rate:        100.0%
Total Tokens:        1,471

SESSION STATISTICS
────────────────────────────────────────────────
Interactions:        5
Session Started:     2025-11-18 20:50:00
```

---

## Tips & Tricks

### 1. Quick Commands
Use keyboard shortcuts for faster navigation:
- **Ctrl+C** or **Ctrl+D**: Quick exit
- **Up/Down Arrow**: Navigate command history (terminal feature)

### 2. Minimize Output
For cleaner output, hide sources and metadata:
```
/config show_sources false
/config show_metadata false
```

### 3. Switch Providers for Speed
Use Groq for quick answers:
```
/provider groq
```

Use OpenAI for best quality:
```
/provider openai
```

### 4. Export Your Session
Save your conversation for later:
```
/export
```

This creates a JSON file in `exports/` directory with all interactions.

### 5. Clear History for Fresh Start
```
/clear
```

### 6. Debug Mode
Enable verbose mode to see detailed logs:
```
/verbose
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Interrupt/Exit |
| `Ctrl+D` | Exit (EOF) |
| `Ctrl+L` | Clear screen (terminal) |
| `↑` / `↓` | Command history (terminal) |

---

## Output Format

### Answer Structure

```
PropIntel:              ← Assistant identifier
                        ← Blank line
Answer text here...     ← Main answer
More details...         ← Continued answer
                        ← Blank line
────────────────────    ← Separator
📚 Sources:             ← Source documents (if enabled)
                        ← Blank line
────────────────────    ← Separator  
ℹ️  Metadata:           ← Response metadata (if enabled)
```

### Color Coding

- **Green**: Success messages, user prompt
- **Cyan**: Assistant responses, titles
- **Magenta**: Sources
- **Blue**: Metadata, info messages
- **Yellow**: Warnings, thinking indicator
- **Red**: Errors
- **Gray**: Separators, dimmed text

---

## Troubleshooting

### Problem: CLI won't start

**Solution:**
```bash
# Check Python path
python --version

# Try with python3
python3 propintel.py

# Or run module directly
python -m cli.propintel_cli
```

### Problem: "Failed to initialize generator"

**Possible causes:**
1. Missing API keys in `.env` file
2. ChromaDB not initialized

**Solution:**
```bash
# Check .env file has API keys
cat .env | grep API_KEY

# Re-run data ingestion if needed
python ingestion/run_data_ingestion.py --data-dir data/processed --embedding-model openai
```

### Problem: No answers returned

**Check:**
1. Is ChromaDB populated? Run `/stats` to see
2. Try different queries
3. Enable verbose mode: `/verbose`

### Problem: Colors not showing

Terminal may not support ANSI colors. The CLI will automatically disable colors for non-TTY output.

---

## Advanced Usage

### Session Export Format

Exported sessions are saved as JSON:

```json
{
  "session_id": "20251118_205000",
  "start_time": "2025-11-18 20:50:00",
  "export_time": "2025-11-18 21:00:00",
  "total_interactions": 5,
  "history": [
    {
      "timestamp": "2025-11-18 20:50:15",
      "query": "What does Astha do?",
      "answer": "Astha specializes in...",
      "success": true,
      "metadata": {
        "provider": "groq - llama-3.3-70b-versatile",
        "response_time": 2.5,
        "tokens": 450,
        "sources_count": 3
      }
    }
  ]
}
```

### Configuration File

Configuration is auto-saved to `cli/config.json`:

```json
{
  "provider": "groq",
  "model": null,
  "template": "default",
  "show_sources": true,
  "show_metadata": true,
  "verbose": false,
  "max_history": 50
}
```

---

## Best Practices

1. **Start with default settings** - They're optimized for best experience
2. **Use /help frequently** - Discover new features
3. **Export important sessions** - Keep records of useful conversations
4. **Try different templates** - Find what works for your queries
5. **Monitor /stats** - Track performance and usage

---

## Support

For issues or questions:
- Check documentation in `docs/`
- Review test suite: `python cli/test_cli.py`
- See Phase 4D completion docs

---

**Version:** 1.0  
**Phase:** 4D - CLI Interface  
**Last Updated:** November 18, 2025
