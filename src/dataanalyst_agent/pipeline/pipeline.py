
# run sub agents pipline
# run sub agents in parrlarl in 4 sliding window!!
# and return the code  save it into the dir
# with diff files with question no as fiename
# and metadat with the question and columns and code
# at last combine this code
# and pass this  code with the final agent that create dashboard:)
# and send this dashboard to the frontend and render
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os
import pandas as pd
from dotenv import load_dotenv

from dataanalyst_agent.config import read_config_file
from dataanalyst_agent.agents.analyst.analyst_agent import AnalystAgent
from dataanalyst_agent.agents.planner.planner_agent import plan_questions, model as planner_model
from dataanalyst_agent.logger import logger

load_dotenv()


class AnalystDashboardPipeline:
    """Run sub-agents and return the final dashboard code ready to post on UI."""

    def __init__(self, run_id: str, csv_path: str | Path, target_column: str | None = None):
        self.agent = AnalystAgent()
        self.target_column = target_column

        config = read_config_file()
        pipe_cfg = config.get("pipeline", {})

        self.max_workers = int(pipe_cfg.get("max_workers", 4))
        self.output_filename = pipe_cfg.get("output_filename", "final_output.json")

        csv_file = Path(csv_path).resolve()
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        self.csv_path = str(csv_file)
        self.csv_name = csv_file.stem
        self.run_id = run_id
        self.run_dir = csv_file.parent

    def _save_code_to_final_dir(self, results: list) -> Path:
        """Saves all results into final_output.json keyed by q1, q2..."""
        file_path = self.run_dir / self.output_filename

        questions_dict = {
            f"q{i}": r.model_dump() if hasattr(r, "model_dump") else r
            for i, r in enumerate(results, 1)
        }
        
        for q in questions_dict.values():
            if isinstance(q.get("figure"), dict) and "layout" in q["figure"]:
                q["figure"]["layout"].pop("template", None)
        
        payload = {
            "run_id": self.run_id,
            "dataset": self.csv_name,
            "total_questions": len(results),
            "successful": sum(1 for r in results if getattr(r, "success", False)),
            "questions": questions_dict,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return file_path,payload

    def run_all_questions(self, plan: list[dict]) -> dict:

        def run_single_question_sandbox(item):
            if hasattr(item, "model_dump"):
                item_dict = item.model_dump() 
            else:
                item_dict = item

            q_text = item_dict.get("question", "")[:50]
            logger.info(f"-> [Docker] Starting: {q_text}...")

            res = self.agent.analysis_worker(item_dict, self.csv_path, max_attempts=3)

            status = "[PASS]" if res.success else f"[FAIL] ({res.error})"
            logger.info(f"<- [Docker] Finished: {q_text} | {status} (Attempts: {res.attempts})")
            return res

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            results = list(pool.map(run_single_question_sandbox, plan))

        saved_file, payload = self._save_code_to_final_dir(results)

        return {
            "run_id": self.run_id,
            "file_path": str(saved_file),
            "data": payload,  # Full dictionary with {"q1": ..., "q2": ...}
        }

    def run(self, target_column: str | None = None) -> dict:
        """End-to-end execution: plans questions using PlannerAgent and executes sandbox analysis."""
        target = target_column or self.target_column
        if not target:
            raise ValueError("target_column must be specified at initialization or passed to run().")

        logger.info(f"Step 1: Planner is analyzing profile for target='{target}'...")
        df = pd.read_csv(self.csv_path)
        plan = plan_questions(df=df, model=planner_model, target=target)
        logger.info(f"Step 1 Complete: Planner generated {len(plan.questions)} questions.")

        logger.info(f"Step 2: Running Pipeline across {self.max_workers} Docker workers...")
        return self.run_all_questions(plan.questions)


if __name__ == "__main__":
    csv_file = Path("data/churn-bigml-80.csv").resolve()
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    pipeline = AnalystDashboardPipeline(run_id="exp_run_01", csv_path=csv_file, target_column="Churn")
    output = pipeline.run()

    logger.info(f"Pipeline Complete! {output['data']['successful']}/{output['data']['total_questions']} successful. Saved to {output['file_path']}")

