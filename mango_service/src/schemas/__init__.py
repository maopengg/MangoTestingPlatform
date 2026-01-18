from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProjectOut(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiTestBase(BaseModel):
    name: str
    description: Optional[str] = None
    url: str
    method: str  # GET, POST, PUT, DELETE, etc.
    headers: Optional[str] = None  # JSON string
    body: Optional[str] = None


class ApiTestCreate(ApiTestBase):
    project_id: int


class ApiTestUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[str] = None
    body: Optional[str] = None


class ApiTestOut(ApiTestBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestCaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    steps: Optional[str] = None  # JSON string representing test steps


class TestCaseCreate(TestCaseBase):
    project_id: int


class TestCaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[str] = None


class TestCaseOut(TestCaseBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TestResultBase(BaseModel):
    test_case_id: int
    status: str  # PASSED, FAILED, SKIPPED
    result_data: Optional[str] = None  # JSON string with test results
    duration: Optional[int] = None  # Execution time in milliseconds


class TestResultCreate(TestResultBase):
    pass


class TestResultUpdate(BaseModel):
    status: Optional[str] = None
    result_data: Optional[str] = None
    duration: Optional[int] = None


class TestResultOut(TestResultBase):
    id: int
    executed_at: datetime

    class Config:
        from_attributes = True
