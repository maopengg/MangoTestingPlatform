from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.database.session import engine, Base
from src.api.v1.endpoints import api_router
from src.core.config import settings
from src.core.middleware import LoggingMiddleware, AuthMiddleware
from src.core.exceptions import (
    MangoException, 
    mango_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from starlette.exceptions import HTTPException as StarletteHTTPException


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=""Mango Service - 一个基于FastAPI的异步自动化测试平台"",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 自定义中间件
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)

# 异常处理器
app.add_exception_handler(MangoException, mango_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 注册API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {""message"": ""Welcome to Mango Service - FastAPI based automation testing platform""}

@app.get("/health")
async def health_check():
    return {""status"": ""healthy"", ""service"": ""mango_service""}
