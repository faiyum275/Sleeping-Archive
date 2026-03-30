from __future__ import annotations

from pydantic import BaseModel, Field


class SettingsDocument(BaseModel):
    base: str = ""
    spoiler: str = ""
    style: str = ""


class PreviousContext(BaseModel):
    mode: str = "hybrid"
    recent_full_text: str = ""
    summary: str = ""


class LoopConfigModel(BaseModel):
    max_loops: int = 3
    early_stop_enabled: bool = True
    parallel_feedback: bool = True


class RunRequest(BaseModel):
    title: str = ""
    plot: str = Field(min_length=1)
    settings: SettingsDocument | None = None
    previous_context: PreviousContext = Field(default_factory=PreviousContext)
    loop_config: LoopConfigModel = Field(default_factory=LoopConfigModel)


class CostEstimateRequest(BaseModel):
    plot: str = Field(min_length=1)
    settings: SettingsDocument | None = None
    previous_context: PreviousContext = Field(default_factory=PreviousContext)
    loop_config: LoopConfigModel = Field(default_factory=LoopConfigModel)


class SettingsUpdateRequest(BaseModel):
    settings: SettingsDocument
