from pydantic import BaseModel, Field
from typing import List, Optional

class MetricsTracked(BaseModel):
    latency_target: Optional[str] = Field(default=None, description="Latency target for the project, if present")
    operational_efficiency: Optional[str] = Field(default=None, description="Operational efficiency metrics, if present")

class UpdatePortfolioArgs(BaseModel):
    project_title: str
    tagline: str = Field(description="One sentence summarizing the unique value proposition")
    technical_stack: List[str]
    core_features: List[str] = Field(description="Bullet points highlighting complex logic or UI/UX enhancements")
    metrics_tracked: Optional[MetricsTracked] = Field(default=None)

class AgentOutputSchema(BaseModel):
    action: str = Field(default="update_portfolio_db", description="Must be 'update_portfolio_db'")
    arguments: UpdatePortfolioArgs
