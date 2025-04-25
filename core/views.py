from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.core.paginator import Paginator
from .models import Domain
from .utils import get_domain_stats, format_interval
from datetime import datetime, timedelta
from .utils import check_domain_status

@login_required 
def dashboard(request):
    domains = Domain.objects.filter(user=request.user)
    stats = {
        'total_domains': domains.count(),
        'active_domains': domains.filter(is_active=True).count(), # 改用 is_active 字段
        'expiring_soon': domains.filter(is_active=True).count(),  # 同样使用 is_active
        'alerts': 0  # 占位符
    }
    return render(request, 'dashboard.html', {'stats': stats})

@login_required
def domain_list(request):
    name = request.GET.get('name', '')
    domain_name = request.GET.get('domain_name', '')
    group = request.GET.get('group', '')
    per_page = int(request.GET.get('per_page', 20))

    domains = Domain.objects.filter(user=request.user)
    if name:
        domains = domains.filter(task_name__icontains=name)
    if domain_name:
        domains = domains.filter(domain_name__icontains=domain_name)
    if group:
        domains = domains.filter(group=group)

    paginator = Paginator(domains, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    domain_data = []
    for domain in page_obj:
        stats = get_domain_stats(domain)
        domain_data.append({
            'domain': domain,
            'formatted_interval': format_interval(domain.check_interval),
            'availability': stats['availability'],
            'last_check_time': stats['last_check_time'],
            'last_response_time': stats['last_response_time'],
        })

    groups = Domain.objects.filter(user=request.user).values_list('group', flat=True).distinct()

    return render(request, 'domain_list.html', {
        'domain_data': domain_data,
        'name': name,
        'domain_name': domain_name,
        'group': group,
        'groups': groups,
        'page_obj': page_obj,
        'per_page': per_page,
    })

@login_required
def domain_form(request, domain_id=None):
    domain = None
    if domain_id:
        try:
            domain = Domain.objects.get(id=domain_id, user=request.user)
        except Domain.DoesNotExist:
            messages.error(request, '监控对象不存在！')
            return redirect('domain_list')

    if request.method == 'POST':
        try:
            # 获取基本数据
            task_name = request.POST.get('task_name', '').strip()
            domain_input = request.POST.get('domain_name', '').strip()
            domain_names = [name.strip() for name in domain_input.split('\n') if name.strip()]
            check_interval = int(request.POST.get('check_interval', 3600))
            group = request.POST.get('group', '默认组').strip()

            # 验证数据
            if not task_name:
                raise ValueError('任务名称不能为空！')
            if not domain_names:
                raise ValueError('监控对象不能为空！')
            if check_interval < 300:
                raise ValueError('检测频率不能小于300秒！')

            # 构建保存数据
            data = {
                'task_name': task_name,
                'check_interval': check_interval,
                'group': group,
                'response_time_threshold': int(request.POST.get('response_time_threshold', 1000)),
                'alert_threshold': int(request.POST.get('alert_threshold', 3)),
                'notify_telegram': 'notify_telegram' in request.POST,
                'notify_email': 'notify_email' in request.POST,
                'notify_inbox': 'notify_inbox' in request.POST,
                'long_term_monitor': 'long_term_monitor' in request.POST,
            }

            # 处理结束时间
            if not data['long_term_monitor']:
                end_time = request.POST.get('end_time')
                if end_time:
                    try:
                        data['end_time'] = datetime.strptime(end_time, '%Y-%m-%d').date()
                    except ValueError:
                        raise ValueError('无效的结束时间格式！')

            # 检查域名重复
            if not domain_id and Domain.objects.filter(user=request.user, domain_name__in=domain_names).exists():
                raise ValueError('监控对象已存在！')

            # 保存数据
            if domain:
                # 更新现有记录
                domain.domain_name = domain_names[0]
                for key, value in data.items():
                    setattr(domain, key, value)
                domain.save()
                messages.success(request, '更新成功！')
            else:
                # 创建新记录
                for domain_name in domain_names:
                    # 自动判断监控类型
                    if domain_name.startswith('https://'):
                        monitor_type = 'https'
                        domain_name = domain_name.replace('https://', '')
                    elif domain_name.startswith('http://'):
                        monitor_type = 'http'
                        domain_name = domain_name.replace('http://', '')
                    else:
                        monitor_type = 'https'  # 默认使用 https
                    
                    Domain.objects.create(
                        user=request.user,
                        domain_name=domain_name,
                        monitor_type=monitor_type,
                        request_method='GET',  # 默认使用 GET
                        next_check=timezone.now(),
                        **data
                    )
                messages.success(request, f'成功添加 {len(domain_names)} 个监控对象！')

            return redirect('domain_list')

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'保存失败：{str(e)}')

    # 获取当前用户的所有分组
    groups = Domain.objects.filter(user=request.user).values_list('group', flat=True).distinct()
    return render(request, 'domain_form.html', {
        'domain': domain,
        'groups': groups
    })

@login_required
def toggle_monitor(request, domain_id, monitor_type):
    domain = Domain.objects.get(id=domain_id, user=request.user)
    if monitor_type == 'domain':
        domain.check_domain = not domain.check_domain
    elif monitor_type == 'cert':
        domain.check_cert = not domain.check_cert
    elif monitor_type == 'https':
        domain.check_https = not domain.check_https
    domain.save()
    return redirect('domain_list')

@login_required
def toggle_all_monitors(request, domain_id, action):
    domain = Domain.objects.get(id=domain_id, user=request.user)
    if action == 'on':
        domain.check_domain = True
        domain.check_cert = True
        domain.check_https = True
    else:
        domain.check_domain = False
        domain.check_cert = False
        domain.check_https = False
    domain.save()
    return redirect('domain_list')

@login_required
def delete_domain(request, domain_id):
    domain = Domain.objects.get(id=domain_id, user=request.user)
    domain.delete()
    return redirect('domain_list')

@login_required
def bulk_action(request):
    if request.method == 'POST':
        selected_domains = request.POST.getlist('selected_domains')
        action = request.POST.get('bulk_action')
        domains = Domain.objects.filter(id__in=selected_domains, user=request.user)

        if action == 'enable':
            domains.update(check_domain=True, check_cert=True, check_https=True)
        elif action == 'disable':
            domains.update(check_domain=False, check_cert=False, check_https=False)
        elif action == 'delete':
            domains.delete()

        return redirect('domain_list')
    return redirect('domain_list')

@login_required
def update_domains(request):
    """更新需要检测的域名"""
    try:
        # 获取需要检测的域名
        now = timezone.now()
        domains = Domain.objects.filter(
            models.Q(next_check__isnull=True) |  # 从未检测过
            models.Q(next_check__lte=now)        # 已到检测时间
        )
        
        updated_count = 0
        for domain in domains:
            if check_domain_status(domain, request.user):
                # 更新下次检测时间
                domain.next_check = now + timedelta(seconds=domain.check_interval)
                domain.save()
                updated_count += 1
        
        messages.success(request, f'成功更新 {updated_count} 个域名')
    except Exception as e:
        messages.error(request, f'更新失败：{str(e)}')
    
    return redirect('domain_list')

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, '用户名或密码错误！')
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def alert_config(request):
    return render(request, 'alert_config.html')
