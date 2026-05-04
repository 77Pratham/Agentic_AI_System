import os
import re
import json
import subprocess
import sys
import tempfile
import time
from typing import TypedDict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, END

load_dotenv()

# ─── Constants ────────────────────────────────────────────────────────────────
 
MAX_RETRIES          = 3
MAX_RESEARCH_QUERIES = 5
SCRAPE_TOP_N         = 3
SCRAPE_TIMEOUT       = 8
MAX_CHARS_PER_PAGE   = 4000

# ─── LLM & Search Tool Setup ────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0,
)

search_tool = TavilySearch(
    max_results=5,
    api_key=os.getenv("TAVILY_API_KEY"),
)


# ─── Shared Agent State ──────────────────────────────────────────────────────

class AgentState(TypedDict):
    question:         str
    action:           str
    deep_research:    bool
    search_results:   Optional[list]
    generated_code:   Optional[str]
    execution_output: Optional[str]
    execution_error:  Optional[str]
    retry_count:      int
    retry_history:    list
    answer:           Optional[str]
    sources:          Optional[list]
    research_queries: Optional[list]
    research_results: Optional[list]
    research_report:  Optional[str]
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  SHARED NODES
# ══════════════════════════════════════════════════════════════════════════════
 
def planner(state: AgentState) -> AgentState:
    if state.get("deep_research"):
        print("[Planner] → deep_research")
        return {**state, "action": "deep_research"}
 
    prompt = f"""Decide which tool to use. Reply ONE word only.
- "search"  → needs real-world info, news, facts
- "code"    → needs math, calculation, algorithms
 
Question: {state['question']}"""
 
    resp = llm.invoke(prompt)
    action = resp.content.strip().lower()
    if action not in ("search", "code"):
        action = "search"
    print(f"[Planner] → {action}")
    return {**state, "action": action}
 
 
def route_after_planner(state: AgentState) -> str:
    return state["action"]
 
 
def normalize_search_results(results):
    if isinstance(results, str):
        try:
            parsed = json.loads(results)
        except Exception:
            return []
        return normalize_search_results(parsed)
 
    if isinstance(results, dict):
        if isinstance(results.get("results"), list):
            return normalize_search_results(results["results"])
        return [results]
 
    if isinstance(results, list):
        normalized = []
        for item in results:
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, str):
                normalized.extend(normalize_search_results(item))
        return normalized
 
    return []
 
 
def search_node(state: AgentState) -> AgentState:
    print(f"[Search] {state['question']}")
    try:
        results = normalize_search_results(search_tool.invoke(state["question"]))
    except Exception as e:
        print(f"[Search] normalization failed: {e}")
        results = []
    return {**state, "search_results": results}
 
 
def response_generator(state: AgentState) -> AgentState:
    question      = state["question"]
    action        = state["action"]
    retry_count   = state.get("retry_count", 0)
    retry_history = state.get("retry_history", [])
 
    if action == "search":
        results = state.get("search_results") or []
        sources, ctx = [], []
        for r in results:
            if not isinstance(r, dict):
                continue
            url = r.get("url", "")
            content = r.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            ctx.append(f"[{url}]\n{content}")
            if url:
                sources.append(url)
        prompt = f"Answer clearly using these results.\nQuestion: {question}\n\n{chr(10).join(ctx)}\n\nWrite 3-5 sentences. Synthesise."
        answer = llm.invoke(prompt).content.strip()
        return {**state, "answer": answer, "sources": sources}
 
    else:
        out = state.get("execution_output", "")
        err = state.get("execution_error", "")
        if err and not out:
            answer = f"Code failed after {retry_count} attempt(s):\n{err}"
        elif out:
            prompt = f'User asked: "{question}"\nCode output: {out}\nSummarise in one sentence.'
            answer = llm.invoke(prompt).content.strip()
        else:
            answer = "Code ran but produced no output."
        return {**state, "answer": answer, "sources": [],
                "retry_count": retry_count, "retry_history": retry_history}
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  CODE PATH
# ══════════════════════════════════════════════════════════════════════════════
 
def code_writer(state: AgentState) -> AgentState:
    rc      = state.get("retry_count", 0)
    history = state.get("retry_history", [])
    fix = ""
    if rc > 0 and history:
        last = history[-1]
        fix = f"\nPREVIOUS CODE FAILED:\n{last['code']}\nERROR:\n{last['error']}\nFix it.\n"
 
    prompt = f"""Write Python code to answer this question.
Rules: raw Python only, no markdown, must print() the answer, stdlib only.
{fix}
Question: {state['question']}"""
 
    raw  = llm.invoke(prompt).content.strip()
    code = re.sub(r"^```(?:python)?\n?", "", raw, flags=re.MULTILINE)
    code = re.sub(r"\n?```$", "",           code, flags=re.MULTILINE).strip()
    print(f"[CodeWriter] attempt {rc+1}")
    return {**state, "generated_code": code}
 
 
