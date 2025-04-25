import requests
from datetime import datetime, timedelta
import time
from .models import MonitorRecord, CheckLog

def get_domain_stats(domain):
    """
    获取域名的统计信息。
    :param domain: Domain 模型实例
    :return: 包含可用率、最后检测时间和响应时间的字典
    """
    # 假设 Domain 模型有以下字段：availability, last_check_time, last_response_time
    # 如果这些字段不存在，可以根据实际需求修改
    stats = {
        'availability': getattr(domain, 'availability', 0),  # 可用率，默认为0
        'last_check_time': getattr(domain, 'last_check_time', None),  # 最后检测时间
        'last_response_time': getattr(domain, 'last_response_time', None),  # 最后响应时间
    }
    return stats

def format_interval(seconds):
    """
    将秒数格式化为人类可读的时间间隔。
    :param seconds: 检测频率（秒）
    :return: 格式化后的字符串，例如“1小时30分钟”
    """
    if not seconds:
        return "未知"
    delta = timedelta(seconds=seconds)
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    hours += delta.days * 24
    parts = []
    if hours:
        parts.append(f"{hours}小时")
    if minutes:
        parts.append(f"{minutes}分钟")
    if seconds:
        parts.append(f"{seconds}秒")
    return " ".join(parts) if parts else "0秒"

def check_domain_status(domain, user):
    """检测域名状态"""
    url = f"{domain.monitor_type}://{domain.domain_name}"
    start_time = time.time()
    dns_start = time.time()
    
    try:
        # 发送请求
        response = requests.get(url, timeout=10)
        end_time = time.time()
        
        # 计算时间
        total_time = end_time - start_time
        dns_time = end_time - dns_start
        
        # 记录检测结果
        record = MonitorRecord.objects.create(
            domain=domain,
            status=str(response.status_code),
            total_time=total_time,
            dns_time=dns_time,
            details=f"HTTP {response.status_code}"
        )
        
        # 记录操作日志
        CheckLog.objects.create(
            domain=domain,
            status='成功',
            operator=user,
            details=f"成功检测域名 {domain.domain_name}"
        )
        
        return True
        
    except Exception as e:
        # 记录失败结果
        MonitorRecord.objects.create(
            domain=domain,
            status='失败',
            total_time=time.time() - start_time,
            dns_time=time.time() - dns_start,
            details=str(e)
        )
        
        # 记录操作日志
        CheckLog.objects.create(
            domain=domain,
            status='失败',
            operator=user,
            details=f"检测失败: {str(e)}"
        )
        
        return False
