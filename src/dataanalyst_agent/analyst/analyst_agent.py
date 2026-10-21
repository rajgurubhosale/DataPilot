from pydantic import BaseModel
import re
from src.dataanalyst_agent.analyst.prompt import SYSTEM_PROMPT
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage,HumanMessage
import os
from langchain_groq import ChatGroq
from .sandbox import SandBox
import asyncio



def extract_code(reply: str) -> str:
    m = re.search(r"```python\s*(.*?)```", reply, re.DOTALL)
    if not m:
        return False
    return m.group(1).strip()

model = ChatGroq(model="openai/gpt-oss-120b", temperature=0.3, api_key=os.getenv("GROQ_API_KEY"))
sandbox = SandBox()    # one shared instance

prompt = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_PROMPT),      # a message object, so {braces} in it aren't treated as variables
    ("human", "{schema}\n\n## Your question\n{question}\nUse columns: {columns}"),
])

################
# THE HINT IS WRONG IT WILL MISLEAD THE LLM OUTPUT GENRATION OKAY!!
#
async def analysis_worker(state: dict, schema: str, columns: list[str],
                          csv_path: str, max_attempts: int = 3) -> dict:
    messages = prompt.format_messages(
        schema=schema, question=state["question"], columns=columns
    )
    last_error = ""

    for attempt in range(1, max_attempts + 1):
        reply = await model.ainvoke(messages)
        code = extract_code(reply.content)

        if code is None:
            last_error = "no code block in reply"
            messages += [reply, HumanMessage("Reply with exactly one ```python code block.")]
            continue

        res = await asyncio.to_thread(sandbox.run_code_in_sandbox, code, csv_path)

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