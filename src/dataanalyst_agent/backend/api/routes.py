from fastapi import APIRouter
from fastapi import APIRouter, UploadFile, File, HTTPException
import pandas as pd
import io
# In-memory session/dataset storage
state = {}
import json
from fastapi.responses import JSONResponse


router = APIRouter()

@router.post("/upload_data")
async def upload_dataset(file: UploadFile = File(...)):
    contents = await file.read()  # bytes

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    state["df"] = df  # store in memory
    num_df = df.select_dtypes("number")
    summary = (
            json.loads(num_df.describe().T.reset_index().to_json(orient="records"))
            if not num_df.empty
            else []
        )


    profile = [
        {
            "column": col,
            "missing": int(df[col].isna().sum()),
            "missing_%": round(float(df[col].isna().mean() * 100), 1),
            "unique": int(df[col].nunique()),
        }
        for col in df.columns
    ]

    df_head = json.loads(df.head(10).to_json(orient="records"))
    rows = len(df)
    columns = len(df.columns)
    
    result= {
        "message": "Dataset uploaded",
        "sample": df_head,
        "rows": rows,
        "columns": columns,
        "duplicates": int(df.duplicated().sum()),
        "summary": summary,
        "profile": profile

    }
    return JSONResponse(status_code=200, content=result)

