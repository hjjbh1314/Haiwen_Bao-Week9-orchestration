# Mini-Assignment 4: Orchestration

## Pipeline Stages

This project builds a two-stage CrewAI pipeline that automates a strategic consulting workflow for a Hong Kong-based DTC brand expanding into Southeast Asia.

| Stage | Name | Crew | Agents | Output |
|---|---|---|---|---|
| `stage_0` | Research Crew | `build_research_crew()` | Senior Market Research Analyst | SEA market research brief (Markdown) |
| `stage_1` | Strategy Crew | `build_strategy_crew()` | Market Entry Strategy Analyst + Executive Strategy Report Writer | Final executive strategy report (Markdown) |

**Data flow:** The full text output of `stage_0` is injected as `{previous_result}` into every task in `stage_1` via `crew.kickoff(inputs={...})`.

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure your API key

You can either export the key directly:

```bash
export DEEPSEEK_API_KEY=your_key_here
python pipeline.py
```

Or create a `.env` file (see `.env.example` for the expected variable names):

```bash
# .env
DEEPSEEK_API_KEY=sk-your_actual_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_API_BASE=https://api.deepseek.com
```

Then run:

```bash
python pipeline.py
```

Optional — pass a custom topic:

```bash
python pipeline.py "How should a Singapore fintech startup expand into ASEAN?"
```

## How to Resume After Failure

The pipeline saves a `checkpoint.json` after every completed stage.  
If the run is interrupted mid-way, simply re-run the same command:

```bash
python pipeline.py
```

The orchestrator reads `checkpoint.json` on startup and **skips any stage whose result is already saved**, continuing from where it left off.

To force a full restart (ignore checkpoint):

```bash
python pipeline.py --reset
```

## Where to Find the Output

| File | Description |
|---|---|
| `output.txt` | Full execution log (timestamps, stage status, crew verbose output, final report) |
| `checkpoint.json` | Persisted stage results; used for resume logic |

Both files are **appended** on each run (new runs add a separator line).

## Challenges and Solutions

1. **Separating one crew into two with clean data handoff.** The Week 8 crew had three agents in a single sequential crew sharing task context automatically. Splitting into two independent `Crew` objects meant the output of Stage 0 had to be explicitly serialised to a string and re-injected as `{previous_result}` in the Stage 1 task descriptions. Using a `{previous_result}` placeholder in the task `description` field and passing it through `crew.kickoff(inputs={"previous_result": result_str})` solved this cleanly.

2. **Retry logic without masking real errors.** Transient API rate-limit errors should trigger a retry, but persistent issues (wrong API key, malformed input) should surface immediately. The solution was to log every failure with full traceback detail at `ERROR` level, retry up to three times with exponential back-off (1s → 2s → 4s), and only raise `RuntimeError` and halt the pipeline after all retries are exhausted.

3. **Checkpoint design that survives partial runs.** Storing the raw result string (not a parsed object) in `checkpoint.json` meant no schema to maintain and no deserialisation risk. The resume logic simply checks `if stage_id in state` before building the crew, which means the expensive LLM call is never made for already-completed stages.

4. **Dual logging to console and file.** Using Python's `logging` module with both a `StreamHandler` and a `FileHandler` meant every timestamped line appeared both in the terminal and in `output.txt` without duplicating `print()` calls throughout the code.
