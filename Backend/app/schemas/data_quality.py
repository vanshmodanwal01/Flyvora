from datetime import datetime

from pydantic import BaseModel


class DataQualitySummary(BaseModel):
    recordsIngested: int
    pipelineUptime: str        # pre-formatted "98.4%"
    validationFailures: int
    lastRun: datetime | None


class ValidationRate(BaseModel):
    passed: float
    warned: float
    failed: float


class IngestionVolumePoint(BaseModel):
    label: str                 # "D1".."D30" or a date string
    records: int


class DataSourceStatusItem(BaseModel):
    name: str
    status: str
    detail: str


class PipelineRunLogRow(BaseModel):
    time: datetime
    status: str
    records: int
    durationSeconds: float
