
# run sub agents pipline
# run sub agents in parrlarl in 4 sliding window!!
# and return the code  save it into the dir
# with diff files with question no as fiename
# and metadat with the question and columns and code
# at last combine this code
# and pass this  code with the final agent that create dashboard:)
# and send this dashboard to the frontend and render
import json
from dataanalyst_agent.config import read_config_file
from dataanalyst_agent.agents.analyst.analyst_agent import AnalystAgent
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv

load_dotenv()


class AnalystDashboardPipeline:
    """Run sub-agents and return the final dashboard code ready to post on UI."""

    def __init__(self, run_id: str, csv_path: str | Path):
        self.agent = AnalystAgent()

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
                item_dict =  item

            return self.agent.analysis_worker(item_dict, self.csv_path, max_attempts=3)

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            results = list(pool.map(run_single_question_sandbox, plan))

        saved_file, payload = self._save_code_to_final_dir(results)

        return {
            "run_id": self.run_id,
            "file_path": str(saved_file),
            "data": payload,  # Full dictionary with {"q1": ..., "q2": ...}
        }



if __name__ == "__main__":
    from pathlib import Path
    import pandas as pd
    from dataanalyst_agent.agents.planner.planner_agent import plan_questions, model

    # 1. Dataset path
    csv_file = Path("data/churn-bigml-80.csv").resolve()
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    print(f"📊 Loading dataset: {csv_file.name}")
    df = pd.read_csv(csv_file)

    # 2. Step 1: Use Planner Agent to generate strategic questions
    target_column = "Churn"  # Change to your target column if needed
    print(f"🧠 Step 1: Planner is analyzing profile and generating questions for target='{target_column}'...")
    plan = plan_questions(df=df, model=model, target=target_column)

    print(f"\n🎯 Planner generated {len(plan.questions)} questions:")
    for i, q in enumerate(plan.questions, 1):
        print(f"  Q{i}: {q.question}")
        print(f"      Columns: {q.required_cols}")
        print(f"      Why it matters: {q.why_it_matters}\n")

    # 3. Step 2: Initialize Pipeline & Execute Sub-Agents in Parallel
    print("⚡ Step 2: Running Pipeline with Sub-Agents in Docker Sandbox...")
    pipeline = AnalystDashboardPipeline(run_id="exp_run_01", csv_path=csv_file)
    
    # Pass plan.questions directly into the pipeline
    output = pipeline.run_all_questions(plan.questions)

    # 4. Results summary
    print("\n✅ --- Pipeline Run Complete ---")
    print(f"Run ID          : {output['run_id']}")
    print(f"File Saved      : {output['file_path']}")
    print(f"Total Questions : {output['data']['total_questions']}")
    print(f"Successful      : {output['data']['successful']}")

    print("\n📈 Results per Question:")
    for q_id, q_data in output["data"]["questions"].items():
        status = "✅ PASS" if q_data.get("success") else "❌ FAIL"
        print(f"  [{q_id}] {status} - Attempts: {q_data.get('attempts')}")
        if q_data.get("facts"):
            print(f"       Answer: {q_data['facts'].get('answer')}")
