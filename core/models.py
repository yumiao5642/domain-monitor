from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import pytz

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
    mfa_enabled = models.BooleanField(default=False, verbose_name='是否启用MFA')

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
    monitor_type = models.CharField(max_length=10, default='http', choices=[('http', 'HTTP'), ('https', 'HTTPS')], verbose_name='监控类型')
    request_method = models.CharField(max_length=10, default='GET', choices=[('GET', 'GET'), ('POST', 'POST')], verbose_name='请求方式')

    class Meta:
        db_table = 'domain'
        verbose_name = '域名'
        verbose_name_plural = '域名'

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

# 监控结果表（网站状态）
class WebsiteMonitorResult(models.Model):
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, verbose_name='关联域名')
    check_time = models.DateTimeField(default=timezone.now, verbose_name='检测时间')
    status_code = models.IntegerField(verbose_name='HTTP状态码')
    response_time = models.FloatField(verbose_name='响应时间（秒）')
    details = models.TextField(verbose_name='检测详情')

    class Meta:
        db_table = 'website_monitor_result'
        verbose_name = '网站监控结果'
        verbose_name_plural = '网站监控结果'

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
