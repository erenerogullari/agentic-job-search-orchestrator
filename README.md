# Agentic Job Search Orchestrator

> **⚠️ UNDER CONSTRUCTION**
> This project is currently in active development. Features and architectures are subject to breaking changes.

An autonomous agentic workflow built with **LangGraph** and **LangChain** that orchestrates intelligent LinkedIn searching, scraping, and resume-matching to automate your job hunt.

### 🚀 Overview
This agent acts as a personal technical recruiter. Instead of manually scrolling through hundreds of listings, the orchestrator:
1.  **Ingests** your resume (PDF) and job preferences.
2.  **Formulates** optimized search strategies and queries.
3.  **Discovers** job listings on LinkedIn using autonomous browser tools.
4.  **Evaluates** fit by scoring job descriptions against your specific "Candidate DNA."

### 🛠️ Tech Stack
* **Orchestration:** [LangGraph](https://langchain-ai.github.io/langgraph/)
* **LLM Integration:** [LangChain](https://www.langchain.com/)
* **Browser Automation:** Playwright
* **Language:** Python 3.10+

### 📂 Project Structure
```text
├── src/
│   ├── agents/     # Core logic (Nodes, State, Graph)
│   ├── chains/     # LLM Prompts and Chains
│   ├── schema/     # Pydantic models (Profile, JobListing)
│   └── tools/      # Browser tools (Scrapers)
└── data/           # Local storage for resumes and output
```