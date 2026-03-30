# Cookie 获取失败问题修复方案

## 问题分析

原代码存在以下问题：

### 1. 域名硬编码
```python
# 原代码
target_url: str = "https://sehuatang.org"  # 硬编码域名
```
色花堂网站经常更换域名，硬编码会导致访问失败。

### 2. Cloudflare 检测逻辑不完善
```python
# 原代码只检测两个哲学家名字
if "阿尔贝·加缪" in title or "约翰·洛克" in title:
```
Cloudflare 已经更新，现在的挑战页面标题可能是 "Just a moment..."、"Checking your browser" 等。

### 3. 缺少自动化特征隐藏
headless 浏览器容易被 Cloudflare 识别为机器人。

---

## 修复内容

### 文件 1: `collect_cookies.py` (增强版)

**主要改进：**

1. **动态域名检测**
   - 维护一个域名列表，自动检测哪个可用
   - 支持自动切换到备用域名

2. **增强的 Cloudflare 处理**
   - 检测更多 CF 挑战页面标题
   - 支持等待验证完成（可配置超时时间）
   - 自动点击验证复选框

3. **隐藏自动化特征**
   - 隐藏 `navigator.webdriver`
   - 设置真实的 User-Agent
   - 添加浏览器指纹伪装

4. **智能代理处理**
   - 自动检测宿主机 IP
   - 不再硬编码 `192.168.31.85`

5. **增强的日志和调试**
   - 详细的执行日志
   - 可选的截图保存
   - cookies 有效性测试

### 文件 2: `domain_detector.py` (新增)

**功能：**

- 并发检测多个域名可用性
- 缓存检测结果
- 提供同步和异步两种接口

---

## 使用方法

### 方法一：直接替换文件

```bash
# 1. 备份原文件
cp collect_cookies.py collect_cookies.py.bak

# 2. 复制新文件到项目目录
cp collect_cookies_new.py collect_cookies.py
cp domain_detector.py ./

# 3. 重启服务
docker-compose restart
```

### 方法二：手动导入 Cookie（推荐用于紧急情况）

如果自动获取仍然失败，可以手动导入：

```bash
# 1. 在本地浏览器访问色花堂
# 2. 登录后按 F12 打开开发者工具
# 3. 切换到 Application > Cookies
# 4. 导出 cookies（可以使用 EditThisCookie 插件）

# 5. 将导出的 cookies 保存为 data/cookies.json
# 格式示例：
[
  {
    "name": "cf_clearance",
    "value": "xxx...",
    "domain": ".sehuatang.org",
    "path": "/",
    "secure": true
  }
]

# 6. 重启服务
docker-compose restart
```

### 方法三：使用 curl_cffi（高级）

如果 Cloudflare 验证严格，可以考虑使用 `curl_cffi` 库模拟真实浏览器 TLS 指纹：

```python
# requirements.txt 添加
curl_cffi>=0.5.0

# 使用示例
from curl_cffi import requests

response = requests.get(
    "https://sehuatang.org",
    impersonate="chrome120",  # 模拟 Chrome 120
    proxies={"https": "http://your-proxy:port"}
)
```

---

## 环境变量配置

新增以下环境变量支持：

```bash
# .env 文件
HEADLESS=true              # 是否无头模式
MAX_CF_WAIT=120            # Cloudflare 验证最大等待时间（秒）
HTTP_PROXY=http://host:port  # 代理地址
```

---

## 测试

```bash
# 测试 cookie 收集
python collect_cookies.py

# 测试 cookies 有效性
python collect_cookies.py --test

# 测试域名检测
python domain_detector.py
```

---

## 常见问题

### Q: Docker 环境下仍然失败？

A: Docker headless 模式更容易被识别，建议：
1. 使用代理
2. 增加等待时间：`MAX_CF_WAIT=180`
3. 考虑手动导入 cookies

### Q: 代理配置后还是不行？

A: 检查：
1. 代理是否支持 HTTPS
2. 代理 IP 是否被目标网站封禁
3. 确认 `HTTP_PROXY` 环境变量格式正确

### Q: 如何知道哪个域名现在可用？

A: 运行：
```bash
python domain_detector.py
```

---

## 下一步建议

1. **监控域名变化**：定时检测域名可用性并通知
2. **Cookie 持久化**：增加 cookie 有效期检测和自动刷新
3. **失败通知**：集成 Telegram/邮件通知
4. **备用方案**：如果 CF 验证失败，自动切换到手动导入模式

---

## 文件清单

- `collect_cookies.py` - 增强版 cookie 收集脚本
- `domain_detector.py` - 域名检测模块
- `README_FIX.md` - 本说明文档
