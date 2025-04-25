from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import pytz
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime

# 用户模型，支持多角色和多因素认证（MFA）
class User(AbstractUser):
    ROLE_CHOICES = (
        ('nnd_admin', '超级管理员'),
        ('admin', '管理员'),
        ('user', '普通用户'),
        ('readonly', '只读用户'),
        ('disabled', '禁用用户'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user', verbose_name='角色')
    mfa_secret = models.CharField(max_length=100, blank=True, null=True, verbose_name='MFA密钥')

    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = '用户'

# 域名模型
class Domain(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='所属用户')
    domain_name = models.CharField(max_length=255, verbose_name='域名')
    task_name = models.CharField(max_length=100, verbose_name='任务名称')
    check_interval = models.IntegerField(verbose_name='检测频率（秒）')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    next_check = models.DateTimeField(verbose_name='下次检测时间')
    group = models.CharField(max_length=100, blank=True, verbose_name='分组')
    labels = models.CharField(max_length=255, blank=True, verbose_name='标签')
    response_time_threshold = models.IntegerField(default=1000, verbose_name='响应时间阈值（毫秒）')
    alert_threshold = models.IntegerField(default=3, verbose_name='异常连续次数')
    notify_telegram = models.BooleanField(default=False, verbose_name='Telegram通知')
    notify_email = models.BooleanField(default=False, verbose_name='邮箱通知')
    notify_inbox = models.BooleanField(default=False, verbose_name='站内信通知')
    long_term_monitor = models.BooleanField(default=True, verbose_name='长期监控')
    end_time = models.DateField(null=True, blank=True, verbose_name='任务结束时间')
    monitor_type = models.CharField(max_length=10, default='https', choices=[('http', 'HTTP'), ('https', 'HTTPS')], verbose_name='监控类型')
    request_method = models.CharField(max_length=10, default='GET', choices=[('GET', 'GET'), ('POST', 'POST')], verbose_name='请求方式')

    class Meta:
        db_table = 'monitors'  # 将 'domain' 改为 'monitors'
        verbose_name = '监控对象'
        verbose_name_plural = '监控对象'

# 证书信息表
class Certificate(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, verbose_name='关联域名')
    issuer = models.CharField(max_length=255, verbose_name='发行者')
    expiry_date = models.DateTimeField(verbose_name='证书到期时间')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        db_table = 'certificate'
        verbose_name = '证书'
        verbose_name_plural = '证书'

# 监控结果表（域名到期）
class DomainExpiryResult(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, verbose_name='关联域名')
    check_time = models.DateTimeField(default=timezone.now, verbose_name='检测时间')
    status = models.CharField(max_length=50, verbose_name='状态')
    details = models.TextField(verbose_name='检测详情')

    class Meta:
        db_table = 'domain_expiry_result'
        verbose_name = '域名到期检测结果'
        verbose_name_plural = '域名到期检测结果'

# 监控结果表（证书到期）
class CertExpiryResult(models.Model):
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, verbose_name='关联证书')
    check_time = models.DateTimeField(default=timezone.now, verbose_name='检测时间')
    status = models.CharField(max_length=50, verbose_name='状态')
    details = models.TextField(verbose_name='检测详情')

    class Meta:
        db_table = 'cert_expiry_result'
        verbose_name = '证书到期检测结果'
        verbose_name_plural = '证书到期检测结果'

# 修改 WebsiteMonitorResult 类名和表名
class MonitorRecord(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, verbose_name='监控对象')
    check_time = models.DateTimeField(auto_now_add=True, verbose_name='检测时间')
    status = models.CharField(max_length=50, default='', verbose_name='访问状态')
    total_time = models.FloatField(null=True, verbose_name='总时间(秒)')
    dns_time = models.FloatField(null=True, verbose_name='解析时间(秒)')
    details = models.TextField(blank=True, verbose_name='详细信息')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'monitor_records'
        verbose_name = '监控记录'
        verbose_name_plural = '监控记录'

# 添加操作日志模型
class CheckLog(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, verbose_name='监控对象')
    check_time = models.DateTimeField(auto_now_add=True, verbose_name='检测时间')
    status = models.CharField(max_length=50, verbose_name='检测状态')
    operator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='操作人')
    details = models.TextField(blank=True, verbose_name='详细信息')

    class Meta:
        db_table = 'check_log'
        verbose_name = '检测日志'
        verbose_name_plural = '检测日志'

# 告警配置表
class AlertConfig(models.Model):
    telegram_token = models.CharField(max_length=255, verbose_name='Telegram Bot Token')
    telegram_chat_id = models.CharField(max_length=255, verbose_name='Telegram Chat ID')
    enabled = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        db_table = 'alert_config'
        verbose_name = '告警配置'
        verbose_name_plural = '告警配置'

# 操作日志表
class OperationLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='操作用户')
    action = models.CharField(max_length=255, verbose_name='操作内容')
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='操作时间')

    class Meta:
        db_table = 'operation_log'
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'

@login_required
def domain_form(request, domain_id=None):
    domain = None
    if domain_id:
        domain = Domain.objects.get(id=domain_id, user=request.user)

    if request.method == 'POST':
        try:
            domain_input = request.POST.get('domain_name', '').strip()
            domain_names = [name.strip() for name in domain_input.split('\n') if name.strip()] if '\n' in domain_input else [domain_input]
            
            # 获取表单数据
            data = {
                'task_name': request.POST.get('task_name', '').strip(),
                'check_interval': int(request.POST.get('check_interval', 3600)),
                'group': request.POST.get('group', '默认组').strip(),
                'monitor_type': request.POST.get('monitor_type', 'https'),
                'request_method': request.POST.get('request_method', 'GET'),
                'response_time_threshold': int(request.POST.get('response_time_threshold', 1000)),
                'alert_threshold': int(request.POST.get('alert_threshold', 3)),
                'notify_telegram': 'notify_telegram' in request.POST,
                'notify_email': 'notify_email' in request.POST,
                'notify_inbox': 'notify_inbox' in request.POST,
                'long_term_monitor': 'long_term_monitor' in request.POST,
            }

            # 处理结束时间
            end_time = request.POST.get('end_time')
            if end_time and not data['long_term_monitor']:
                data['end_time'] = datetime.strptime(end_time, '%Y-%m-%d').date()
            else:
                data['end_time'] = None

            # 检查域名是否已存在
            if not domain_id:
                if Domain.objects.filter(user=request.user, domain_name__in=domain_names).exists():
                    raise ValueError('监控对象已存在！')

            if domain:
                # 更新现有记录
                domain.domain_name = domain_names[0]
                for key, value in data.items():
                    setattr(domain, key, value)
                domain.save()
            else:
                # 创建新记录
                for domain_name in domain_names:
                    Domain.objects.create(
                        user=request.user,
                        domain_name=domain_name,
                        next_check=timezone.now(),
                        **data
                    )
            
            messages.success(request, '保存成功！')
            return redirect('domain_list')
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'保存失败：{str(e)}')
            
    groups = Domain.objects.filter(user=request.user).values_list('group', flat=True).distinct()
    return render(request, 'domain_form.html', {'domain': domain, 'groups': groups})
