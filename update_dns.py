import os
import sys
import requests
import subprocess
import tempfile
import platform
import zipfile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm
import time
import re

# 优先从环境变量加载配置
# 如果存在.env文件，则作为补充配置源
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=False)  # override=False表示不覆盖已存在的环境变量

def parse_config(config_path):
    """解析配置文件"""
    config = []
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释行
                if not line or line.startswith('#'):
                    continue
                # 处理参数=值的格式
                if '=' in line:
                    param, value = line.split('=', 1)
                    config.extend([f'-{param.strip()}', value.strip()])
                else:
                    # 处理单独的参数(如dd)
                    config.append(f'-{line.strip()}')
    except Exception as e:
        print(f"读取配置文件出错: {str(e)}")
    return config

# Cloudflare配置
CF_API_TOKEN = os.environ.get('CF_API_TOKEN')
CF_ZONE_ID = os.environ.get('CF_ZONE_ID')
CF_BASE_DOMAIN = os.environ.get('CF_BASE_DOMAIN')
API_BASE_URL = os.environ.get('API_BASE_URL')

if not API_BASE_URL:
    raise ValueError("API_BASE_URL environment variable is not set")

# 确保API_BASE_URL是完整的URL
if not API_BASE_URL.startswith(('http://', 'https://')):
    API_BASE_URL = f"https://{API_BASE_URL}"

print(f"Using API base URL: {API_BASE_URL}")

# CloudflareSpeedTest配置
SPEEDTEST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'speedtest'))  # 保存目录
IP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ip'))  # IP结果保存目录
SPEEDTEST_FILENAME = 'CloudflareST.exe' if platform.system().lower() == 'windows' else 'CloudflareST'  # 可执行文件名
SPEEDTEST_PATH = os.path.join(SPEEDTEST_DIR, SPEEDTEST_FILENAME)  # 可执行文件路径
TEST_COUNT = os.environ.get('TEST_COUNT', '2')  # 延迟测试次数
DOWNLOAD_TIMEOUT = os.environ.get('DOWNLOAD_TIMEOUT', '5')  # 下载测试超时时间(秒)
MAX_RESULT = os.environ.get('MAX_RESULT', '3')  # 最多使用几个IP
MAX_LATENCY = os.environ.get('MAX_LATENCY', '500')  # 延迟时间上限(ms)

# Telegram配置
TG_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID')

def check_speedtest():
    """检查CloudflareSpeedTest是否可用"""
    try:
        # 检查文件是否存在
        if not os.path.exists(SPEEDTEST_PATH):
            print(f"测速工具不存在: {SPEEDTEST_PATH}")
            # 在Windows系统下尝试下载
            if platform.system().lower() == 'windows':
                return download_speedtest()
            return False
            
        # 检查文件大小
        if os.path.getsize(SPEEDTEST_PATH) == 0:
            print(f"测速工具文件无效")
            # 在Windows系统下尝试重新下载
            if platform.system().lower() == 'windows':
                return download_speedtest()
            return False
            
        # 设置执行权限(Linux)
        if platform.system().lower() != 'windows':
            print(f"设置执行权限: {SPEEDTEST_PATH}")
            os.chmod(SPEEDTEST_PATH, 0o755)
            
        print(f"测速工具就绪: {SPEEDTEST_PATH}")
        return True
            
    except Exception as e:
        print(f"检查测速工具出错: {str(e)}")
        return False

