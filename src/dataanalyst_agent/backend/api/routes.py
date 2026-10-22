from fastapi import APIRouter, UploadFile, File, HTTPException,Request
import pandas as pd
import io
from pathlib import Path
import uuid

import json
from fastapi.responses import JSONResponse


UPLOAD_DIR = Path("data")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_BYTES = 25 * 1024 * 1024

router = APIRouter()

@router.post("/upload_data")
def upload_dataset(request: Request,file: UploadFile = File(...)):
    contents = file.file.read()  # bytes
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 25 MB)")

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    
    # Generate a unique name: e.g. "a1b2c3d4_churn.csv"
    unique_name = f"{uuid.uuid4().hex[:8]}_{Path(file.filename).name}"
    file_path = UPLOAD_DIR / unique_name
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving CSV: {str(e)}")

    # Safely ensure datasets dict exists on app.state
    if not hasattr(request.app.state, "datasets"):
        request.app.state.datasets = {}
    request.app.state.datasets["csv_path"] = str(file_path.resolve())

    # state["df"] = df  # store in memory
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

