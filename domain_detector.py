#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名检测和配置模块
动态检测色花堂可用域名
"""

import asyncio
import aiohttp
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

# 已知的色花堂域名列表（会定期更新）
KNOWN_DOMAINS = [
    "sehuatang.org",
    "www.sehuatang.org", 
    "sehuatang.net",
    "www.sehuatang.net",
    "sehuatang.co",
    "www.sehuatang.co",
    "sehuatang.xyz",
    "sehuatang.life",
    "sehuatang.one",
]


async def check_domain_availability(domain: str, timeout: int = 10) -> tuple[bool, int, Optional[str]]:
    """
    检查单个域名是否可用
    
    Returns:
        (is_available, status_code, final_url)
    """
    url = f"https://{domain}"
    
    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                url, 
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            ) as response:
                final_url = str(response.url)
                return True, response.status, final_url
                
    except asyncio.TimeoutError:
        logger.debug(f"{domain} - 超时")
        return False, 0, None
    except Exception as e:
        logger.debug(f"{domain} - 错误: {e}")
        return False, 0, None


async def find_working_domain(domains: List[str] = None) -> Optional[str]:
    """
    并发检测多个域名，返回第一个可用的
    
    Args:
        domains: 要检测的域名列表，None则使用默认列表
        
    Returns:
        可用的域名（包含https://），如果都不可用返回None
    """
    if domains is None:
        domains = KNOWN_DOMAINS
    
    logger.info(f"开始检测 {len(domains)} 个域名...")
    
    # 并发检测所有域名
    tasks = [check_domain_availability(domain) for domain in domains]
    results = await asyncio.gather(*tasks)
    
    # 找出第一个可用的域名
    for domain, (is_available, status_code, final_url) in zip(domains, results):
        if is_available:
            logger.info(f"✅ 找到可用域名: {domain} (状态码: {status_code})")
            logger.info(f"   最终URL: {final_url}")
            return f"https://{domain}"
    
    logger.warning("❌ 所有域名都不可用")
    return None


def get_default_domain() -> str:
    """获取默认域名（同步版本，用于配置）"""
    return "https://sehuatang.org"


# 域名配置类
class DomainConfig:
    """域名配置管理"""
    
    def __init__(self):
        self._current_domain = None
        self._last_check_time = 0
        self._check_interval = 3600  # 1小时重新检测一次
    
    @property
    def current_domain(self) -> str:
        """获取当前域名"""
        if self._current_domain is None:
            self._current_domain = get_default_domain()
        return self._current_domain
    
    async def refresh_domain(self) -> str:
        """刷新并返回当前可用的域名"""
        domain = await find_working_domain()
        if domain:
            self._current_domain = domain
            self._last_check_time = asyncio.get_event_loop().time()
        return self.current_domain


# 全局实例
domain_config = DomainConfig()


if __name__ == "__main__":
    # 测试域名检测
    async def test():
        domain = await find_working_domain()
        print(f"\n检测到可用域名: {domain}")
    
    asyncio.run(test())
