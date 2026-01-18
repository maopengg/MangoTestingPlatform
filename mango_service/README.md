# Mango Service - FastAPI 重构版

这是芒果测试平台的 FastAPI 重构版本，使用异步编程提升性能。

## 项目特性

- 基于 FastAPI 的高性能异步 Web 框架
- 支持 API 测试、UI 测试、性能测试
- 集成 Pytest 框架
- 支持定时任务调度
- 实时 WebSocket 通信
- 完整的用户认证和授权系统
- 监控和报告功能

## 技术栈

- Python 3.10+
- FastAPI
- SQLAlchemy 2.0 (异步)
- PostgreSQL/SQLite (异步驱动)
- Redis
- Celery (可选)
- Docker

## 安装和运行

### 环境要求

- Python 3.10+
- pip
- virtualenv (推荐)

### 本地开发环境设置

1. 创建虚拟环境：

   `ash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   `

2. 安装依赖：

   `ash
   pip install -r requirements.txt
   `

3. 配置环境变量：

   创建 .env 文件并添加必要的配置：

   `env
   DATABASE_URL=sqlite+aiosqlite:///./mango_service.db
   SECRET_KEY=your-super-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   `

4. 运行应用：

   `ash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   `

## API 文档

启动服务后，访问以下地址获取交互式 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

\\\
mango_service/
 main.py                 # 应用入口
 requirements.txt        # 依赖包
 README.md              # 项目说明
 .env.example           # 环境变量示例
 .gitignore             # Git忽略文件
 docker-compose.yml     # Docker配置
 Dockerfile             # Docker镜像构建文件
 config/                # 配置文件
 docs/                  # 文档
 tests/                 # 测试文件
 src/                   # 源代码
     api/               # API路由
        v1/
            endpoints/ # API端点
     models/            # 数据模型
     schemas/           # Pydantic模型
     database/          # 数据库相关
     services/          # 业务逻辑
     core/              # 核心配置
     utils/             # 工具函数
     middleware/        # 中间件
\\\

## Docker 部署

1. 构建镜像：

   `ash
   docker build -t mango-service .
   `

2. 运行容器：

   `ash
   docker run -d -p 8000:8000 --env-file .env mango-service
   `

## 环境变量

- \DATABASE_URL\: 数据库连接URL
- \SECRET_KEY\: JWT密钥
- \ALGORITHM\: 加密算法
- \ACCESS_TOKEN_EXPIRE_MINUTES\: 访问令牌过期时间

## 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证

MIT
