from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import IntegrityError
from django.db.models import Q, Count, Case, When, IntegerField
from .models import Domain, User, AlertConfig, DomainExpiryResult, CertExpiryResult, WebsiteMonitorResult, Certificate
from django.utils import timezone
import pytz
import pyotp
import qrcode
from io import BytesIO
import base64
from django.contrib.auth import update_session_auth_hash
from datetime import datetime

# 登录视图
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        mfa_code = request.POST.get('mfa_code')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.mfa_enabled:
                totp = pyotp.TOTP(user.mfa_secret)
                if not totp.verify(mfa_code):
                    return render(request, 'login.html', {'error': 'MFA验证码错误'})
            login(request, user)
            return redirect('dashboard')
        return render(request, 'login.html', {'error': '用户名或密码错误'})
    return render(request, 'login.html')

# 仪表板视图
@login_required
def dashboard(request):
    if request.user.role == 'nnd_admin':
        domains = Domain.objects.all()
    else:
        domains = Domain.objects.filter(user=request.user)
    stats = {
        'domain_count': domains.count(),
        'cert_count': Certificate.objects.count(),
        'alert_count': DomainExpiryResult.objects.filter(status='异常').count() + \
                       CertExpiryResult.objects.filter(status='异常').count() + \
                       WebsiteMonitorResult.objects.filter(status_code__gte=400).count(),
    }
    return render(request, 'dashboard.html', {'stats': stats})

# 域名列表视图
@login_required
def domain_list(request):
    if request.user.role == 'nnd_admin':
        domains = Domain.objects.all()
    else:
        domains = Domain.objects.filter(user=request.user)

    # 查询条件
    name = request.GET.get('name', '')
    domain_name = request.GET.get('domain_name', '')
    group = request.GET.get('group', '')
    time_range = request.GET.get('time_range', '')

    if name:
        domains = domains.filter(task_name__icontains=name)
    if domain_name:
        domains = domains.filter(domain_name__icontains=domain_name)
    if group:
        domains = domains.filter(group=group)
    if time_range:
        try:
            start_time, end_time = time_range.split(' - ')
            start_dt = datetime.strptime(start_time, '%Y-%m-%d')
            end_dt = datetime.strptime(end_time, '%Y-%m-%d')
            start_dt = pytz.timezone('Asia/Shanghai').localize(start_dt)
            end_dt = pytz.timezone('Asia/Shanghai').localize(end_dt.replace(hour=23, minute=59, second=59))
            domains = domains.filter(create_time__range=(start_dt, end_dt))
        except ValueError:
            pass

    # 计算可用率、最新检测数据和格式化频率
    domain_data = []
    for domain in domains:
        monitor_results = WebsiteMonitorResult.objects.filter(domain=domain).order_by('-check_time')
        total_checks = monitor_results.count()
        successful_checks = monitor_results.filter(status_code__lt=400).count()
        availability = (successful_checks / total_checks * 100) if total_checks > 0 else 0
        latest_result = monitor_results.first()
        # 格式化检测频率
        interval = domain.check_interval
        if interval >= 3600:
            formatted_interval = f"{interval // 3600}（小时）"
        elif interval >= 60:
            formatted_interval = f"{interval // 60}（分钟）"
        else:
            formatted_interval = f"{interval}（秒）"
        domain_data.append({
            'domain': domain,
            'availability': round(availability, 2),
            'last_check_time': latest_result.check_time if latest_result else None,
            'last_response_time': latest_result.response_time if latest_result else None,
            'formatted_interval': formatted_interval,
        })

    return render(request, 'domain_list.html', {
        'domain_data': domain_data,
        'name': name,
        'domain_name': domain_name,
        'group': group,
        'time_range': time_range,
    })

