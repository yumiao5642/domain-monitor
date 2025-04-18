// 手风琴菜单效果
$(document).ready(function() {
    $('#monitorSubmenu').on('show.bs.collapse', function () {
        $('.collapse').not(this).collapse('hide');
    });

    // 响应式菜单悬停效果
    $('.sidebar').hover(
        function() {
            $(this).addClass('expanded');
        },
        function() {
            $(this).removeClass('expanded');
        }
    );

    // 密码修改表单验证
    $('#passwordChangeForm').submit(function(e) {
        e.preventDefault();
        const newPassword = $('#new_password').val();
        const confirmPassword = $('#confirm_password').val();
        if (newPassword !== confirmPassword) {
            alert('两次输入的密码不一致！');
            return;
        }
        // 提交密码修改请求
        $.post('/change-password/', { new_password: newPassword }, function(data) {
            if (data.status === 'success') {
                alert('密码修改成功！');
                $('#passwordChangeModal').modal('hide');
            } else {
                alert(data.message || '密码修改失败！');
            }
        });
    });

    // 主题切换
    $('#theme-toggle').click(function() {
        $('body').toggleClass('light-theme');
        const isLightTheme = $('body').hasClass('light-theme');
        localStorage.setItem('theme', isLightTheme ? 'light' : 'dark');
        // 切换图标
        $(this).find('i').toggleClass('fa-sun fa-moon');
    });

    // 初始化主题
    if (localStorage.getItem('theme') === 'light') {
        $('body').addClass('light-theme');
        $('#theme-toggle i').removeClass('fa-sun').addClass('fa-moon');
    } else {
        $('#theme-toggle i').removeClass('fa-moon').addClass('fa-sun');
    }
});
