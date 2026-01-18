from fastapi import APIRouter

api_router = APIRouter()

from . import users, projects, api_tests, ui_tests, perf_tests, pytest_tests, monitoring, auth, websocket

api_router.include_router(auth.router, prefix='/auth', tags=['auth'])
api_router.include_router(users.router, prefix='/users', tags=['users'])
api_router.include_router(projects.router, prefix='/projects', tags=['projects'])
api_router.include_router(api_tests.router, prefix='/api-tests', tags=['api-tests'])
api_router.include_router(ui_tests.router, prefix='/ui-tests', tags=['ui-tests'])
api_router.include_router(perf_tests.router, prefix='/perf-tests', tags=['perf-tests'])
api_router.include_router(pytest_tests.router, prefix='/pytest-tests', tags=['pytest-tests'])
api_router.include_router(monitoring.router, prefix='/monitoring', tags=['monitoring'])
api_router.include_router(websocket.router, prefix='/ws', tags=['websocket'])
