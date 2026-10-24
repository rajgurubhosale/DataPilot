from fastapi import APIRouter, UploadFile, File, HTTPException,Request
import pandas as pd
import io
from .schemas import DashboardRequest
from pathlib import Path
import uuid
from dataanalyst_agent.pipeline import AnalystDashboardPipeline
from dataanalyst_agent.agents.planner.planner_agent import plan_questions, model
import json
from fastapi.responses import JSONResponse
from dataanalyst_agent.config import read_config_file


config = read_config_file()
backend_cfg = config.get("backend-app", {})

UPLOAD_DIR = Path(backend_cfg.get("data_dir", "data"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
max_mb = backend_cfg.get("max_upload_size_mb", 25) 
MAX_BYTES = max_mb * 1024 * 1024

router = APIRouter()


@router.get('/')
def welcome():
    return {"msg":"welcome to AutoAnalyst Api"}


@router.post("/upload_data")
def upload_dataset(request: Request,file: UploadFile = File(...)):
    contents = file.file.read()  # bytes
    if len(contents) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (max {max_mb} MB)")

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    
    # "data/a1b2c3d4_churn/"
    run_id = uuid.uuid4().hex[:8]
    dataset_name = Path(file.filename).stem              
    dataset_dir = UPLOAD_DIR / f"{run_id}_{dataset_name}"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    
    # data save
    file_path = dataset_dir / Path(file.filename).name
    
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving CSV: {str(e)}")

    # Store by run_id (isolated per upload)

    if not hasattr(request.app.state, "datasets"):
        request.app.state.datasets = {}
    request.app.state.datasets[run_id] = str(file_path.resolve())

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
        "run_id": run_id,                              
        "message": "Dataset uploaded",
        "sample": df_head,
        "rows": rows,
        "columns": columns,
        "duplicates": int(df.duplicated().sum()),
        "summary": summary,
        "profile": profile

    }
    return JSONResponse(status_code=200, content=result)




@router.post("/create_dashboard")
def create_dashboard(request_body: DashboardRequest,request: Request):
    datasets = getattr(request.app.state, "datasets", {})
    csv_path = datasets.get(request_body.run_id)    
    if not csv_path or not Path(csv_path).exists():
            raise HTTPException(status_code=404, detail="Dataset not found for this run_id")

    pipeline = AnalystDashboardPipeline(
            run_id=request_body.run_id, 
            csv_path=csv_path, 
            target_column=request_body.target_column
        )

    result = pipeline.run()
    
    return JSONResponse(status_code=200, content=result["data"])
