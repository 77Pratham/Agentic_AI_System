# Agentic AI System — Bootcamp Assignment

A working AI agent built with **LangGraph + LangChain + Gemini + Tavily + Streamlit**.

## Architecture

```
User Question
     │
     ▼
 [Planner]  ──── decides ────┐
     │                       │
  "search"                "code"
     │                       │
     ▼                       ▼
 [Search]            [Code Writer]
  (Tavily)                   │
     │                       ▼
     │              [Code Executor]
     │                (subprocess)
     └──────┬────────────────┘
            ▼
   [Response Generator]
            │
            ▼
      Final Answer (UI)
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Get API keys

- **Gemini API key**: https://aistudio.google.com/app/apikey
- **Tavily API key**: https://app.tavily.com (free tier available)

### 4. Set up environment variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

Then edit `.env`:

```
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxx
```

### 5. Run the app

```bash
streamlit run app.py
```

The UI will open at `http://localhost:8501`.

---

## File Structure

```
agentic_ai_agent/
├── agent.py          # Core LangGraph agent (all 5 nodes)
├── app.py            # Streamlit UI
├── requirements.txt  # Python dependencies
├── .env.example      # Environment variable template
└── README.md         # This file
```

## Component Summary

| Component | File | What it does |
|---|---|---|
| Planner | `agent.py` → `planner()` | Decides: search or code |
| Search Tool | `agent.py` → `search_node()` | Queries Tavily web search |
| Code Writer | `agent.py` → `code_writer()` | Generates Python code via Gemini |
| Code Executor | `agent.py` → `code_executor()` | Runs code safely with subprocess |
| Response Generator | `agent.py` → `response_generator()` | Formats final answer |

## Testing the Agent

Try these query types:

| Type | Example |
|---|---|
| Web search | "What is the latest news about OpenAI?" |
| Calculation | "Calculate compound interest for ₹50,000 at 7% for 10 years" |
| Math | "Find all prime numbers between 1 and 50" |
| Algorithm | "Sort a list [5, 2, 8, 1, 9] using bubble sort" |

## Quick CLI Test (without Streamlit)

```bash
python agent.py
```

Enter a question when prompted and see the JSON output directly.