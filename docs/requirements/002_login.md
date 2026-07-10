# 登录模块需求文档（002_login.md）

## 一、模块背景（Background）

企业级自动化测试平台需要统一的身份认证体系，确保不同角色的用户能够安全、可靠地访问系统资源。

登录模块作为平台的入口，负责完成用户身份认证、权限校验及 Token 管理，为后续所有业务模块提供统一的认证能力。

---

# 二、业务目标（Business Goal）

实现一套安全、稳定、可扩展的登录认证模块，满足以下目标：

1. 用户能够通过用户名和密码登录系统。
2. 登录成功后生成 JWT Access Token。
3. 支持 Refresh Token 刷新登录状态。
4. 支持用户主动退出登录。
5. 后续所有接口统一采用 JWT 鉴权。
6. 为 RBAC（角色权限控制）提供基础能力。

---

# 三、目标用户（Target User）

支持以下角色登录：

### 1. 系统管理员（Admin）

权限：

* 用户管理
* 角色管理
* 系统配置
* 所有业务模块

---

### 2. 测试工程师（Tester）

权限：

* 项目管理
* 环境管理
* API 管理
* 测试执行
* 查看测试报告

---

### 3. 开发工程师（Developer）

权限：

* 查看接口
* 查看测试结果
* 查看测试报告

---

# 四、功能范围（Scope）

本模块包含以下功能：

## 1. 用户登录

用户输入：

* 用户名
* 密码

系统完成：

* 用户身份校验
* 密码验证
* Token 生成
* 登录成功返回用户信息

---

## 2. Token 刷新

支持：

* Refresh Token 换取新的 Access Token
* Access Token 过期后无需重新登录

---

## 3. 用户退出

支持：

* 用户主动退出登录
* 当前 Token 立即失效

---

## 4. 登录状态校验

所有需要登录的接口：

* 自动校验 JWT
* Token 无效返回未登录状态
* Token 过期返回重新登录提示

---

# 五、业务流程（Business Flow）

```text
用户输入用户名、密码
        │
        ▼
系统校验账号是否存在
        │
        ▼
校验密码是否正确
        │
        ▼
生成 JWT Access Token
        │
        ▼
生成 Refresh Token
        │
        ▼
返回用户信息
        │
        ▼
后续接口统一使用 JWT 鉴权
```

---

# 六、API 设计（REST API）

## 1. 用户登录

**POST** `/api/v1/auth/login`

请求参数：

* username
* password

响应：

* access_token
* refresh_token
* token_type
* expires_in
* user_info

---

## 2. 刷新 Token

**POST** `/api/v1/auth/refresh`

请求参数：

* refresh_token

响应：

* 新的 access_token

---

## 3. 退出登录

**POST** `/api/v1/auth/logout`

请求参数：

无

响应：

退出成功

---

## 4. 获取当前用户信息

**GET** `/api/v1/auth/me`

响应：

当前登录用户信息

---

# 七、数据库设计（Data Model）

表：`user`

字段包括：

* id
* username
* password（加密存储）
* nickname
* email
* phone
* status
* role_id
* last_login_time
* created_at
* updated_at

---

# 八、安全要求（Security）

必须满足以下要求：

1. 密码采用加密存储，不允许明文保存。
2. 使用 JWT 作为身份认证方式。
3. Access Token 设置有效期。
4. Refresh Token 设置独立有效期。
5. 登录接口增加参数合法性校验。
6. 禁止返回密码等敏感信息。
7. 所有鉴权失败统一返回标准错误码。
8. 预留验证码、登录失败次数限制等安全扩展能力。

---

# 九、异常处理（Exception）

需要处理以下异常场景：

* 用户不存在
* 密码错误
* 用户被禁用
* Token 无效
* Token 已过期
* Refresh Token 无效
* 非法请求参数
* 系统内部异常

所有异常均返回统一错误格式：

```json
{
  "code": 401,
  "msg": "Unauthorized",
  "data": null
}
```

---

# 十、日志要求（Logging）

记录以下关键操作：

* 登录成功
* 登录失败
* Token 刷新
* 用户退出
* 非法访问
* Token 校验失败

日志至少包含：

* 用户 ID
* 用户名
* IP 地址
* 请求时间
* 请求接口
* 操作结果

---

# 十一、技术约束（Technical Constraints）

技术栈要求：

* Python 3.12
* FastAPI
* SQLAlchemy 2.x
* Alembic
* PostgreSQL
* Pydantic v2
* JWT
* uv
* Ruff
* mypy
* pytest

---

# 十二、验收标准（Definition of Done）

满足以下条件即视为登录模块开发完成：

* 用户可使用正确账号密码成功登录。
* 错误账号或密码返回规范错误信息。
* 登录成功后返回 Access Token 和 Refresh Token。
* Token 可正常访问受保护接口。
* Token 过期后可通过 Refresh Token 获取新的 Access Token。
* 用户可正常退出登录。
* 所有接口通过参数校验和异常处理。
* 单元测试、接口测试全部通过。
* OpenAPI 文档自动生成且内容完整。
* 代码符合项目编码规范，静态检查（Ruff、mypy）无严重告警。