def code_executor(state: AgentState) -> AgentState:
    code = state.get("generated_code", "")
    if not code:
        return {**state, "execution_output": "", "execution_error": "No code."}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code); tmp = f.name
    try:
        res = subprocess.run([sys.executable, tmp], capture_output=True, text=True, encoding="utf-8", timeout=15)
        return {**state, "execution_output": res.stdout.strip(),
                "execution_error": res.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {**state, "execution_output": "", "execution_error": "Timed out."}
    except Exception as e:
        return {**state, "execution_output": "", "execution_error": str(e)}
    finally:
        os.unlink(tmp)
 
 
def self_correct(state: AgentState) -> AgentState:
    err     = state.get("execution_error", "")
    out     = state.get("execution_output", "")
    rc      = state.get("retry_count", 0)
    history = state.get("retry_history", [])
    if err and not out and rc < MAX_RETRIES:
        new_h = history + [{"attempt": rc+1, "code": state.get("generated_code",""), "error": err}]
        print(f"[SelfCorrect] retry {rc+1}/{MAX_RETRIES}")
        return {**state, "retry_count": rc+1, "retry_history": new_h,
                "execution_output": None, "execution_error": None}
    print(f"[SelfCorrect] {'max retries' if rc >= MAX_RETRIES else 'success'}")
    return state
 
 
def route_after_executor(state: AgentState) -> str:
    if (state.get("execution_error") and not state.get("execution_output")
            and state.get("retry_count", 0) <= MAX_RETRIES):
        return "retry"
    return "done"
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  DEEP RESEARCH PATH
# ══════════════════════════════════════════════════════════════════════════════
 
def query_planner(state: AgentState) -> AgentState:
    prompt = f"""Break this question into {MAX_RESEARCH_QUERIES} specific sub-questions
covering different angles (background, stats, expert views, future outlook, comparisons etc.).
Output ONLY a JSON array of strings. No markdown.
Question: {state['question']}"""
 
    raw = llm.invoke(prompt).content.strip()
    raw = re.sub(r"^```(?:json)?\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\n?```$", "", raw, flags=re.MULTILINE).strip()
 
    try:
        queries = json.loads(raw)
        if not isinstance(queries, list):
            raise ValueError
        queries = [str(q) for q in queries[:MAX_RESEARCH_QUERIES]]
    except Exception:
        queries = [l.strip("- •1234567890.)").strip()
                   for l in raw.splitlines() if l.strip()][:MAX_RESEARCH_QUERIES]
 
    print(f"[QueryPlanner] {len(queries)} sub-questions generated")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")
    return {**state, "research_queries": queries}
 
 
def multi_searcher(state: AgentState) -> AgentState:
    queries = state.get("research_queries") or []
    results = []
    for q in queries:
        print(f"[MultiSearcher] → {q}")
        try:
            r = normalize_search_results(search_tool.invoke(q))
        except Exception as e:
            print(f"[MultiSearcher] normalization failed: {e}")
            r = []
        results.append({"query": q, "tavily_results": r, "scraped_pages": []})
        time.sleep(0.3)
    return {**state, "research_results": results}
 
 
SKIP_DOMAINS = {
    "youtube.com","youtu.be","twitter.com","x.com",
    "instagram.com","facebook.com","reddit.com",
    "linkedin.com","tiktok.com",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
 
 
def _scrape_url(url: str) -> dict:
    domain = url.split("/")[2].replace("www.", "")
    if any(s in domain for s in SKIP_DOMAINS):
        return {"url": url, "text": "", "success": False}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=SCRAPE_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script","style","nav","footer","header","aside","form","iframe","noscript"]):
            tag.decompose()
        main = (soup.find("article") or soup.find("main")
                or soup.find("div", {"id": re.compile(r"content|article|main", re.I)})
                or soup.body)
        text = main.get_text("\n", strip=True) if main else ""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)[:MAX_CHARS_PER_PAGE]
        print(f"[Scraper] ✓ {url[:65]}  ({len(text)} chars)")
        return {"url": url, "text": text, "success": bool(text)}
    except Exception as e:
        print(f"[Scraper] ✗ {url[:65]}  {e}")
        return {"url": url, "text": "", "success": False}
 
 
def web_scraper(state: AgentState) -> AgentState:
    research_results = state.get("research_results") or []
    updated = []
    for item in research_results:
        urls = [r.get("url", "") for r in item.get("tavily_results", [])
                if isinstance(r, dict) and r.get("url")][:SCRAPE_TOP_N]
        scraped = []
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(_scrape_url, u): u for u in urls}
            for f in as_completed(futures):
                res = f.result()
                if res["success"]:
                    scraped.append(res)
        item["scraped_pages"] = scraped
        updated.append(item)
    return {**state, "research_results": updated}
 
 
