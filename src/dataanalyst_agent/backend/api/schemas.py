from pydantic import BaseModel

class DashboardRequest(BaseModel):
    run_id: str
    target_column: str
