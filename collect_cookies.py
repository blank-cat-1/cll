#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Playwright收集cookies - 增强版
支持动态域名检测和增强的Cloudflare处理
"""

import asyncio
import json
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 色花堂可能使用的域名列表（按优先级排序）
SEHUATANG_DOMAINS = [
    "https://sehuatang.org",
    "https://www.sehuatang.org",
    "https://sehuatang.net",
    "https://www.sehuatang.net",
    "https://sehuatang.co",
    "https://sehuatang.xyz",
    "https://www.sehuatang.co",
]

# Cloudflare 挑战页面可能的标题关键词
CF_CHALLENGE_INDICATORS = [
    "Just a moment...",
    "Checking your browser",
    "DDoS protection by Cloudflare",
    "Please Wait...",
    "Cloudflare",
    "Access denied",
    "验证中",
    "请稍候",
]

# 成功页面的标题关键词（表示已经过了 CF）
SUCCESS_INDICATORS = [
    "色花堂",
    "SEHUATANG",
    "阿尔贝·加缪",  # 某些情况下论坛首页可能显示
]


async def detect_working_domain(page, timeout=10000):
    """检测哪个域名可以正常访问"""
    for domain in SEHUATANG_DOMAINS:
        try:
            print(f"🔍 尝试访问: {domain}")
            response = await page.goto(domain, wait_until="domcontentloaded", timeout=timeout)
            
            if response and response.status < 500:
                # 检查是否被重定向
                final_url = page.url
                print(f"   → 最终URL: {final_url}")
                
                # 检查页面标题
                title = await page.title()
                print(f"   → 页面标题: {title}")
                
                # 如果标题包含色花堂相关内容，说明域名可用
                for indicator in SUCCESS_INDICATORS:
                    if indicator.lower() in title.lower():
                        print(f"✅ 找到可用域名: {domain}")
                        return domain
                
                # 即使标题不匹配，只要状态码正常也返回
                if response.status == 200:
                    print(f"✅ 域名响应正常: {domain}")
                    return domain
                    
        except Exception as e:
            print(f"   ❌ 访问失败: {e}")
            continue
    
    # 默认返回第一个
    return SEHUATANG_DOMAINS[0]


def is_cloudflare_challenge(title: str) -> bool:
    """检查是否是 Cloudflare 挑战页面"""
    title_lower = title.lower()
    for indicator in CF_CHALLENGE_INDICATORS:
        if indicator.lower() in title_lower:
            return True
    return False


async def wait_for_cloudflare_challenge(page, max_wait_time: int = 60):
    """等待 Cloudflare 挑战完成"""
    print("🛡️ 检测到Cloudflare保护页面，等待验证...")
    
    start_time = asyncio.get_event_loop().time()
    
    while True:
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > max_wait_time:
            print(f"⏱️ 等待超时（{max_wait_time}秒）")
            return False
        
        title = await page.title()
        print(f"   ⏳ 等待中... ({int(elapsed)}s) - 标题: {title}")
        
        if not is_cloudflare_challenge(title):
            print(f"✅ Cloudflare验证通过！")
            return True
        
        # 检查是否有验证码需要手动完成
        try:
            # 检查常见的 CF 验证元素
            cf_checkbox = await page.query_selector('input[type="checkbox"]')
            if cf_checkbox:
                print("   📋 检测到验证复选框，尝试点击...")
                await cf_checkbox.click()
        except:
            pass
        
        await asyncio.sleep(2)
    
    return False


async def handle_age_verification(page):
    """处理年龄验证/同意按钮"""
    print("🔍 查找年龄同意按钮...")
    
    # 更全面的选择器列表
    selectors = [
        # 中文
        "button:has-text('同意')",
        "button:has-text('进入')", 
        "button:has-text('确认')",
        "button:has-text('我已满18岁')",
        "button:has-text('满18岁')",
        "a:has-text('同意')",
        "a:has-text('进入')",
        "a:has-text('确认')",
        # 英文
        "button:has-text('Agree')",
        "button:has-text('Enter')",
        "button:has-text('Confirm')",
        "button:has-text('I am 18')",
        "button:has-text('18+')",
        "a:has-text('Enter')",
        "a:has-text('Agree')",
        # 通用
        "button.agree-btn",
        "button.enter-btn",
        "button.confirm-btn",
        "a.agree-btn",
        ".age-verification button",
        ".age-gate button",
        ".adult-warning button",
        # XPath 等效选择器
        "//button[contains(text(), '同意')]",
        "//button[contains(text(), '进入')]",
        "//a[contains(text(), '同意')]",
    ]
    
    for selector in selectors:
        try:
            if selector.startswith("//"):
                # XPath 选择器
                element = await page.query_selector(f'xpath={selector}')
            else:
                element = await page.wait_for_selector(selector, timeout=3000)
            
            if element:
                print(f"✅ 找到按钮: {selector}")
                await element.click()
                print("✅ 点击成功")
                await asyncio.sleep(2)
                return True
        except Exception as e:
            continue
    
    print("⚠️ 未找到年龄同意按钮（可能不需要）")
    return False


async def collect_cookies(target_url: str = None, headless: bool = False, max_cf_wait: int = 60):
    """收集cookies - 增强版
    
    Args:
        target_url: 目标URL（可选，不提供则自动检测）
        headless: 是否无头模式
        max_cf_wait: 最大等待Cloudflare验证时间（秒）
    """
    print("🚀 开始收集cookies...")
    
    # 获取代理配置
    proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy') or os.environ.get('HTTPS_PROXY')
    if proxy:
        print(f"🔗 使用代理: {proxy}")
        
        # 智能处理 host.docker.internal
        if 'host.docker.internal' in proxy:
            import socket
            try:
                # 尝试获取真实的宿主机IP
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                # 替换为局域网IP段
                proxy = proxy.replace('host.docker.internal', local_ip.rsplit('.', 1)[0] + '.1')
                print(f"🔗 自动修正代理地址: {proxy}")
            except:
                # 如果自动检测失败，使用常见的网关地址
                print(f"⚠️ 无法自动检测宿主机IP，请手动配置代理")

    async with async_playwright() as p:
        # 配置浏览器启动参数
        browser_args = [
            '--disable-blink-features=AutomationControlled',  # 隐藏自动化特征
            '--disable-infobars',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
        ]
        
        if proxy:
            browser_args.extend([
                f'--proxy-server={proxy}',
                '--ignore-certificate-errors',
            ])
        
        # 在Docker环境中强制使用headless模式
        is_docker = os.path.exists('/.dockerenv')
        if is_docker:
            headless = True
            print("🐳 检测到Docker环境，强制使用headless模式")
        
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=headless,
            args=browser_args
        )
        
        # 创建上下文时设置更真实的浏览器特征
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
        )
        
        # 添加初始化脚本来隐藏webdriver特征
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 隐藏自动化特征
            window.chrome = {
                runtime: {}
            };
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
        """)
        
        page = await context.new_page()
        
        try:
            # 如果没有指定目标URL，自动检测
            if target_url:
                print(f"📡 访问指定URL: {target_url}")
            else:
                print("📡 自动检测可用域名...")
                target_url = await detect_working_domain(page)
                print(f"📡 使用域名: {target_url}")
            
            # 访问目标网站
            await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            
            # 等待页面初始加载
            await asyncio.sleep(3)
            
            # 检查页面标题
            title = await page.title()
            print(f"📄 页面标题: {title}")
            
            # 处理 Cloudflare 挑战
            if is_cloudflare_challenge(title):
                cf_success = await wait_for_cloudflare_challenge(page, max_cf_wait)
                
                if not cf_success:
                    print("❌ Cloudflare验证超时")
                    
                    # 尝试截图保存（调试用）
                    if not headless:
                        await page.screenshot(path="data/cf_challenge.png")
                        print("📸 已保存CF挑战页面截图到 data/cf_challenge.png")
                    
                    return []
                
                # 重新获取标题
                title = await page.title()
                print(f"📄 验证后页面标题: {title}")
            
            # 处理年龄验证
            await handle_age_verification(page)
            
            # 额外等待确保页面完全加载
            await asyncio.sleep(3)
            
            # 最终检查页面内容
            final_title = await page.title()
            print(f"📄 最终页面标题: {final_title}")
            
            # 获取当前URL（可能有重定向）
            final_url = page.url
            print(f"🔗 最终URL: {final_url}")
            
            # 检查是否成功访问（页面内容包含预期关键词）
            try:
                page_content = await page.content()
                content_indicators = ["色花堂", "SEHUATANG", "磁力", "torrent", "magnet"]
                found_indicators = [ind for ind in content_indicators if ind.lower() in page_content.lower()]
                
                if found_indicators:
                    print(f"✅ 页面内容验证成功，找到关键词: {found_indicators}")
                else:
                    print("⚠️ 页面内容未找到预期关键词，可能访问失败")
            except:
                pass
            
            # 获取cookies
            cookies = await context.cookies()
            print(f"🍪 收集到 {len(cookies)} 个cookies")
            
            # 打印重要的cookie名称（调试用）
            important_cookies = ['cf_clearance', 'PHPSESSID', '__cf_bm']
            for cookie in cookies:
                if cookie.get('name') in important_cookies:
                    print(f"   ✨ 找到重要cookie: {cookie.get('name')}")
            
            # 保存cookies
            os.makedirs("data", exist_ok=True)
            
            # 同时保存原始格式和简化格式
            cookies_data = {
                "cookies": cookies,
                "domain": target_url,
                "collected_at": asyncio.get_event_loop().time(),
                "source_url": final_url,
                "page_title": final_title
            }
            
            with open("data/cookies.json", 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            with open("data/cookies_full.json", 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, ensure_ascii=False, indent=2)
            
            print("✅ cookies已保存到 data/cookies.json")
            
            # 如果不是headless模式，等待用户确认
            if not headless:
                input("按回车键关闭浏览器...")
            
            return cookies
            
        except PlaywrightTimeoutError as e:
            print(f"❌ 页面加载超时: {e}")
            return []
        except Exception as e:
            print(f"❌ 收集cookies失败: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            await browser.close()


async def test_cookies_validity(cookies_file: str = "data/cookies.json"):
    """测试收集的cookies是否有效"""
    print("🧪 测试cookies有效性...")
    
    if not os.path.exists(cookies_file):
        print("❌ cookies文件不存在")
        return False
    
    with open(cookies_file, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    
    if not cookies:
        print("❌ cookies文件为空")
        return False
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # 添加cookies
        await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        try:
            # 测试访问
            await page.goto("https://sehuatang.org", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            title = await page.title()
            print(f"📄 页面标题: {title}")
            
            # 检查是否还在CF挑战页面
            if is_cloudflare_challenge(title):
                print("❌ cookies无效，仍在CF挑战页面")
                return False
            
            print("✅ cookies有效！")
            return True
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            return False
        finally:
            await browser.close()


if __name__ == "__main__":
    import sys
    
    # 支持命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 测试模式
        asyncio.run(test_cookies_validity())
    else:
        # 正常收集模式
        # 可以通过环境变量设置参数
        headless = os.environ.get('HEADLESS', 'false').lower() == 'true'
        max_cf_wait = int(os.environ.get('MAX_CF_WAIT', '60'))
        
        asyncio.run(collect_cookies(headless=headless, max_cf_wait=max_cf_wait))
