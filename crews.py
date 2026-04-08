"""
Mini-Assignment 4: Orchestration — Crew Definitions
=====================================================
Two CrewAI crews that execute in sequence as part of a pipeline:

  Stage 0 — Research Crew:
      1 agent  (Senior Market Research Analyst)
      1 task   (SEA e-commerce market research)
      Input:   {"topic": <topic string>}
      Output:  Comprehensive market research brief (Markdown)

  Stage 1 — Strategy Crew:
      2 agents (Market Entry Strategy Analyst + Executive Strategy Report Writer)
      2 tasks  (Strategic analysis → Executive report)
      Input:   {"previous_result": <Stage 0 output>}
      Output:  Final executive strategy report (Markdown)

The output of Stage 0 is passed as `previous_result` to Stage 1 by the
orchestrator in pipeline.py.

Usage (called from pipeline.py):
    from crews import build_research_crew, build_strategy_crew
"""

import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM

load_dotenv()


# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------

def _build_llm() -> LLM:
    """Instantiate the DeepSeek LLM from environment variables."""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key or api_key == "your_deepseek_api_key_here":
        raise EnvironmentError(
            "DEEPSEEK_API_KEY is not set or still contains the placeholder.\n"
            "Please edit .env and set your actual DeepSeek API key:\n"
            "  DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        )
    return LLM(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        base_url=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com"),
        api_key=api_key,
    )


# ---------------------------------------------------------------------------
# Stage 0 — Research Crew
# ---------------------------------------------------------------------------

def build_research_crew() -> Crew:
    """
    Build and return the Research Crew.

    One agent performs comprehensive market research on the SEA e-commerce
    landscape for a Hong Kong-based DTC brand.  The output is a structured
    Markdown research brief that feeds directly into the Strategy Crew.
    """
    llm = _build_llm()

    researcher = Agent(
        role="Senior Market Research Analyst",
        goal=(
            "Conduct comprehensive research on the Southeast Asian e-commerce "
            "market, identifying key trends, major platforms, consumer behaviour "
            "patterns, and regulatory considerations for a Hong Kong-based DTC "
            "brand entering the region."
        ),
        backstory=(
            "You are a seasoned market research analyst with 15+ years of "
            "experience in Asia-Pacific consumer markets.  You previously led "
            "the APAC research division at Euromonitor International, where you "
            "published landmark reports on e-commerce adoption in emerging "
            "Southeast Asian economies.  You have deep expertise in cross-border "
            "commerce, digital consumer behaviour, and regulatory landscapes "
            "across ASEAN nations.  Your research is known for being data-driven, "
            "nuanced, and actionable."
        ),
        llm=llm,
        verbose=True,
    )

    research_task = Task(
        description=(
            "Research the Southeast Asian e-commerce market for a Hong Kong-based "
            "DTC consumer brand considering regional expansion.  The topic is: "
            "{topic}\n\n"
            "Cover all of the following areas:\n"
            "1. Market size and growth trends for the top 5 SEA e-commerce markets "
            "(Indonesia, Thailand, Vietnam, Philippines, Malaysia)\n"
            "2. Key e-commerce platforms and their market shares (Shopee, Lazada, "
            "TikTok Shop, Tokopedia, etc.)\n"
            "3. Consumer behaviour patterns: purchasing preferences, payment "
            "methods, mobile commerce adoption\n"
            "4. Cross-border e-commerce regulations and logistics challenges\n"
            "5. Competitive landscape: 3–5 case studies of successful DTC brands "
            "that have expanded into SEA"
        ),
        expected_output=(
            "A comprehensive market research brief in Markdown format covering:\n"
            "- Market size data and growth projections for the top 5 SEA markets\n"
            "- Platform landscape analysis with market-share breakdown\n"
            "- Consumer behaviour insights and trends\n"
            "- Regulatory and logistics overview\n"
            "- 3–5 case studies of successful market entries"
        ),
        agent=researcher,
    )

    return Crew(
        agents=[researcher],
        tasks=[research_task],
        process=Process.sequential,
        verbose=True,
    )


# ---------------------------------------------------------------------------
# Stage 1 — Strategy Crew
# ---------------------------------------------------------------------------

def build_strategy_crew() -> Crew:
    """
    Build and return the Strategy Crew.

    Two agents collaborate sequentially:
      1. The Strategy Analyst applies frameworks (SWOT, country prioritisation,
         channel strategy) to the research brief received from Stage 0.
      2. The Report Writer synthesises everything into a polished executive report.

    The orchestrator injects the Stage 0 output via the {previous_result}
    placeholder in each task description.
    """
    llm = _build_llm()

    analyst = Agent(
        role="Market Entry Strategy Analyst",
        goal=(
            "Analyse the market research data using structured frameworks "
            "(MECE, SWOT, Porter's Five Forces) to identify the optimal market "
            "entry strategy, target country, channel mix, and positioning for "
            "a Hong Kong-based DTC brand in Southeast Asia."
        ),
        backstory=(
            "You are a former McKinsey engagement manager who spent 8 years "
            "advising Fortune 500 consumer goods companies on market entry "
            "strategies across Asia.  You specialise in MECE decomposition and "
            "hypothesis-driven analysis.  You led the Southeast Asia practice "
            "and have helped over 20 brands successfully enter markets like "
            "Thailand, Vietnam, Indonesia, and the Philippines.  You are rigorous "
            "about separating signal from noise and always ground your "
            "recommendations in quantitative evidence and competitive benchmarks."
        ),
        llm=llm,
        verbose=True,
    )

    writer = Agent(
        role="Executive Strategy Report Writer",
        goal=(
            "Synthesise the market research and strategic analysis into a "
            "polished, executive-ready strategy report with clear recommendations, "
            "an actionable implementation roadmap, and key success metrics for "
            "the Southeast Asian market expansion."
        ),
        backstory=(
            "You are a business strategist and communications expert with a "
            "decade of experience at BCG and Bain.  You are known for transforming "
            "complex data analyses into compelling strategic narratives that drive "
            "C-suite decision-making.  Your reports follow the pyramid principle — "
            "leading with the answer, supporting with evidence, and closing with "
            "actionable next steps.  You have a talent for making intricate market "
            "dynamics accessible to diverse stakeholders."
        ),
        llm=llm,
        verbose=True,
    )

    analysis_task = Task(
        description=(
            "Based on the market research brief below, perform a structured "
            "strategic analysis for the Hong Kong DTC brand's SEA expansion.\n\n"
            "--- MARKET RESEARCH BRIEF ---\n"
            "{previous_result}\n"
            "--- END OF BRIEF ---\n\n"
            "Your analysis must include:\n"
            "1. SWOT analysis of entering the SEA e-commerce market\n"
            "2. Country prioritisation matrix — rank the top 5 SEA markets by "
            "attractiveness and ease of entry\n"
            "3. Channel strategy recommendation — which platforms to prioritise "
            "and why\n"
            "4. Competitive positioning analysis — how to differentiate against "
            "local and international competitors\n"
            "5. Risk assessment — top 5 risks and mitigation strategies\n"
            "6. Financial viability indicators — estimated unit economics and "
            "break-even timeline"
        ),
        expected_output=(
            "A structured strategic analysis report in Markdown format including:\n"
            "- SWOT analysis matrix\n"
            "- Country ranking with scoring criteria\n"
            "- Channel strategy with platform recommendations\n"
            "- Competitive positioning map\n"
            "- Risk register with mitigation plans\n"
            "- Preliminary financial projections"
        ),
        agent=analyst,
    )

    report_task = Task(
        description=(
            "Synthesise the market research and the strategic analysis below into "
            "a polished executive strategy report for the Hong Kong DTC brand's "
            "Southeast Asian expansion.\n\n"
            "--- CONTEXT FROM PREVIOUS STAGE ---\n"
            "{previous_result}\n"
            "--- END OF CONTEXT ---\n\n"
            "The report must:\n"
            "1. Open with an executive summary (key recommendation + rationale)\n"
            "2. Present the market opportunity with supporting data\n"
            "3. Detail the recommended entry strategy (target market, channel, "
            "positioning)\n"
            "4. Include a phased implementation roadmap (6–18 months)\n"
            "5. Define KPIs and success metrics\n"
            "6. Close with risk considerations and contingency plans\n"
            "Tone: professional, concise, decision-oriented."
        ),
        expected_output=(
            "A complete executive strategy report (1 000–1 500 words, Markdown) "
            "with sections:\n"
            "- Executive Summary\n"
            "- Market Opportunity Overview\n"
            "- Recommended Entry Strategy\n"
            "- Implementation Roadmap (phased)\n"
            "- KPIs and Success Metrics\n"
            "- Risk Considerations\n"
            "Ready for C-suite presentation."
        ),
        agent=writer,
        context=[analysis_task],
    )

    return Crew(
        agents=[analyst, writer],
        tasks=[analysis_task, report_task],
        process=Process.sequential,
        verbose=True,
    )
