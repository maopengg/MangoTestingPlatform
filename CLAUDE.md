# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

芒果测试平台 (MangoTestingPlatform) — a low-code test automation platform supporting UI, API, and Pytest-based testing, consisting of three main components.

## Repository Structure

```
MangoServer/       # Django REST backend (Python)
MangoActuator/     # Desktop test executor (Python + PySide6/Qt)
mango-console/     # Vue 3 + TypeScript web frontend
```

## Common Commands

### MangoServer (Django backend)

```bash
cd MangoServer
# Start dev services
sh scripts/start_dev_services.sh
# Start core-api only
python manage.py runserver --env=dev 0.0.0.0:8000
# Django management commands
python manage.py migrate
python manage.py createsuperuser
```

### MangoActuator (desktop executor)

```bash
cd MangoActuator
python main.py            # Windows GUI entry
python linux_main.py      # Linux entry
# Build standalone .exe (see PyInstaller comment in main.py)
```

### mango-console (Vue frontend)

```bash
cd mango-console
npm run dev        # Vite dev server (dev env)
npm run test       # Test env
npm run master     # Master env
npm run build:dev  # Build for dev
npm run tsc        # Type-check
```

### Docker (full stack)

```bash
docker compose up -d    # Starts core-api, scheduler, dispatcher, api workers, MCP, frontend, actuator
```

## Architecture

### MangoServer — Django Backend

- **Entry point**: Docker starts `uvicorn src.asgi:application`; local multi-service startup uses `scripts/start_dev_services.sh`
- **ASGI app**: `src/asgi.py` — ProtocolTypeRouter dispatching HTTP (Django) and WebSocket (Channels)
- **Settings**: `DJANGO_ENV` environment variable selects `src/settings/{dev,test,prod,master}.py`; defaults to `master`
- **Database**: MySQL by default (`IS_SQLITE = False`); connection config in `src/settings/database.json` or directly in the env-specific setting file

**Django apps** under `src/auto_test/`:

| App | Purpose |
|-----|---------|
| `auto_api` | API test cases, case sets, parameterization, assertions |
| `auto_ui` | UI test page elements, case steps, case sets |
| `auto_pytest` | Pytest case orchestration and result reporting |
| `auto_perf` | Performance test script management |
| `auto_system` | System config (projects, products, notifications, scheduled tasks) + WebSocket consumer |
| `auto_user` | Users, roles, permissions |
| `monitoring` | Monitoring tasks with script upload/editing, real-time logs, alert reports |

- **URL routing**: `src/urls.py` — REST endpoints; `src/routing.py` — WebSocket routes
- **WebSocket**: `ChatConsumer` in `auto_system/consumers.py` handles both web (`/web/socket`) and client executor (`/client/socket`) connections
- **Authentication**: JWT-based via `src/middleware/auth.py`; demo mode restrictions in `src/middleware/is_delete.py`
- **File storage**: MinIO when `IS_MINIO = True`, otherwise local filesystem to `mango-file/`
- **Exception hierarchy**: `MangoServerError` base in `src/exceptions/` with subclasses (`UiError`, `ApiError`, `PytestError`, etc.)
- **Logging**: Per-app rotating file handlers under `logs/auto_{api,ui,system,perf,pytest}/` + console output

### MangoActuator — Desktop Executor

- **GUI framework**: PySide6 with `QApplication` + custom async event loop
- **Communication**: WebSocket to MangoServer for receiving test tasks; HTTP for auth and result upload
- **Architecture**: Three concurrent asyncio tasks in `src/__init__.py`:
  1. `WebSocketClient.client_run()` — maintain persistent connection
  2. `SocketConsumer.process_tasks()` — handle incoming messages/commands
  3. `CaseFlow.process_tasks()` / `PytestCaseFlow.process_tasks()` — execute test cases
- **Key dirs under `src/`**: `pages/` (GUI windows), `consumer/` (server message handlers), `services/` (execution logic for api/ui/pytest), `network/` (HTTP + WebSocket clients)
- **Packaging**: PyInstaller with `芒果执行器.spec` or inline config in `main.py`

### mango-console — Vue Frontend

- **Framework**: Vue 3 + TypeScript + Vite + Arco Design + Pinia
- **Routing**: Hash-based (`createWebHashHistory`), routes defined in `src/router/routes/constants.ts` + `extraRoutes` in `src/router/index.ts`
- **API layer**: Axios with per-module API files under `src/api/{apitest,uitest,pytest,system,monitoring,user}/`; interceptors handle auth tokens
- **State**: Pinia stores in `src/store/`
- **Environment**: `.env.{dev,test,prod,master}` files control API base URL and build output

### mango_pytest (within MangoServer)

External test framework code pulled in from a separate repository — not part of the MangoTestingPlatform itself. It represents the test content that users write and execute through the platform's pytest functionality, not a platform feature.

## Key Patterns

- **View layer**: Django REST Framework ViewSets in each app's `views/` directory, with service logic in `service/`
- **Async execution**: APScheduler for scheduled tasks in `auto_system`
- **Enum-driven config**: `src/enums/` contains shared enum definitions used across apps
- **Message protocol**: Server and actuator communicate via a JSON-based protocol (models defined in `src/models/socket_model.py`)