def report_writer(state: AgentState) -> AgentState:
    question = state["question"]
    research = state.get("research_results") or []
 
    context_blocks = []
    all_sources    = []
 
    for item in research:
        sub_q = item["query"]
        block = [f"\n### Sub-question: {sub_q}"]
 
        for page in item.get("scraped_pages", []):
            block.append(f"\n**Full page — {page['url']}**\n{page['text']}")
            all_sources.append({"url": page["url"], "query": sub_q, "type": "scraped"})
 
        for r in item.get("tavily_results", []):
            url = r.get("url","")
            snip = r.get("content","")
            if url and snip:
                block.append(f"\n**Snippet — {url}**\n{snip}")
                if not any(s["url"] == url for s in all_sources):
                    all_sources.append({"url": url, "query": sub_q, "type": "snippet"})
 
        context_blocks.append("\n".join(block))
 
    full_ctx = "\n\n".join(context_blocks)
    if len(full_ctx) > 32000:
        full_ctx = full_ctx[:32000] + "\n\n[... trimmed ...]"
 
    prompt = f"""You are an expert research analyst. Write a comprehensive research report.
Use ONLY the sources provided. Do not invent facts. Be specific — use numbers and data.
 
===== RESEARCH QUESTION =====
{question}
 
===== SOURCES =====
{full_ctx}
 
===== FORMAT =====
Write in markdown:
## Executive Summary
(3-4 sentence overview)
 
## Key Findings
(bullet points of most important facts with data)
 
## Detailed Analysis
(3-4 sections with ### headings — one per major angle)
 
## Conclusion
(2-3 sentences on what this all means)
 
## Sources
(list all URLs)
 
Minimum 700 words. Synthesise — do not copy-paste."""
 
    print("[ReportWriter] Generating report …")
    report = llm.invoke(prompt).content.strip()
 
    seen, unique = set(), []
    for s in all_sources:
        if s["url"] not in seen:
            seen.add(s["url"])
            unique.append(s["url"])
 
    return {**state, "research_report": report, "answer": report, "sources": unique}
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  GRAPH ASSEMBLY
# ══════════════════════════════════════════════════════════════════════════════
 
def build_graph() -> StateGraph:
    g = StateGraph(AgentState)
 
    g.add_node("planner",            planner)
    g.add_node("search",             search_node)
    g.add_node("code_writer",        code_writer)
    g.add_node("code_executor",      code_executor)
    g.add_node("self_correct",       self_correct)
    g.add_node("response_generator", response_generator)
    g.add_node("query_planner",      query_planner)
    g.add_node("multi_searcher",     multi_searcher)
    g.add_node("web_scraper",        web_scraper)
    g.add_node("report_writer",      report_writer)
 
    g.set_entry_point("planner")
 
    g.add_conditional_edges("planner", route_after_planner, {
        "search":        "search",
        "code":          "code_writer",
        "deep_research": "query_planner",
    })
 
    g.add_edge("search",        "response_generator")
    g.add_edge("code_writer",   "code_executor")
    g.add_edge("code_executor", "self_correct")
    g.add_conditional_edges("self_correct", route_after_executor, {
        "retry": "code_writer",
        "done":  "response_generator",
    })
 
    g.add_edge("query_planner", "multi_searcher")
    g.add_edge("multi_searcher", "web_scraper")
    g.add_edge("web_scraper",    "report_writer")
 
    g.add_edge("response_generator", END)
    g.add_edge("report_writer",      END)
 
    return g.compile()
 
 
agent = build_graph()
 
 
# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
 
def run_agent(question: str, deep_research: bool = False, human_correction: str = "") -> dict:
    # If there's a human correction, append it to the question so every node sees it
    enriched_question = question
    if human_correction.strip():
        enriched_question = (
            f"{question}\n\n"
            f"[HUMAN CORRECTION]: A human reviewed the previous answer and said:\n"
            f"\"{human_correction.strip()}\"\n"
            f"Please take this feedback into account and produce a better answer."
        )
        print(f"[HumanFeedback] Correction injected: {human_correction[:80]}")
 
    initial: AgentState = {
        "question":         enriched_question,
        "action":           "",
        "deep_research":    deep_research,
        "search_results":   None,
        "generated_code":   None,
        "execution_output": None,
        "execution_error":  None,
        "answer":           None,
        "sources":          None,
        "retry_count":      0,
        "retry_history":    [],
        "research_queries": None,
        "research_results": None,
        "research_report":  None,
    }
    final = agent.invoke(initial)
    return {
        "answer":           final.get("answer") or "No answer generated.",
        "code":             final.get("generated_code") or "",
        "execution_output": final.get("execution_output") or "",
        "execution_error":  final.get("execution_error") or "",
        "sources":          final.get("sources") or [],
        "action":           final.get("action", ""),
        "retry_count":      final.get("retry_count", 0),
        "retry_history":    final.get("retry_history", []),
        "research_queries": final.get("research_queries") or [],
        "research_results": final.get("research_results") or [],
        "research_report":  final.get("research_report") or "",
    }
 
 
if __name__ == "__main__":
    import json as _j
    q   = input("Question: ")
    dr  = input("Deep research? (y/n): ").strip().lower() == "y"
    cor = input("Human correction (leave blank for none): ").strip()
    print(_j.dumps(run_agent(q, deep_research=dr, human_correction=cor), indent=2))