# 添加/编辑域名视图
@login_required
def domain_form(request, domain_id=None):
    if domain_id:
        domain = Domain.objects.get(id=domain_id)
    else:
        domain = None
    if request.method == 'POST':
        try:
            domain_name = request.POST.get('domain_name')
            task_name = request.POST.get('task_name')
            check_interval = int(request.POST.get('check_interval'))
            check_domain = 'check_domain' in request.POST
            check_cert = 'check_cert' in request.POST
            check_https = 'check_https' in request.POST
            group = request.POST.get('group', '')
            template = request.POST.get('template', '')
            if domain:
                domain.domain_name = domain_name
                domain.task_name = task_name
                domain.check_interval = check_interval
                domain.check_domain = check_domain
                domain.check_cert = check_cert
                domain.check_https = check_https
                domain.group = group
                domain.save()
            else:
                Domain.objects.create(
                    user=request.user,
                    domain_name=domain_name,
                    task_name=task_name,
                    check_interval=check_interval,
                    check_domain=check_domain,
                    check_cert=check_cert,
                    check_https=check_https,
                    group=group,
                    next_check=timezone.now()
                )
            return redirect('domain_list')
        except IntegrityError:
            return render(request, 'domain_form.html', {'error': '域名已存在', 'domain': domain})
    # 模拟监控模板
    templates = [
        {'name': '标准监控', 'interval': 3600, 'check_domain': True, 'check_cert': True, 'check_https': True},
        {'name': '高频监控', 'interval': 300, 'check_domain': True, 'check_cert': False, 'check_https': True},
        {'name': '低频监控', 'interval': 86400, 'check_domain': True, 'check_cert': True, 'check_https': False},
    ]
    return render(request, 'domain_form.html', {'domain': domain, 'templates': templates})

# 告警配置视图
@login_required
def alert_config(request):
    if request.method == 'POST':
        telegram_token = request.POST.get('telegram_token')
        telegram_chat_id = request.POST.get('telegram_chat_id')
        enabled = 'enabled' in request.POST
        AlertConfig.objects.update_or_create(
            id=1,
            defaults={
                'telegram_token': telegram_token,
                'telegram_chat_id': telegram_chat_id,
                'enabled': enabled
            }
        )
        return redirect('alert_config')
    config = AlertConfig.objects.first()
    return render(request, 'alert_config.html', {'config': config})

# MFA设置视图
@login_required
def mfa_setup(request):
    if request.method == 'POST':
        mfa_code = request.POST.get('mfa_code')
        if request.user.mfa_secret:
            totp = pyotp.TOTP(request.user.mfa_secret)
            if totp.verify(mfa_code):
                request.user.mfa_enabled = True
                request.user.save()
                return JsonResponse({'status': 'success'})
            return JsonResponse({'status': 'error', 'message': '验证码错误'})
        else:
            secret = pyotp.random_base32()
            request.user.mfa_secret = secret
            request.user.save()
            totp = pyotp.TOTP(secret)
            qr = qrcode.make(totp.provisioning_uri(request.user.username, issuer_name="域名监控系统"))
            buffered = BytesIO()
            qr.save(buffered)
            qr_base64 = base64.b64encode(buffered.getvalue()).decode()
            return JsonResponse({'qr_code': qr_base64})
    return render(request, 'mfa_setup.html')

# 密码修改视图
@login_required
def change_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        user = request.user
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': '无效请求'})

# 退出登录视图
def logout_view(request):
    logout(request)
    return redirect('login')

# 切换监控状态视图
@login_required
def toggle_monitor(request, domain_id, monitor_type):
    domain = Domain.objects.get(id=domain_id)
    if monitor_type == 'domain':
        domain.check_domain = not domain.check_domain
    elif monitor_type == 'cert':
        domain.check_cert = not domain.check_cert
    elif monitor_type == 'https':
        domain.check_https = not domain.check_https
    domain.save()
    return redirect('domain_list')

# 切换启用状态视图
@login_required
def toggle_active(request, domain_id):
    domain = Domain.objects.get(id=domain_id)
    domain.is_active = not domain.is_active
    domain.save()
    return redirect('domain_list')

# 删除域名视图
@login_required
def delete_domain(request, domain_id):
    domain = Domain.objects.get(id=domain_id)
    domain.delete()
    return redirect('domain_list')

# 同步切换所有监控状态视图
@login_required
def toggle_all_monitors(request, domain_id, state):
    domain = Domain.objects.get(id=domain_id)
    if state == 'on':
        domain.check_domain = True
        domain.check_cert = True
        domain.check_https = True
    elif state == 'off':
        domain.check_domain = False
        domain.check_cert = False
        domain.check_https = False
    domain.save()
    return redirect('domain_list')
