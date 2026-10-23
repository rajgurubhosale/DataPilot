from pydantic import BaseModel
import io
from langchain.agents import create_agent
from dataanalyst_agent.planner.planner_prompt import PLANNER_PROMPT
import pandas as pd
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()


df = pd.read_csv(r'D:\DataAnalyst Agent\data\churn-bigml-80.csv')

class Question(BaseModel):
    question: str
    required_cols: list[str]
    why_it_matters: str

class Plan(BaseModel):
    questions: list[Question]  


def read_feature_info(df):
    """Get dataset overview: sample rows, column types, missing-value % and
    unique counts per feature. Features flagged unreliable must not be analysed."""

    NAN_LIMIT=10

    buf = io.StringIO()

    df.info(buf=buf)

    nan_pct = (df.isna().mean() * 100).round(1)
    unreliable = nan_pct[nan_pct > NAN_LIMIT].index.tolist()

    return {
        "sample_head": df.head(5).to_string(max_colwidth=30),
        "features_info": buf.getvalue(),
        "unique_counts": df.nunique().to_dict(),
        "unreliable_features": unreliable,
        "duplicate_rows": int(df.duplicated().sum()),
        "nan_pct": nan_pct.to_dict(),
    }

model = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0.3,
    api_key=os.getenv("GROQ_API_KEY")
    
)

def plan_questions(df, model, target):
    profile = read_feature_info(df)

    prompt = PLANNER_PROMPT.format(
        description=profile,
        target_variable=target,
        
    )
    
    structured_model = model.with_structured_output(Plan, method="json_schema")
    result = structured_model.invoke(prompt)

    return result

if __name__ == "__main__":
    result = plan_questions(df,model,target='Churn')
    print(result)
    plan = plan_questions(df, model, target="Churn")

    for q in plan.questions:
        print(q.query)
        print(q.required_cols)