def download_speedtest():
    """下载CloudflareSpeedTest（仅Windows系统）"""
    try:
        print(f"开始下载CloudflareSpeedTest...")
        
        # 确保目录存在
        os.makedirs(SPEEDTEST_DIR, exist_ok=True)
        
        # 获取系统架构
        machine = platform.machine().lower()
        
        # 确定下载文件名
        if machine == 'amd64' or machine == 'x86_64':
            filename = 'CloudflareST_windows_amd64.zip'
        else:
            filename = 'CloudflareST_windows_386.zip'
            
        # 下载文件
        url = f'https://github.com/XIU2/CloudflareSpeedTest/releases/download/v2.2.5/{filename}'
        print(f"下载地址: {url}")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        print(f"文件大小: {total_size} 字节")
        
        # 保存文件
        zip_path = os.path.join(SPEEDTEST_DIR, filename)
        print(f"保存文件到: {zip_path}")
        
        # 显示下载进度
        block_size = 8192
        downloaded_size = 0
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    progress = (downloaded_size / total_size) * 100
                    print(f"下载进度: {progress:.1f}%", end='\r')
        print("\n下载完成")
        
        # 解压文件
        print(f"开始解压文件: {zip_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(SPEEDTEST_DIR)
            print(f"解压的文件列表:")
            for name in zip_ref.namelist():
                print(f"- {name}")
                
        # 清理下载的压缩包
        print(f"清理压缩包: {zip_path}")
        os.remove(zip_path)
        
        # 验证文件
        if os.path.exists(SPEEDTEST_PATH) and os.path.getsize(SPEEDTEST_PATH) > 0:
            print(f"测速工具安装成功: {SPEEDTEST_PATH}")
            return True
        else:
            raise Exception(f"测速工具文件不存在或无效: {SPEEDTEST_PATH}")
            
    except Exception as e:
        print(f"下载CloudflareSpeedTest失败: {str(e)}")
        return False

def send_telegram_message(message):
    """发送Telegram通知"""
    if not all([TG_BOT_TOKEN, TG_CHAT_ID]):
        return
        
    try:
        url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TG_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=data)
        if not response.json()['ok']:
            print(f"发送Telegram通知失败: {response.json()['description']}")
    except Exception as e:
        print(f"发送Telegram通知出错: {str(e)}")

