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
from datetime import datetime

@login_required
def dashboard(request):
    domains = Domain.objects.filter(user=request.user)
    stats = {
        'total_domains': domains.count(),
        'active_domains': domains.filter(check_domain=True).count(),
        'expiring_soon': domains.filter(check_domain=True).count(),  # Placeholder
        'alerts': 0  # Placeholder
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
        domain = Domain.objects.get(id=domain_id, user=request.user)

    if request.method == 'POST':
        try:
            domain_input = request.POST.get('domain_name')
            domain_names = [name.strip() for name in domain_input.split('\n') if name.strip()] if '\n' in domain_input else [domain_input.strip()]
            task_name = request.POST.get('task_name')
            check_interval = int(request.POST.get('check_interval'))
            check_domain = 'check_domain' in request.POST
            check_cert = 'check_cert' in request.POST
            check_https = 'check_https' in request.POST
            group = request.POST.get('group', '默认组')
            response_time_threshold = int(request.POST.get('response_time_threshold', 1000))
            alert_threshold = int(request.POST.get('alert_threshold', 3))
            notify_telegram = 'notify_telegram' in request.POST
            notify_email = 'notify_email' in request.POST
            notify_inbox = 'notify_inbox' in request.POST
            long_term_monitor = 'long_term_monitor' in request.POST
            end_time = request.POST.get('end_time') or None
            if end_time and end_time.strip() and end_time != '00:00:00':
                try:
                    end_time = datetime.strptime(end_time, '%Y-%m-%d').date()
                except ValueError:
                    end_time = None
            else:
                end_time = None

            # 检查域名是否已存在（仅在添加新域名时检查）
            if not domain_id:
                existing_domains = Domain.objects.filter(user=request.user, domain_name__in=domain_names)
                if existing_domains.exists():
                    messages.error(request, '该监控对象已添加！')
                    groups = Domain.objects.filter(user=request.user).values_list('group', flat=True).distinct()
                    return render(request, 'domain_form.html', {
                        'domain': domain,
                        'groups': groups,
                        'error': '该监控对象已添加！'
                    })

            if domain:
                domain.domain_name = domain_names[0]
                domain.task_name = task_name
                domain.check_interval = check_interval
                domain.check_domain = check_domain
                domain.check_cert = check_cert
                domain.check_https = check_https
                domain.group = group
                domain.response_time_threshold = response_time_threshold
                domain.alert_threshold = alert_threshold
                domain.notify_telegram = notify_telegram
                domain.notify_email = notify_email
                domain.notify_inbox = notify_inbox
                domain.long_term_monitor = long_term_monitor
                domain.end_time = end_time
                domain.save()
            else:
                for domain_name in domain_names:
                    Domain.objects.create(
                        user=request.user,
                        domain_name=domain_name,
                        task_name=task_name,
                        check_interval=check_interval,
                        check_domain=check_domain,
                        check_cert=check_cert,
                        check_https=check_https,
                        group=group,
                        response_time_threshold=response_time_threshold,
                        alert_threshold=alert_threshold,
                        notify_telegram=notify_telegram,
                        notify_email=notify_email,
                        notify_inbox=notify_inbox,
                        long_term_monitor=long_term_monitor,
                        end_time=end_time,
                        next_check=timezone.now()
                    )
            return redirect('domain_list')
        except Exception as e:
            messages.error(request, f'错误：{str(e)}')

    groups = Domain.objects.filter(user=request.user).values_list('group', flat=True).distinct()
    return render(request, 'domain_form.html', {'domain': domain, 'groups': groups})

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
