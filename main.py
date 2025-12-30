import requests
import re
import base64
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# 目标频道
TARGET_URL = "https://t.me/s/wxdy666"

# 伪装头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_target_dates():
    """获取UTC时间的今天和昨天的日期字符串 (YYYY-MM-DD)"""
    today = datetime.datetime.now(datetime.timezone.utc)
    yesterday = today - datetime.timedelta(days=1)
    return {today.strftime('%Y-%m-%d'), yesterday.strftime('%Y-%m-%d')}

def is_base64(s):
    """极其暴力的Base64检测"""
    try:
        # 移除可能的空白字符
        s = s.strip()
        if not s: return False
        # 长度要是4的倍数，不足补=
        padding = len(s) % 4
        if padding:
            s += '=' * (4 - padding)
        decoded = base64.b64decode(s, validate=True)
        # 再次编码对比，或者检查解码后是否包含常见节点关键字
        # 为了极致宽容，只要能解码且包含部分非乱码字符即可，这里我们检查常见协议头
        try:
            decoded_str = decoded.decode('utf-8')
            # 检查是否包含常见协议头 (vmess, vless, trojan, ss, ssr, hysteria)
            if any(proto in decoded_str for proto in ['vmess://', 'vless://', 'trojan://', 'ss://', 'ssr://', 'hysteria://']):
                return True, decoded_str
        except:
            pass
        return False, None
    except Exception:
        return False, None

def fetch_and_parse_channel():
    print(f"[*] Starting hunt on {TARGET_URL}...")
    try:
        resp = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[-] Failed to open channel: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    messages = soup.find_all('div', class_='tgme_widget_message')
    
    target_dates = get_target_dates()
    print(f"[*] Targeting dates (UTC): {target_dates}")

    extracted_urls = set()

    for msg in messages:
        # 提取时间
        time_tag = msg.find('time', class_='time')
        if not time_tag or not time_tag.get('datetime'):
            continue
        
        # 解析时间：格式通常为 2025-12-30T14:22:05+00:00
        msg_dt_str = time_tag['datetime']
        msg_date = msg_dt_str.split('T')[0] # 取出 YYYY-MM-DD
        
        if msg_date in target_dates:
            # 提取该消息内的所有文本
            text_div = msg.find('div', class_='tgme_widget_message_text')
            if not text_div:
                continue
            
            # 使用正则暴力提取所有 URL
            # 只要是 http/https 开头的都抓，宁可错杀三千
            text_content = str(text_div) # 用 str 包含 html 标签，防止 text 丢失链接
            urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text_div.get_text())
            
            # 针对 <a href="..."> 的情况做补充
            for a_tag in text_div.find_all('a', href=True):
                urls.append(a_tag['href'])

            for url in urls:
                # 简单清洗
                url = url.strip().rstrip('.,;)')
                # 过滤掉 Telegram 内部链接和显而易见的无关链接
                if 't.me/' in url and 'joinchat' not in url: 
                    continue # 忽略普通频道跳转，保留可能的私有车链接
                extracted_urls.add(url)

    print(f"[*] Scanned messages. Found {len(extracted_urls)} candidate URLs.")
    return list(extracted_urls)

def process_links(urls):
    all_nodes = []
    
    for url in urls:
        try:
            print(f"[*] Probing: {url}")
            # 某些订阅链接需要 User-Agent 才能吐数据
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
                
            content = r.text.strip()
            
            # 判定 1: 内容直接是 Base64 编码的订阅
            is_b64, decoded_text = is_base64(content)
            if is_b64:
                print(f"    [+] Valid Base64 subscription found!")
                all_nodes.extend(decoded_text.splitlines())
                continue
            
            # 判定 2: 内容是明文节点列表 (一行一个 vmess://...)
            if any(content.startswith(p) for p in ['vmess://', 'vless://', 'ss://', 'trojan://']):
                 print(f"    [+] Plaintext node list found!")
                 all_nodes.extend(content.splitlines())
                 continue
                 
            # 判定 3: 可能是 Clash 配置 (yaml)，这个比较复杂，为了“极端”效率，
            # 我们暂且只处理能提取出 proxies 字段的情况，或者直接放弃 Clash 格式只抓通用格式
            # 既然你要“汇总在一个订阅链接”，通常是指 Base64 格式。
            # 这里如果不兼容 Clash 转换，直接跳过。
            
        except Exception as e:
            print(f"    [-] Failed: {str(e)[:50]}")
            
    return all_nodes

def main():
    candidate_urls = fetch_and_parse_channel()
    if not candidate_urls:
        print("[-] No URLs found in today/yesterday messages.")
        return

    nodes = process_links(candidate_urls)
    
    # 去重
    nodes = list(set(nodes))
    # 过滤空行和无效行
    nodes = [n for n in nodes if n and '://' in n]
    
    print(f"[*] Total valid nodes extracted: {len(nodes)}")
    
    if nodes:
        # 聚合
        final_str = "\n".join(nodes)
        # 编码回 Base64
        final_b64 = base64.b64encode(final_str.encode('utf-8')).decode('utf-8')
        
        with open("subscribed_nodes.txt", "w", encoding="utf-8") as f:
            f.write(final_b64)
        print("[+] Success! 'subscribed_nodes.txt' generated.")
    else:
        # 如果没抓到，创建一个空文件或者保留旧的，防止报错，这里选择创建空的提示信息
        print("[-] No valid nodes merged.")

if __name__ == "__main__":
    main()
