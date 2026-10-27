from pathlib import Path
import json
from pydantic import BaseModel, Field
from dataanalyst_agent.models import get_model
from dataanalyst_agent.logger import logger
from .prompt import PROMPT


class ExecutiveInsights(BaseModel):
    headline: str = Field(
        description="One sentence summarizing the main story in the data"
    )
    key_findings: list[str] = Field(
        default_factory=list, 
        description="Key insights ordered by importance, each citing evidence question IDs in brackets e.g. [q1, q4]"
    )
    actionable_insights: list[str] = Field(
        default_factory=list, 
        description="Actionable next steps starting with Investigate, Test, Monitor or Prioritize"
    )


def synthesize(final_json_path: Path | str, target_col: str) -> ExecutiveInsights | None:

    """
    Takes a saved JSON file path, extracts questions & facts, uses the LLM to generate
    high-level business insights, and saves them in the same run directory.

    """
    path = Path(final_json_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        lines = []
        for qid, q in data.get("questions", {}).items():
            facts = q.get("facts")
            if q.get("success") and facts:
                lines.append(
                    f"[{qid}] {q.get('question', '')} -> {facts.get('answer', '')} "
                    f"| Numbers: {facts.get('key_numbers', {})}"
                )

        if not lines:
            logger.warning(f"Synthesizer: no successful analyses in '{path}'.")
            return None

        prompt = (
            f"{PROMPT}\n\nDataset: {data.get('dataset', 'Unknown')}\n"
            f"Target: {target_col}\n\nFindings:\n" + "\n".join(lines)
        )
        result = get_model().with_structured_output(ExecutiveInsights).invoke(prompt)

        out = path.with_name("executive_insights.json")   
        logger.info(f"Synthesizer: saved insights to '{out}'")
        return result

    except Exception:
        logger.exception("Synthesizer failed")             
        return None