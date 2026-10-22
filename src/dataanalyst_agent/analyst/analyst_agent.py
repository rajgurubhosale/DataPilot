from dataanalyst_agent.planner.planner_agent import model
import re
import os
import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq

from .prompt import SYSTEM_PROMPT
from .sandbox import SandBox


load_dotenv()

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

    def extract_code(self,reply: str):
        m = re.search(r"```python\s*(.*?)```", reply, re.DOTALL)
        if not m:
            return None
        return m.group(1).strip()


    ################
    # THE HINT IS WRONG IT WILL MISLEAD THE LLM OUTPUT GENRATION OKAY!!
    def analysis_worker(self, state: dict, schema: str, columns: list[str], csv_path: str, max_attempts: int = 3) -> dict:

        messages = self.prompt.format_messages(
            schema=schema, question=state["question"], columns=columns
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
                csv_path=csv_path,
                timeout=30,
            )

            if res["exit_code"] == 0:
                return {"success": True, "code": code, "stdout": res["stdout"], "attempts": attempt}

            last_error = res["stderr"][-2000:]
            if res["exit_code"] == 137:
                hint = "It ran out of memory: use less data, e.g. read only needed columns."
            else:
                hint = ""

            messages += [reply, HumanMessage(
                f"Your code failed (exit code {res['exit_code']}):\n{last_error}\n{hint}\n"
                "Return the full corrected code in one ```python block."
            )]

        return {"success": False, "error": last_error, "attempts": max_attempts}