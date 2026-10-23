from pydantic import BaseModel, Field, model_validator



class SubAgentOutput(BaseModel):
    id: int | str | None = Field(default=None, description="Question id, for example 'q1'")
    question: str = Field(description="The question this worker answered")
    columns: list[str] = Field(default_factory=list, description="Dataset columns used for this question")
    success: bool = Field(description="True if the code ran and produced a valid figure")
    code: str | None = Field(default=None, description="The LLM's Python script (without the footer)")
    figure: dict | None = Field(default=None, description="Plotly figure as JSON; None on failure")
    facts: dict | None = Field(default=None, description="answer, key_numbers, caveats; None on failure")
    attempts: int = Field(ge=0, le=10, description="How many attempts were used")
    error: str | None = Field(default=None, description="Last error message; None on success")

    @model_validator(mode="after")
    def check_consistency(self):
        if self.success and (self.figure is None or self.facts is None):
            raise ValueError("success=True requires both figure and facts")
        if not self.success and not self.error:
            raise ValueError("success=False requires an error message")
        return self


class AnalysisCode(BaseModel):
    approach: str = Field(description="One sentence: how you will answer the question")
    code: str = Field(description="Complete Python script as plain text, with no markdown fences")