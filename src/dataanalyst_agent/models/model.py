import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain_openai import ChatOpenAI

load_dotenv()



def get_model():
    return ChatOpenAI(
        model=os.getenv("MESHAPI_MODEL_NAME"),
        api_key=os.getenv("MESHAPI_API_KEY"),
        base_url=os.getenv("MESHAPI_BASE_URL"),
        temperature=0.3
    )
