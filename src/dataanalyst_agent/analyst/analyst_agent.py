from langchain_core.tools import retriever
import re
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_groq import ChatGroq
import pandas as pd
from .prompt import SYSTEM_PROMPT
from .sandbox import SandBox
import json
from .schemas import SubAgentOutput,AnalysisCode
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
        self.structured_model = self.model.with_structured_output(AnalysisCode)

        self.sandbox =  SandBox()
        
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SYSTEM_PROMPT),      # a message object, so {braces} in it aren't treated as variables
            ("human", "{schema}\n\n## Your question\n{question}\nUse columns: {columns}"),
        ])

        self.footer = FOOTER    
        
    def clean_code(self, code: str) -> str:
        m = re.search(r"```(?:python)?\s*(.*?)```", code, re.DOTALL)
        return (m.group(1) if m else code).strip()

    def parse_result(self, stdout: str) -> dict:
        for line in stdout.splitlines():
            if line.startswith("__RESULT__"):
                data = json.loads(line.replace("__RESULT__", "", 1))

                if data.get("figure") is None:
                    raise ValueError("`fig` was not defined. Build a Plotly figure named `fig`.")

                facts = data.get("facts")
                if not isinstance(facts, dict) or not facts.get("answer"):
                    raise ValueError("`facts` must be a dict with a non-empty 'answer'.")

                return data
        raise ValueError("No __RESULT__ line found in sandbox output")


    def analysis_worker(self, plan: dict, csv_path: str, max_attempts: int = 3) -> SubAgentOutput:
        
        columns = plan.get("columns")

        schema = pd.read_csv(csv_path, nrows=2)[columns].dtypes.to_string()

        messages = self.prompt.format_messages(
            schema=schema, question= plan.get("question"), columns=columns
        )
        last_error = ""


        for attempt in range(1, max_attempts + 1):
            reply = self.structured_model.invoke(messages)    # AnalysisCode object

            code = self.clean_code(reply.code)
            if not code:
                last_error = "empty code"
                messages += [HumanMessage("Return the full script in the `code` field as plain Python.")]
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
                    return SubAgentOutput(
                        id=plan.get("id"),
                        question=plan.get("question") or plan.get("query"),
                        columns=columns,
                        success=True,
                        code=code,
                        figure=data["figure"],
                        facts=data["facts"],
                        attempts=attempt,
                        error=None,
                    )
                except Exception as e:
                    last_error = f"Output problem: {e}"
            else:
                last_error = res["stderr"][-2000:]

            if res["exit_code"] == 137:
                hint = "It was killed for exceeding the memory limit. Aggregate before plotting and avoid huge merges or copies." 
            else:
                hint =  "" 

            messages += [
                    AIMessage(content=f"```python\n{code}\n```"),
                    HumanMessage(f"{last_error}{hint}\nReturn the full corrected script in the `code` field."),
                ]


        
        return SubAgentOutput(
            id=plan.get("id"),
            question=plan.get("question"),
            columns=columns,
            success=False,
            code=code,
            attempts=max_attempts,
            error=last_error or "Max attempts exceeded",
        )
