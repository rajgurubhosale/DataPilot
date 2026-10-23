
# run sub agents pipline
# run sub agents in parrlarl in 4 sliding window!!
# and return the code  save it into the dir
# with diff files with question no as fiename
# and metadat with the question and columns and code
# at last combine this code
# and pass this  code with the final agent that create dashboard:)
# and send this dashboard to the frontend and render
from numpy import outer
from .analyst_agent import AnalystAgent
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv
load_dotenv()




class AnalystDashboardPipeline:
    """Run sub-agents and return the final dashboard code ready to post on UI."""

    def __init__(self,csv_path:str):
        self.max_workers = os.getenv("MAX_SANDBOX_WORKERS",1)
        self.agent = AnalystAgent()
    
        csv_file = Path(csv_path).resolve()
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        self.csv_path = str(csv_file)
    
    def _save_code_to_final_dir(self):
        """
        
        """
        pass


    def run_all_questions(self, plan: list[dict], csv_path: str) -> list[dict]:

        def run_single_question_sandbox(item):
            output =  self.agent.analysis_worker(plan,csv_path,max_attempts=3)
            return output
            

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(run_single_question_sandbox, plan))     # results stay in question order

