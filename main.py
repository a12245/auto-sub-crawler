import requests
import re
import base64
import os
from urllib.parse import urlparse

# 配置目标：你要监控的 TG 频道 Web 预览地址
# 注意：/s/ 是关键，它允许无登录访问
TARGET_URL = "https://t.me/s/wxdy666"

# 伪装头，防止被反爬
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_page(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[-] Error fetching Telegram page: {e}")
        return ""

def extract_links(html):
    # 暴力正则：匹配用户指定的特定域名格式，只要带有 token 的都抓
    # 如果你想抓所有类型的订阅，可以放宽正则
    pattern = r'https?://api\.dingyueapi\.win/api/v1/client/subscribe\?token=[a-zA-Z0-9]+'
    links = set(re.findall(pattern, html))
    print(f"[*] Found {len(links)} potential subscription links.")
    return links

def download_and_merge_subs(links):
    merged_content = []
    
    for link in links:
        try:
            print(f"[*] Downloading content from: {link}")
            # GitHub Action 的服务器在海外，下载速度极快，无需代理
            resp = requests.get(link, headers=HEADERS, timeout=5)
            if resp.status_code == 200:
                content = resp.text.strip()
                # 尝试 Base64 解码，确认是有效节点数据
                try:
                    # 补全 padding 防止解码错误
                    missing_padding = len(content) % 4
                    if missing_padding:
                        content += '=' * (4 - missing_padding)
                    decoded = base64.b64decode(content).decode('utf-8')
                    # 将解码后的节点行添加到列表
                    merged_content.extend(decoded.splitlines())
                    print(f"    [+] Successfully merged nodes from {link}")
                except Exception:
                    # 如果不是 Base64，可能是明文配置或其他格式，这里做简单处理或忽略
                    # 极简模式：假设大部分都是 Base64 编码的 vmess/ss/trojan 链接
                    print(f"    [-] Content not valid Base64, skipping.")
        except Exception as e:
            print(f"    [-] Failed to fetch sub link: {e}")

    # 去重
    unique_nodes = list(set(merged_content))
    print(f"[*] Total unique nodes after merge: {len(unique_nodes)}")
    
    # 重新编码为 Base64
    if unique_nodes:
        raw_str = "\n".join(unique_nodes)
        final_b64 = base64.b64encode(raw_str.encode('utf-8')).decode('utf-8')
        return final_b64
    return None

def main():
    html = fetch_page(TARGET_URL)
    if not html:
        return

    links = extract_links(html)
    if not links:
        print("[-] No links found.")
        return

    final_data = download_and_merge_subs(links)
    
    if final_data:
        with open("subscribed_nodes.txt", "w", encoding="utf-8") as f:
            f.write(final_data)
        print("[+] Successfully wrote subscribed_nodes.txt")
    else:
        print("[-] No valid data merged.")

if __name__ == "__main__":
    main()
