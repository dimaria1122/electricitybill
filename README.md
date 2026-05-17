# 寝室电费监控器

这是一个本地运行的寝室电费余额监控工具，用于查询一个已授权寝室在「慧新易校」里的电费余额，定时保存历史记录，并在浏览器里展示余额曲线和消耗趋势。

项目默认只适合查询你自己有权限查询的寝室。请不要用于查询未授权寝室，也不要上传 `.env`、token 或本地数据库。

## 功能

- 定时查询电费余额，默认每 30 分钟一次。
- 启动服务后会立即查询一次。
- 支持网页手动点击「立即刷新」。
- 使用 SQLite 本地保存余额历史。
- 浏览器 Dashboard 展示：
  - 当前余额；
  - 最近一次更新时间；
  - token / 查询状态；
  - 余额变化曲线；
  - 每次余额变化；
  - 最近 24 小时消耗；
  - 最近 7 日日均消耗；
  - 按当前速度预计还能用多少天。
- token 失效时会在页面提示，不会在页面显示 token。

## 目录说明

```text
electricitybill/          后端服务和静态页面
electricitybill/static/   浏览器 Dashboard
tests/                    自动化测试
scripts/                  跨平台启动脚本
.env.example              配置模板，不含真实 token
```

## macOS / Linux 使用方法

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

然后编辑 `.env`：

```env
SYNJONES_AUTH=bearer 你的token
ROOM=你的寝室号
FEEITEM_ID=261
QUERY_INTERVAL_MINUTES=30
DATABASE_PATH=electricity.db
```

启动服务：

```bash
uvicorn electricitybill.app:app --reload
```

打开：

```text
http://127.0.0.1:8000
```

也可以使用脚本启动：

```bash
chmod +x scripts/run-macos-linux.sh
./scripts/run-macos-linux.sh
```

## Windows 使用方法

在 PowerShell 中执行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

编辑 `.env` 后启动：

```powershell
uvicorn electricitybill.app:app --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

也可以使用脚本启动：

```powershell
.\scripts\run-windows.ps1
```

如果 PowerShell 阻止脚本运行，可以先在当前窗口执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

然后再运行脚本。

## 树莓派 / 局域网使用方法

树莓派上按 macOS / Linux 的方式安装依赖和配置 `.env`。

如果只在树莓派本机访问：

```bash
./scripts/run-macos-linux.sh
```

如果希望同一局域网内的手机或电脑访问，把服务绑定到所有网卡：

```bash
HOST=0.0.0.0 PORT=8000 ./scripts/run-macos-linux.sh
```

然后在其他设备打开：

```text
http://树莓派IP:8000
```

建议把 `.env` 和 `electricity.db` 保存在树莓派本地。它们已经被 `.gitignore` 忽略，不应该上传到 GitHub。

## 如何获取 token

当前版本使用手动 token 模式：

1. 使用 Reqable 等抓包工具，只抓取你自己账号、自己寝室的正常查询请求。
2. 找到请求头里的 `synjones-auth`。
3. 把完整值复制到 `.env` 的 `SYNJONES_AUTH` 中。

示例格式：

```env
SYNJONES_AUTH=bearer paste_token_here
```

不要把真实 token 发给别人，也不要提交到 GitHub。

## 验证一次查询

启动服务后，打开页面点击「立即刷新」。

如果成功，页面会显示当前余额和更新时间。

如果 token 失效，页面会显示认证失败。这时需要重新从 App 请求中复制新的 `synjones-auth`，更新 `.env`，然后重启服务。

也可以直接访问接口检查：

```text
http://127.0.0.1:8000/api/status
```

## 运行测试

```bash
python -m pytest tests -v
```

如果你使用的是 macOS 自带 Python，推荐用虚拟环境里的 Python：

```bash
.venv/bin/python -m pytest tests -v
```

## 常见问题

### 1. 访问 `http://127.0.0.1:8000` 加载不出来

先看终端里 `uvicorn` 是否报错。如果看到类似：

```text
TypeError: unsupported operand type(s) for |: 'type' and 'type'
```

说明运行环境是 Python 3.9，而代码需要兼容类型标注。当前版本已经修复这个问题，请拉取最新代码后重启服务。

### 2. 页面打开了，但余额不更新

打开：

```text
http://127.0.0.1:8000/api/status
```

查看 `last_query_status`：

- `success`：查询成功；
- `auth_error`：token 失效或填写错误；
- `error`：网络、接口或解析失败。

### 3. 为什么没有历史数据？

历史数据只在服务运行时记录。如果电脑休眠、服务停止，期间不会查询。

## 安全说明

- 只查询你有权限查询的寝室。
- `.env` 只保存在本地，不要上传 GitHub。
- `electricity.db` 是本地历史数据，也不要上传。
- 本项目不会保存慧新易校账号密码。
- 本项目不会自动缴费。
- 本项目不会绕过验证码、短信验证、设备指纹或其他安全保护。

## 后续计划：自动登录

如果慧新易校登录接口确实只是账号密码直登，后续可以实现自动登录并自动获取 token。

实现前需要确认登录接口是否包含：

- 验证码；
- 短信验证；
- 设备指纹；
- 加密密码；
- refresh token；
- 风控限制。

如果存在验证码、短信或风控，本项目不会尝试绕过。更推荐优先研究是否有合法的 token 刷新接口。