# 创建一个带重试机制的session
def create_session():
    session = requests.Session()
    retry = Retry(
        total=5,  # 最多重试5次
        backoff_factor=1,  # 重试间隔
        status_forcelist=[500, 502, 503, 504],  # 这些状态码会触发重试
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# 使用session发送请求
session = create_session()

def get_api_configs():
    """获取所有API配置"""
    if not CF_BASE_DOMAIN:
        raise ValueError("CF_BASE_DOMAIN environment variable is not set")
        
    configs = []
    
    # 处理API_URL_REGIONS配置
    regions = os.environ.get('API_URL_REGIONS', '').strip()
    if regions:
        for region in regions.split(','):
            region = region.strip().lower()
            if region:
                # 构建完整的API URL
                api_url = f"{API_BASE_URL}/{region}"
                configs.append({
                    'region': region,
                    'url': api_url,
                    'record_name': f"{region}.{CF_BASE_DOMAIN}"
                })
    
    # 处理单独的API_URL_XX配置（优先级更高）
    for key, value in os.environ.items():
        if key.startswith('API_URL_') and key != 'API_URL_REGIONS' and value:
            region = key.replace('API_URL_', '').lower()
            record_name = f"{region}.{CF_BASE_DOMAIN}"
            
            # 检查是否是完整的URL
            if value.startswith('http://') or value.startswith('https://'):
                api_url = value
            else:
                # 如果不是完整URL，使用基础URL
                api_url = f"{API_BASE_URL}/{value.lstrip('/')}"
                    
            # 更新或添加配置（替换已存在的同名region配置）
            config_index = next((i for i, conf in enumerate(configs) if conf['region'] == region), -1)
            config = {
                'region': region,
                'url': api_url,
                'record_name': record_name
            }
            
            if config_index >= 0:
                configs[config_index] = config
            else:
                configs.append(config)
                
    return configs

def get_region_ips(api_url):
    """获取地区所有IP"""
    try:
        print(f"正在请求API: {api_url}")
        response = session.get(api_url)
        
        data = response.json()
        if data['status'] == 'success':
            ips = [proxy['ip'] for proxy in data['proxies']]
            print(f"成功获取到 {len(ips)} 个IP")
            return ips if ips else None
        else:
            print(f"API返回失败状态: {data['status']}")
    except Exception as e:
        print(f"获取IP失败: {str(e)}")
        print(f"错误类型: {type(e)}")
        if hasattr(e, '__traceback__'):
            import traceback
            print(f"错误堆栈: {traceback.format_exc()}")
    return None

def test_ips_speed(ips, region):
    """使用CloudflareSpeedTest测试IP速度"""
    if not ips:
        return None
        
    try:
        # 检查CloudflareST是否存在
        if not os.path.exists(SPEEDTEST_PATH):
            print(f"错误: CloudflareST工具不存在: {SPEEDTEST_PATH}")
            return None
            
        # 检查CloudflareST是否可执行
        if not os.access(SPEEDTEST_PATH, os.X_OK) and platform.system().lower() != 'windows':
            print(f"错误: CloudflareST工具没有执行权限")
            return None
            
        # 确保ip目录存在并可写
        try:
            os.makedirs(IP_DIR, exist_ok=True)
            test_file = os.path.join(IP_DIR, 'test.txt')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            print(f"错误: IP目录不可写: {str(e)}")
            return None
        
        # 创建临时文件来存储IP列表
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_ip_file:
            print(f"创建IP列表文件: {temp_ip_file.name}")
            for ip in ips:
                temp_ip_file.write(f"{ip}\n")
                
        # 创建结果文件路径（使用地区名命名）
        result_file = os.path.join(IP_DIR, f"{region}.csv")
        
        # 构建命令
        cmd = [
            SPEEDTEST_PATH,
            '-f', temp_ip_file.name,    # IP列表文件
            '-o', result_file,          # 结果文件
        ]
        
        # 读取配置文件
        config_path = os.environ.get('SPEEDTEST_CONFIG', 'config.conf')
        config_path = os.path.join(os.path.dirname(__file__), config_path)
        
        if os.path.exists(config_path):
            print(f"使用配置文件: {config_path}")
            config_params = parse_config(config_path)
            cmd.extend(config_params)
        else:
            print(f"配置文件不存在: {config_path}, 使用默认参数")
            # 使用默认参数
            cmd.extend([
                '-n', '200',    # 延迟测速线程数
                '-t', '4',      # 延迟测速次数
                '-tp', '443',   # 测速端口
                '-tl', '500',   # 延迟上限
                '-sl', '10',    # 选择的IP数量
                '-dd'           # 禁用下载测速
            ])
        
        print("开始测速...")
        print(f"执行命令: {' '.join(cmd)}")
        
        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 获取输出
        stdout, stderr = process.communicate()
        print("CloudflareST输出:")
        print(stdout)
        if stderr:
            print("CloudflareST错误:")
            print(stderr)
        print(f"CloudflareST返回码: {process.returncode}")
        
        # 检查结果文件
        if not os.path.exists(result_file):
            print(f"结果文件不存在: {result_file}")
            return None
            
        if os.path.getsize(result_file) == 0:
            print("结果文件为空")
            return None
            
        print(f"结果文件存在: {result_file}")
        print(f"结果文件大小: {os.path.getsize(result_file)} 字节")
        
        # 读取结果文件
        result_ips = []
        with open(result_file, 'r', encoding='utf-8') as f:
            print("结果文件内容:")
            content = f.read()
            print(content)
            
            # 重新读取文件来处理IP
            f.seek(0)
            next(f)  # 跳过标题行
            for line in f:
                if line.strip():
                    ip = line.split(',')[0].strip()
                    result_ips.append(ip)
                    
        if not result_ips:
            print("未找到有效的IP")
            return None
            
        print(f"测速完成，获取到 {len(result_ips)} 个有效IP")
        
        # 创建txt格式的结果文件
        txt_file = os.path.join(IP_DIR, f"{region}.txt")
        with open(txt_file, 'w', encoding='utf-8') as f:
            for ip in result_ips:
                f.write(f"{ip}#{region}\n")
        print(f"已生成txt格式结果文件: {txt_file}")
        
        return result_ips
            
    except Exception as e:
        print(f"测速过程出错: {str(e)}")
        import traceback
        print(f"错误堆栈: {traceback.format_exc()}")
        return None
    finally:
        # 清理临时文件
        try:
            if 'temp_ip_file' in locals():
                os.unlink(temp_ip_file.name)
                print("已删除IP列表文件")
        except Exception as e:
            print(f"清理临时文件出错: {str(e)}")

def create_dns_records(headers, url, record_name, ips):
    """创建新的DNS记录"""
    try:
        # 创建主记录
        data = {
            'type': 'A',
            'name': record_name,
            'content': ips[0],
            'ttl': 60,
            'proxied': False
        }
        
        response = session.post(url, headers=headers, json=data)
        result = response.json()
        
        if result['success']:
            print(f"主DNS记录创建成功 [{record_name}]: {ips[0]}")
            
            # 添加额外的IP记录
            for ip in ips[1:]:
                data = {
                    'type': 'A',
                    'name': record_name,
                    'content': ip,
                    'ttl': 60,
                    'proxied': False
                }
                response = session.post(url, headers=headers, json=data)
                if response.json()['success']:
                    print(f"添加额外IP成功 [{record_name}]: {ip}")
                else:
                    print(f"添加额外IP失败 [{record_name}]: {ip}")
            return True
        else:
            print(f"DNS记录创建失败: {result['errors']}")
    except Exception as e:
        print(f"创建DNS记录失败: {str(e)}")
    return False

def update_cloudflare_dns(ips, record_name):
    """更新或创建Cloudflare DNS记录"""
    if not all([CF_API_TOKEN, CF_ZONE_ID]):
        raise ValueError("Missing required Cloudflare configuration")
        
    headers = {
        'Authorization': f'Bearer {CF_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.cloudflare.com/client/v4/zones/{CF_ZONE_ID}/dns_records'
    
    try:
        # 获取所有现有记录
        response = session.get(url, headers=headers)
        records = response.json()
        
        if records['success']:
            # 删除旧的记录
            deleted = False
            for record in records['result']:
                if record['name'] == record_name:
                    record_id = record['id']
                    delete_url = f'{url}/{record_id}'
                    try:
                        session.delete(delete_url, headers=headers)
                        print(f"删除旧DNS记录: {record['name']} ({record['content']})")
                        deleted = True
                    except Exception as e:
                        print(f"删除DNS记录失败 [{record['name']}]: {str(e)}")
            
            # 如果有删除操作,等待5秒让删除生效
            if deleted:
                print("等待删除操作生效...")
                time.sleep(5)
            
            # 创建新记录
            return create_dns_records(headers, url, record_name, ips)
        else:
            print(f"获取DNS记录失败: {records['errors']}")
    except Exception as e:
        print(f"操作DNS记录失败: {str(e)}")
    return False

def main():
    """主函数"""
    start_time = datetime.now()
    print(f"开始运行 - {start_time}")
    
    # 收集所有消息
    messages = []
    def log(message):
        print(message)
        messages.append(message)
    
    try:
        # 检查CloudflareSpeedTest
        log("检查CloudflareSpeedTest...")
        if not check_speedtest():
            log("CloudflareSpeedTest不可用，程序退出")
            return
        log("CloudflareSpeedTest准备就绪")
        
        configs = get_api_configs()
        if not configs:
            log("未找到任何API配置")
            return
        
        # 处理每个地区
        for config in configs:
            region = config['region']
            api_url = config['url']
            record_name = config['record_name']
            
            log(f"\n处理地区: {region}")
            log(f"API URL: {api_url}")
            
            # 获取IP列表
            ips = get_region_ips(api_url)
            if not ips:
                log(f"未找到可用的IP")
                continue
                
            log(f"获取到 {len(ips)} 个IP:")
            for ip in ips:
                log(f"- {ip}")
            
            # 测试该地区的IP速度
            log(f"\n开始测试 {region} 地区IP速度...")
            tested_ips = test_ips_speed(ips, region)  # 传入region参数
            if not tested_ips:
                log(f"{region} 地区IP测速失败")
                continue
                
            log(f"{region} 地区测速完成,选择了 {len(tested_ips)} 个最快的IP:")
            for ip in tested_ips:
                log(f"- {ip}")
            
            # 更新DNS记录
            if update_cloudflare_dns(tested_ips, record_name):
                log(f"{region} DNS记录更新成功")
            else:
                log(f"{region} DNS记录更新失败")
    
    except Exception as e:
        error_message = f"发生错误: {str(e)}"
        log(error_message)
    
    # 发送汇总消息到Telegram
    end_time = datetime.now()
    duration = end_time - start_time
    summary = f"DNS更新任务完成\n开始时间: {start_time}\n结束时间: {end_time}\n耗时: {duration}\n\n详细日志:\n" + "\n".join(messages)
    send_telegram_message(summary)

if __name__ == "__main__":
    main() 
