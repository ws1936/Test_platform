# 自动化测试平台 (Auto Test Platform)

一个功能完善的自动化测试平台，支持 API 测试用例的管理、执行和报告生成。

## 📁 项目结构

```
auto-test-platform/
│
├── docs/                        # 文档目录
│   ├── requirements/            # 需求文档
│   │   ├── 001_project.md       # 项目需求
│   │   ├── 002_login.md         # 登录模块需求
│   │   ├── 003_user.md          # 用户管理需求
│   │   └── 004_api.md           # API测试需求
│   │
│   ├── architecture/            # 架构文档
│   │   ├── system.md            # 系统架构设计
│   │   ├── er.md                # ER图设计
│   │   └── api.md               # API设计文档
│   │
│   ├── design/                  # 详细设计文档
│   └── meeting/                 # 会议纪要
│
├── src/                         # 后端代码（实际代码位置）
│   ├── app/
│   │   ├── common/              # 公共模块
│   │   ├── domain/              # 领域层
│   │   ├── infrastructure/      # 基础设施层
│   │   └── interfaces/          # 接口层
│   ├── migrations/              # 数据库迁移
│   └── tests/                   # 后端测试
│
├── frontend/                    # 前端代码（待开发）
│   └── src/
│
├── tests/                       # 集成测试
├── scripts/                     # 脚本工具
└── README.md
```

## 🚀 技术栈

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 编程语言 |
| FastAPI | 0.115+ | Web框架 |
| SQLAlchemy | 2.0+ | ORM |
| Pydantic | 2.9+ | 数据验证 |
| PostgreSQL | 15+ | 主数据库 |
| Redis | 7+ | 缓存 |

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18+ | UI框架 |
| TypeScript | 5+ | 类型安全 |
| Ant Design | 5+ | UI组件 |
| React Query | 5+ | 数据请求 |

## 📋 功能模块

### 已完成
- [x] 用户认证（注册/登录/Token刷新）
- [x] 项目结构搭建
- [x] 数据库设计

### 进行中
- [ ] 用户管理模块
- [ ] API测试项目管理
- [ ] 测试用例管理
- [ ] 测试执行引擎
- [ ] 测试报告生成

### 待开发
- [ ] 前端界面
- [ ] 环境配置管理
- [ ] 定时任务
- [ ] 数据导出

## 🛠️ 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### 后端启动

```bash
# 安装依赖（在项目根目录）
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件

# 运行数据库迁移（alembic.ini 位于 src/）
cd src && alembic upgrade head && cd ..

# 启动服务
cd src && uvicorn app.main:app --reload
```

### 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 📖 API 文档

启动后端服务后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🧪 测试

```bash
# 运行后端测试（在项目根目录）
pytest src/tests

# 运行集成测试
pytest tests
```

## 📝 开发规范

### 代码风格
- 后端：遵循 PEP 8，使用 Black 格式化
- 前端：遵循 ESLint + Prettier 配置

### Git 提交规范
```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具链
```

## 📄 License

MIT License

## 👥 团队

- 项目负责人：[姓名]
- 后端开发：[姓名]
- 前端开发：[姓名]
- 测试工程师：[姓名]