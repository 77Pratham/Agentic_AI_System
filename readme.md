# Agentic AI System

A powerful AI agent built with **LangGraph + LangChain + Gemini + Tavily + Streamlit** that performs intelligent research, executes code, generates insights, and exports beautiful PDF reports.

## Features

✨ **Three Operating Modes:**
- **🔍 Web Search**: Quick real-time web search for news, facts, and current information
- **⚙️ Code Execution**: Generate and execute Python code for calculations and algorithms
- **🔬 Deep Research**: Comprehensive multi-angle research with web scraping and AI-powered report generation

📊 **Deep Research Capabilities:**
- Breaks questions into 5 sub-questions covering different angles
- Performs parallel Tavily searches
- Scrapes top web pages for detailed content
- Generates professional markdown reports
- Exports polished PDF reports with cover page

👥 **Human-in-the-Loop:**
- Review and approve/reject agent responses
- Provide corrections and rerun with feedback
- Maintain conversation history

📄 **PDF Reports:**
- Beautiful dark-themed design with accent colors
- Cover page with research metadata
- White text for excellent readability
- Structured sections with headings and bullet points
- Source citations and research angles covered

## Architecture

```
User Question
     │
     ▼
 [Planner] ─────────┬──────────┬──────────┐
                    │          │          │
                "search"    "code"   "deep_research"
                    │          │          │
                    ▼          ▼          ▼
                [Search]  [CodeWriter] [QueryPlanner]
                (Tavily)      │             │
                    │         ▼             ▼
                    │    [CodeExecutor]  [MultiSearcher]
                    │    [SelfCorrect]       │
                    │         │              ▼
                    │         │          [WebScraper]
                    └─────┬───┘              │
                          ▼                  ▼
                   [ResponseGenerator]  [ReportWriter]
                          │                  │
                          └──────┬───────────┘
                                 ▼
                          Final Answer (UI)
                                 │
                          ┌──────┴──────┐
                          ▼             ▼
                     [Download PDF]  [Feedback Loop]
```

## Setup

### 1. Clone and enter directory
```bash
git clone https://github.com/77Pratham/Agentic-AI-System.git
cd Agentic-AI-System
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate           # Windows
source venv/bin/activate        # macOS/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Get API keys
- **Gemini API**: https://aistudio.google.com/app/apikey
- **Tavily API**: https://app.tavily.com (free tier available)

### 5. Create .env file
```
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxx
```

### 6. Run the app
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

## Usage

### Quick Search
- Ask a factual question: "Who won the 2024 Nobel Prize in Physics?"
- Get instant web search results

### Code Execution
- Ask for calculations: "Calculate compound interest ₹10000 at 8% for 5 years"
- Agent generates and runs Python code

### Deep Research
- Toggle "🔬 Deep Research Mode"
- Ask comprehensive questions: "Impact of AI on the job market in 2024"
- Get a multi-page research report with sources
- Download as beautifully formatted PDF

### Human Feedback
- Review the agent's answer
- Click "👍 Looks good" to approve or "👎 Not right" to correct
- Provide corrections, agent re-runs with your feedback
- View full conversation history

## Project Structure

```
Agentic_AI_System/
├── agent.py              # Core LangGraph agent pipeline
├── app.py                # Streamlit UI with feedback loop
├── report_pdf.py         # PDF generation with styling
├── requirements.txt      # Dependencies
├── .gitignore
└── README.md
```

## Key Components

| Component | Purpose |
|---|---|
| `planner()` | Routes to search/code/deep-research |
| `search_node()` | Tavily web search with normalization |
| `code_writer()` | Generates Python code via Gemini |
| `code_executor()` | Executes code safely with subprocess |
| `self_correct()` | Retries failed code up to 3 times |
| `response_generator()` | Formats and synthesizes answers |
| `query_planner()` | Creates 5 sub-questions for deep research |
| `multi_searcher()` | Parallel searches with error handling |
| `web_scraper()` | Scrapes pages with ThreadPoolExecutor |
| `report_writer()` | Generates AI-powered markdown reports |
| `generate_pdf()` | Renders polished PDF reports |

## Error Handling

- ✅ Safe code execution with subprocess timeout
- ✅ Retry logic for code failures (up to 3 attempts)
- ✅ Search result normalization
- ✅ Graceful web scraping with timeout and error recovery
- ✅ Defensive iteration guards against unexpected data types

## Dependencies

- `langchain-google-genai` - Gemini LLM
- `langchain-tavily` - Web search
- `langgraph` - Agent orchestration
- `streamlit` - UI
- `reportlab` - PDF generation
- `pypdf` - PDF merging
- `requests` + `beautifulsoup4` - Web scraping

## Testing

Try these examples:

**Web Search:**
- "Who won the 2024 Nobel Prize in Physics?"
- "What are the latest developments in quantum computing?"

**Code Execution:**
- "Calculate compound interest ₹10000 at 8% for 5 years"
- "Find all prime numbers between 1 and 50"

**Deep Research:**
- "Impact of AI on the job market in 2024"
- "Compare renewable energy sources: solar, wind, hydro"

## CLI Usage (without UI)

```bash
python agent.py
# Enter question and deep_research preference
# Returns JSON output with answer, sources, and research data
```

## License

MIT

## Author

Pratham R

---

**Built during internship at ROOMAN**
