import re
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
import pandas as pd
from .prompt import SYSTEM_PROMPT
from .sandbox import SandBox
import json

load_dotenv()


FOOTER = """
import json
__res__ = {
    "figure": json.loads(fig.to_json()) if "fig" in globals() and fig is not None else None,
    "facts": facts if "facts" in globals() else {}
}
print("__RESULT__" + json.dumps(__res__))
"""


class AnalystAgent:
    """
    Agent that generates Python analysis code, runs it in a Docker sandbox,
    and iteratively self-corrects based on errors.
    """
    def __init__(self):

        self.model = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3, api_key=os.getenv("GROQ_API_KEY"))
        
        self.sandbox =  SandBox()
        
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SYSTEM_PROMPT),      # a message object, so {braces} in it aren't treated as variables
            ("human", "{schema}\n\n## Your question\n{question}\nUse columns: {columns}"),
        ])

        self.footer = FOOTER

    def extract_code(self,reply: str):
        m = re.search(r"```python\s*(.*?)```", reply, re.DOTALL)
        if not m:
            return None
        return m.group(1).strip()

    def parse_result(self, stdout: str) -> dict:
        for line in stdout.splitlines():
            if line.startswith("__RESULT__"):
                return json.loads(line.replace("__RESULT__", "", 1))
        raise ValueError("No __RESULT__ line found in sandbox output")


    ################
    # THE HINT IS WRONG IT WILL MISLEAD THE LLM OUTPUT GENRATION OKAY!!
    def analysis_worker(self, plan: dict, csv_path: str, max_attempts: int = 3) -> dict:
        
        columns = plan.get("columns")

        schema = pd.read_csv(csv_path, nrows=2)[columns].dtypes.to_string()

        messages = self.prompt.format_messages(
            schema=schema, question= plan.get("question"), columns=columns
        )
        last_error = ""


        for attempt in range(1, max_attempts + 1):
            reply = self.model.invoke(messages)
            code = self.extract_code(reply.content)

            if code is None:
                last_error = "no code block in reply"
                messages += [reply, HumanMessage("Reply with exactly one ```python code block.")]
                continue

            res = self.sandbox.run_code_in_sandbox(
                code=code,
                footer=self.footer,
                csv_path=csv_path,
                timeout=30,
            )

            if res["exit_code"] == 0:
                try:
                    data = self.parse_result(res["stdout"])
                    return {
                        "id": plan.get("id"),
                        "question": plan.get("question"),
                        "columns": columns,
                        "success": True,
                        "code": code,
                        "figure": data["figure"],
                        "facts": data["facts"],
                        "attempts": attempt,
                        "error": None,
                    }
                except Exception as e:
                    last_error = f"Output problem: {e}"
            else:
                last_error = res["stderr"][-2000:]

            if res["exit_code"] == 137:
                hint = "It was killed for exceeding the memory limit. Aggregate before plotting and avoid huge merges or copies." 
            else:
                hint =  "" 

            messages += [reply, HumanMessage(
                f"Your code failed (exit code {res['exit_code']}):\n{last_error}\n{hint}\n"
                "Return the full corrected code in one ```python block."
            )]

        
        return {
            "id": plan.get("id"),
            "question": plan.get("question"),
            "columns": columns,
            "success": False,
            "code": code,
            "figure": None,
            "facts": None,
            "attempts": max_attempts,
            "error": last_error,
        }