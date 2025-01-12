# DNS 自动更新工具

这是一个自动更新 Cloudflare DNS 记录的工具，可以根据不同地区的可用 IP 自动更新 DNS 记录。

## 功能特点

- 支持多个地区（如日本、香港、韩国等）
- 使用CloudflareSpeedTest测试IP延迟
- 支持多 IP 负载均衡（一个域名对应多个 IP）
- 每2小时自动更新一次
- Telegram 通知支持

## 配置说明

1. 复制 `.env.example` 为 `.env`，填写以下配置：

```ini
# Cloudflare配置
CF_API_TOKEN=   # Cloudflare API Token
CF_ZONE_ID=     # 域名的Zone ID
CF_BASE_DOMAIN= # 你的域名

# API基础URL配置（必需）
API_BASE_URL=   # API的基础URL

# 地区配置（两种方式二选一）
# 方式1：使用逗号分隔的地区代码
API_URL_REGIONS=jp,hk,kr

# 方式2：单独配置每个地区
#API_URL_JP=jp
#API_URL_HK=hk
#API_URL_KR=kr

# CloudflareSpeedTest配置
MAX_RESULT=20    # 每个地区选择的IP数量，默认5个
MAX_LATENCY=500 # 延迟时间上限(ms)，默认200ms

# Telegram通知配置（可选）
TG_BOT_TOKEN=   # 从 @BotFather 获取
TG_CHAT_ID=     # 从 @userinfobot 获取
```

2. 在 GitHub 仓库的 Settings -> Secrets and variables -> Actions 中添加上述所有环境变量。

## 部署步骤

1. Fork 本仓库到你的 GitHub 账号

2. 配置 Cloudflare API：
   - 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
   - 在右上角的个人资料中选择 "API Tokens"
   - 创建新的 Token，选择 "Edit zone DNS" 模板
   - 设置权限：Zone - DNS - Edit
   - 设置 Zone Resources：Include - Specific zone - 选择你的域名
   - 创建 Token 并复制

3. 配置 GitHub Secrets：
   - 在仓库的 Settings -> Secrets and variables -> Actions 中添加以下 secrets：
     - `CF_API_TOKEN`: Cloudflare API Token
     - `CF_ZONE_ID`: 域名的 Zone ID（在域名概览页面右侧可以找到）
     - `CF_BASE_DOMAIN`: 你的域名
     - `API_BASE_URL`: API 的基础 URL
     - `API_URL_REGIONS`: 需要更新的地区，如 "jp,hk,kr"
     - `MAX_RESULT`: (可选) 每个地区选择的IP数量，默认5个
     - `MAX_LATENCY`: (可选) 延迟时间上限(ms)，默认200ms
     - `TG_BOT_TOKEN`: （可选）Telegram Bot Token
     - `TG_CHAT_ID`: （可选）Telegram Chat ID

4. 启用 GitHub Actions：
   - 进入仓库的 Actions 标签页
   - 点击 "I understand my workflows, go ahead and enable them"

## 运行方式

- 自动运行：每2小时自动运行一次
- 手动运行：在 GitHub Actions 页面点击 "Run workflow" 按钮

## IP测速说明

1. 测速工具：
   - 使用CloudflareSpeedTest进行测速
   - 自动下载对应系统版本的测速工具
   - 支持Windows和Linux系统

2. 测速参数：
   - `MAX_RESULT`: 每个地区选择的IP数量
     * 默认值：5
     * 建议范围：3-5
     * 数量越多，负载均衡效果越好，但可能会包含较慢的IP
   
   - `MAX_LATENCY`: 延迟时间上限(ms)
     * 默认值：200ms
     * 建议范围：200-500ms
     * 超过此延迟的IP将被丢弃
     * 设置过低可能导致可用IP不足

3. 测速流程：
   - 获取API返回的IP列表
   - 测试每个IP的延迟（TCP模式，端口443）
   - 丢弃延迟超过上限的IP
   - 选择指定数量的最快IP
   - 更新DNS记录

## Telegram 通知设置（可选）

1. 创建 Telegram Bot：
   - 在 Telegram 中找到 @BotFather
   - 发送 `/newbot` 命令
   - 按提示设置机器人名称
   - 保存获得的 Bot Token

2. 获取 Chat ID：
   - 在 Telegram 中找到 @userinfobot
   - 向机器人发送任意消息
   - 机器人会返回你的 Chat ID

3. 将 Bot Token 和 Chat ID 添加到配置中

## 注意事项

1. GitHub Actions 的免费额度：
   - 每月 2000 分钟的运行时间
   - 每2小时运行一次，每天12次，每月约360次
   - 每次运行约1分钟，每月消耗约360分钟，在免费额度内

2. DNS 记录说明：
   - 每个地区会创建一个子域名，如 jp.example.com
   - 每个子域名可以包含多个 IP 用于负载均衡
   - TTL 设置为60秒，确保 DNS 记录能够快速更新

3. 系统要求：
   - GitHub Actions使用Ubuntu 22.04
   - Python 3.x
   - 自动安装所需依赖

## 问题排查

1. 如果更新失败，请检查：
   - Cloudflare API Token 是否有正确的权限
   - Zone ID 是否正确
   - API URL 是否可以访问

2. 如果测速结果不理想：
   - 调整 MAX_LATENCY 值
   - 增加 MAX_RESULT 数量
   - 检查API返回的IP质量

3. 如果没有收到 Telegram 通知，请检查：
   - Bot Token 是否正确
   - Chat ID 是否正确
   - 是否已经与机器人进行过对话 