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
        try:
            decoded_str = decoded.decode('utf-8')
            # 检查是否包含常见协议头
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
        time_tag = msg.find('time', class_='time')
        if not time_tag or not time_tag.get('datetime'):
            continue
        
        msg_dt_str = time_tag['datetime']
        msg_date = msg_dt_str.split('T')[0]
        
        if msg_date in target_dates:
            text_div = msg.find('div', class_='tgme_widget_message_text')
            if not text_div:
                continue
            
            urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text_div.get_text())
            for a_tag in text_div.find_all('a', href=True):
                urls.append(a_tag['href'])

            for url in urls:
                url = url.strip().rstrip('.,;)')
                if 't.me/' in url and 'joinchat' not in url: 
                    continue 
                extracted_urls.add(url)

    print(f"[*] Scanned messages. Found {len(extracted_urls)} candidate URLs.")
    return list(extracted_urls)

def process_links(urls):
    all_nodes = []
    for url in urls:
        try:
            print(f"[*] Probing: {url}")
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            content = r.text.strip()
            
            is_b64, decoded_text = is_base64(content)
            if is_b64:
                print(f"    [+] Valid Base64 subscription found!")
                all_nodes.extend(decoded_text.splitlines())
                continue
            
            if any(content.startswith(p) for p in ['vmess://', 'vless://', 'ss://', 'trojan://']):
                 print(f"    [+] Plaintext node list found!")
                 all_nodes.extend(content.splitlines())
                 continue
        except Exception as e:
            print(f"    [-] Failed: {str(e)[:50]}")
    return all_nodes

def main():
    candidate_urls = fetch_and_parse_channel()
    if not c
