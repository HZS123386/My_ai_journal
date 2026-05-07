# AI 日记助手：CI/CD 自动化与线上部署说明（README 精简版）

## 项目概览

本项目是一个基于 **FastAPI + PostgreSQL + Render + GitHub Actions** 的 AI 日记系统，已完成：

- 用户注册 / 登录
- JWT 鉴权
- 用户级数据隔离
- AI 日记分析与周报生成
- Render 自动部署
- GitHub Actions 基础 CI 校验

---

## 技术栈

- **后端**：FastAPI、SQLAlchemy、Alembic
- **数据库**：SQLite（开发阶段）→ PostgreSQL（线上阶段）
- **前端**：HTML + CSS + 原生 JavaScript
- **部署平台**：Render
- **代码托管**：GitHub / Gitee
- **CI**：GitHub Actions
- **认证**：JWT

---

## 为什么要做 CI/CD

### CD（持续部署）
让代码在推送到 GitHub 后，自动触发 Render 重新部署，减少手动上线成本。

### CI（持续集成）
让代码在提交后，自动执行依赖安装、语法检查、Ruff 检查、Pytest 冒烟测试，提前发现问题，降低回归风险。

---

## 自动化部署流程（CD）

### 1. 本地开发
在本地完成功能开发、调试和验证。

### 2. 提交代码
```bash
git add .
git commit -m "your message"
```

### 3. 推送 GitHub
```bash
git push github main
```

### 4. Render 自动部署
Render 检测到 GitHub 仓库主分支更新后，自动：

- 拉取代码
- 安装依赖
- 执行启动命令
- 发布新版本

### 5. 线上验证
部署成功后，通过 Render 提供的 URL 访问项目，验证功能是否正常。

---

## CI 流程（GitHub Actions）

当前项目已经接入 GitHub Actions，并实现基础 CI。

### 当前 CI 检查项

1. Checkout 代码
2. 安装 Python 环境
3. 安装依赖
4. 语法检查（compileall）
5. Ruff 检查
6. Pytest 冒烟测试

### 典型 CI 配置能力

- 验证 `app.py` 能否正常导入
- 验证核心路由是否存在
- 检查明显语法错误和未定义问题

---

## 数据库迁移：为什么从 SQLite 切到 PostgreSQL

### SQLite 的问题

SQLite 适合本地开发，但不适合生产环境，主要原因：

- 并发能力弱
- 文件型数据库，不适合云部署
- 数据持久化和扩展性有限
- 多用户场景下可靠性不足

### PostgreSQL 的优势

- 更适合线上环境
- 支持并发访问
- Render 原生支持
- 更适合用户系统与长期数据存储

因此，项目最终切换到了 PostgreSQL 作为线上数据库。

---

## 本项目部署和 CI 过程中遇到的问题

### 1. Render 启动失败：`DATABASE_URL` 为空
**现象：** 部署日志报错，后端启动失败。  
**原因：** Render 环境变量未正确配置。  
**解决：** 在 Render 的 Environment 中补充：

- `DATABASE_URL`
- `DEEPSEEK_API_KEY`
- `JWT_SECRET_KEY`

---

### 2. SQLite 不支持某些 Alembic 约束变更
**现象：** 本地迁移报错，提示 SQLite 不支持 `ALTER TABLE` 某些操作。  
**原因：** SQLite 对复杂 schema 变更支持有限。  
**解决：**

- 本地开发阶段减少复杂迁移依赖
- 线上主要依赖 PostgreSQL 执行正式迁移

---

### 3. Render 免费实例无法使用 Shell
**现象：** 想通过 Render Shell 执行命令，但提示需要升级。  
**原因：** Render 免费实例不支持 Shell。  
**解决：**

- 在本地完成迁移验证
- 通过 Git 提交 + Render 自动部署完成线上更新

---

### 4. `/docs` 页面一度空白
**现象：** Swagger 页面空白，但服务本身正常。  
**原因：** CDN 静态资源加载失败 / 浏览器缓存异常。  
**解决：**

- 强制刷新浏览器
- 检查 `openapi.json` 是否正常
- 确认 FastAPI 服务实际可用

---

### 5. `email-validator` 缺失
**现象：** 使用 `EmailStr` 时启动报错。  
**原因：** 依赖未安装。  
**解决：** 安装并加入 `requirements.txt`：

```bash
pip install email-validator
```

---

### 6. `python-jose` 缺失
**现象：** JWT 相关导入报错。  
**原因：** JWT 库未安装。  
**解决：**

```bash
pip install "python-jose[cryptography]"
```

---

### 7. `bcrypt` 与 `passlib` 版本兼容问题
**现象：** 注册接口报 500，密码哈希异常。  
**原因：** `bcrypt` 新版本与当前环境不稳定兼容。  
**解决：** 固定版本：

```txt
bcrypt==4.0.1
```

---

### 8. GitHub Actions 中 `pytest` 找不到 `app`
**现象：** CI 里 `pytest` 报 `ModuleNotFoundError: No module named 'app'`。  
**原因：** CI 环境下 Python 模块搜索路径不正确。  
**解决：**

- 在 `tests/conftest.py` 中手动补充项目根目录到 `sys.path`
- 在 CI 中增加：

```yaml
PYTHONPATH: .
```

---

### 9. GitHub 推送网络不稳定
**现象：** `git push github main` 多次失败。  
**原因：** 网络波动、HTTPS 或 SSH 默认端口不稳定。  
**解决：**

- GitHub 改用 SSH 推送
- 在必要时改走更稳定网络
- Gitee 作为备用远程仓库

---

## 当前项目的 CI/CD 状态

### 已完成
- GitHub Actions 基础 CI
- GitHub → Render 自动部署
- 线上 PostgreSQL 数据库接入
- 多环境密钥配置

### 当前可准确表述为

> 项目已实现基础 CI/CD 流程：
> 使用 GitHub Actions 做基础持续集成校验，使用 Render 完成自动化持续部署。

---

## 注意事项

### 1. 环境变量不要写死到代码里
敏感信息统一放到：

- 本地 `.env`
- Render Environment Variables
- GitHub Actions env

### 2. 生产环境不要继续使用 SQLite
线上必须使用 PostgreSQL。

### 3. 每次新增依赖后都要同步更新 `requirements.txt`
否则本地能跑，CI / Render 可能失败。

### 4. 推送失败不等于代码丢失
只要本地已经 `commit`，代码就还在本地仓库里，可以等网络恢复再推送。

### 5. 先保证最小 CI 可用，再逐步增强
当前 CI 先保证：

- 能安装依赖
- 能跑语法检查
- 能跑 Ruff
- 能跑 Smoke Test

后续再逐步加入：

- 更完整的 pytest
- black / format 检查
- 数据库迁移测试

---

## 后续优化方向

### 工程化方向
- 增加更完整的 pytest 用例
- 增加 black / Ruff 全量规则
- 增加数据库迁移检查
- 增加 PR 触发策略与分支保护

### 产品方向
- 第三方登录（Google / GitHub）
- 语音识别写日记
- AI 失败重试
- 更完整的用户中心

---

## 总结

本项目已经从一个本地原型，逐步演进为具备基础工程化能力的完整 Web 应用：

- 支持用户系统
- 支持线上数据库
- 支持自动部署
- 支持基础 CI
- 支持稳定迭代

这使得项目不仅“能运行”，而且“能持续开发、持续上线、持续维护”。
