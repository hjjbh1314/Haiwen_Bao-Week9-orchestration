"""
Mini-Assignment 4: Orchestration — Pipeline Orchestrator
=========================================================
Runs two CrewAI crews in sequence with:

  • Stage logging   — logs [START] / [DONE] / [FAIL] / [SKIP] for every stage
  • Retry logic     — up to 3 attempts per stage, exponential back-off (1s, 2s, 4s)
  • Checkpointing   — saves completed stage results to checkpoint.json after each stage
  • Resume logic    — on re-run, stages already in checkpoint.json are skipped
  • Dual output     — all logs go to both the console and output.txt

Pipeline stages
---------------
  stage_0  Research Crew   — SEA e-commerce market research
  stage_1  Strategy Crew   — strategic analysis + executive report

Usage
-----
  python pipeline.py                    # Run with default topic
  python pipeline.py "Custom topic"     # Run with a custom topic
  python pipeline.py --resume           # Resume from an existing checkpoint
  python pipeline.py --reset            # Delete checkpoint and start fresh
  python pipeline.py --help
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TOPIC = (
    "How should a Hong Kong-based DTC consumer brand "
    "expand into the Southeast Asian e-commerce market?"
)
CHECKPOINT_PATH = "checkpoint.json"
OUTPUT_LOG_PATH = "output.txt"
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    """
    Configure a logger that writes to both stdout and output.txt.
    Every line is prefixed with an ISO-8601 timestamp.
    """
    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler — appends to output.txt so multiple runs accumulate
    fh = logging.FileHandler(OUTPUT_LOG_PATH, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


log = setup_logging()


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint(path: str) -> dict:
    """Load existing checkpoint state; return empty dict if file is absent."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        log.info(f"[CHECKPOINT] Loaded {len(state)} completed stage(s) from {path}")
        return state
    return {}


def save_checkpoint(state: dict, path: str) -> None:
    """Persist current pipeline state to JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    log.info(f"[CHECKPOINT] Saved state to {path}")


# ---------------------------------------------------------------------------
# Core orchestrator
# ---------------------------------------------------------------------------

def run_pipeline(
    stage_configs: list[tuple],
    topic: str = DEFAULT_TOPIC,
    checkpoint_path: str = CHECKPOINT_PATH,
) -> dict:
    """
    Execute a list of crews in sequence.

    Parameters
    ----------
    stage_configs : list of (stage_label, crew_builder_fn) tuples
        stage_label      — human-readable name logged for each stage
        crew_builder_fn  — zero-argument callable that returns a crewai.Crew
    topic : str
        The initial topic injected into Stage 0.
    checkpoint_path : str
        Path to the JSON checkpoint file.

    Returns
    -------
    dict  — final checkpoint state {stage_id: result_str, ...}
    """
    state = load_checkpoint(checkpoint_path)
    current_input: dict = {"topic": topic, "previous_result": topic}

    run_start = datetime.now().isoformat()
    log.info("=" * 70)
    log.info(f"PIPELINE START  {run_start}")
    log.info(f"Topic: {topic}")
    log.info(f"Stages: {len(stage_configs)}")
    log.info("=" * 70)

    for i, (stage_label, crew_builder) in enumerate(stage_configs):
        stage_id = f"stage_{i}"

        # ── Resume logic ────────────────────────────────────────────────────
        if stage_id in state:
            log.info(f"[SKIP] {stage_id} ({stage_label}) — already in checkpoint")
            current_input = {
                "topic": topic,
                "previous_result": state[stage_id],
            }
            continue

        log.info(f"[START] {stage_id}: {stage_label}")
        stage_start = time.time()

        # ── Retry loop ───────────────────────────────────────────────────────
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    wait = 2 ** (attempt - 1)   # 1s, 2s on retry 2 and 3
                    log.warning(
                        f"[RETRY] {stage_id} — attempt {attempt + 1}/{MAX_RETRIES} "
                        f"(waiting {wait}s after previous failure)"
                    )
                    time.sleep(wait)

                crew = crew_builder()
                result = crew.kickoff(inputs=current_input)
                result_str = str(result)

                elapsed = round(time.time() - stage_start, 1)
                log.info(f"[DONE] {stage_id} completed in {elapsed}s")

                state[stage_id] = result_str
                save_checkpoint(state, checkpoint_path)

                current_input = {
                    "topic": topic,
                    "previous_result": result_str,
                }
                last_error = None
                break   # success — exit retry loop

            except Exception as exc:
                last_error = exc
                log.error(
                    f"[FAIL] {stage_id} attempt {attempt + 1}/{MAX_RETRIES} "
                    f"failed: {exc}"
                )

        if last_error is not None:
            log.critical(
                f"[ABORT] {stage_id} failed after {MAX_RETRIES} retries. "
                "Pipeline halted.  Fix the error and re-run to resume."
            )
            raise RuntimeError(
                f"{stage_id} ({stage_label}) failed after {MAX_RETRIES} retries"
            ) from last_error

    run_end = datetime.now().isoformat()
    log.info("=" * 70)
    log.info(f"PIPELINE COMPLETE  {run_end}")
    log.info("=" * 70)

    # Print the final report to stdout as well
    final_stage = f"stage_{len(stage_configs) - 1}"
    if final_stage in state:
        print("\n" + "=" * 70)
        print("  FINAL REPORT")
        print("=" * 70)
        print(state[final_stage])

    return state


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def parse_args() -> tuple[str, bool]:
    """
    Returns (topic, reset_flag).
    --reset  deletes the checkpoint so the pipeline restarts from scratch.
    --resume is the default behaviour (no flag needed).
    """
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        print(__doc__)
        sys.exit(0)

    if "--reset" in args:
        if os.path.exists(CHECKPOINT_PATH):
            os.remove(CHECKPOINT_PATH)
            print(f"[RESET] Deleted {CHECKPOINT_PATH} — pipeline will restart from stage_0.")
        else:
            print("[RESET] No checkpoint found — nothing to reset.")
        args = [a for a in args if a != "--reset"]

    # Any remaining non-flag argument is the custom topic
    topic_parts = [a for a in args if not a.startswith("--")]
    topic = " ".join(topic_parts) if topic_parts else DEFAULT_TOPIC
    return topic, False


if __name__ == "__main__":
    # Lazy import so that syntax errors in crews.py are reported cleanly
    from crews import build_research_crew, build_strategy_crew

    topic, _ = parse_args()

    stages = [
        ("Research Crew — SEA e-commerce market research", build_research_crew),
        ("Strategy Crew — strategic analysis + executive report", build_strategy_crew),
    ]

    try:
        final_state = run_pipeline(stages, topic=topic)
    except RuntimeError as err:
        log.critical(f"Pipeline aborted: {err}")
        sys.exit(1)
