"""
Central translation table for the bilingual (fa/en) web panel.
Add new UI strings here as (key -> {"fa": ..., "en": ...}) and reference
them in templates with {{ t('key') }}. Server-side messages generated in
Python (validation errors, etc.) are intentionally kept in English only
(see app/schemas.py) — only the static UI chrome is bilingual for now.
"""

TRANSLATIONS = {
    # --- Common / shell ---
    "brand": {"fa": "مسیریابی مرکزی", "en": "CENTRAL ROUTING"},
    "nav_dashboard": {"fa": "داشبورد", "en": "Dashboard"},
    "nav_nodes": {"fa": "نودها", "en": "Nodes"},
    "nav_connections": {"fa": "اتصالات و مسیریابی", "en": "Connections & Routing"},
    "nav_users": {"fa": "کاربران", "en": "Users"},
    "nav_backup": {"fa": "پشتیبان‌گیری", "en": "Backup"},
    "nav_system": {"fa": "سیستم", "en": "System"},
    "logout": {"fa": "خروج", "en": "Logout"},
    "ssl_warning_banner": {
        "fa": "شما با آدرس IP خام و بدون رمزنگاری (HTTP) وارد شده‌اید. استفاده از یک دامنه با گواهی SSL (HTTPS) امنیت بیشتری فراهم می‌کند — از منوی CLI روی سرور قابل تنظیم است.",
        "en": "You're connected over plain HTTP with a raw IP address. Using a domain with an SSL certificate (HTTPS) is more secure — this can be set up from the server's CLI tool.",
    },

    # --- Login page ---
    "login_eyebrow": {"fa": "پنل مسیریابی مرکزی", "en": "CENTRAL ROUTING PANEL"},
    "login_title": {"fa": "ورود به پنل مدیریت", "en": "Sign in to the admin panel"},
    "login_username": {"fa": "نام کاربری", "en": "Username"},
    "login_password": {"fa": "رمز عبور", "en": "Password"},
    "login_submit": {"fa": "ورود", "en": "Sign in"},
    "login_error": {"fa": "نام کاربری یا رمز عبور اشتباه است.", "en": "Incorrect username or password."},

    # --- Dashboard ---
    "dashboard_title": {"fa": "داشبورد", "en": "Dashboard"},
    "dev_mode_banner": {
        "fa": "حالت DEV فعال است — وضعیت پینگ نودها واقعی نیست و قوانین فایروال/کانفیگ‌ها روی دیسک اعمال نمی‌شوند (dry-run).",
        "en": "DEV mode is active — node ping status isn't real and firewall/config changes aren't written to disk (dry-run).",
    },
    "node_status_title": {"fa": "وضعیت نودها", "en": "Node Status"},
    "active_routes_title": {"fa": "مسیرهای فعال", "en": "Active Routes"},
    "col_label": {"fa": "لیبل", "en": "Label"},
    "col_tunnel_ip": {"fa": "Tunnel IP", "en": "Tunnel IP"},
    "col_subnet": {"fa": "Subnet", "en": "Subnet"},
    "col_status": {"fa": "وضعیت", "en": "Status"},
    "col_actions": {"fa": "عملیات", "en": "Actions"},
    "status_online": {"fa": "آنلاین", "en": "Online"},
    "status_offline": {"fa": "آفلاین", "en": "Offline"},
    "no_nodes": {"fa": "نودی ثبت نشده.", "en": "No nodes registered yet."},
    "no_routes": {"fa": "هنوز مسیری تعریف نشده.", "en": "No routes defined yet."},

    # --- Nodes ---
    "nodes_title": {"fa": "نودها", "en": "Nodes"},
    "nodes_count": {"fa": "نود ثبت‌شده", "en": "registered node(s)"},
    "add_node": {"fa": "+ افزودن نود جدید", "en": "+ Add new node"},
    "rotate_secrets": {"fa": "چرخش PSK/رمز", "en": "Rotate PSK/password"},
    "delete": {"fa": "حذف", "en": "Delete"},
    "confirm_delete_node": {
        "fa": "حذف نود «{label}» و تمام اتصالات وابسته؟",
        "en": "Delete node \"{label}\" and all its connections?",
    },
    "no_nodes_yet": {"fa": "هنوز نودی ثبت نشده.", "en": "No nodes registered yet."},
    "credentials_reveal_title": {"fa": "⚠ فقط یک بار نمایش داده می‌شود", "en": "⚠ Shown only once"},
    "credentials_reveal_body": {
        "fa": "اطلاعات ورود نود «{label}» ساخته شد. همین حالا این‌ها را جایی امن کپی کنید — دیگر از پنل قابل بازیابی نیستند:",
        "en": "Credentials for node \"{label}\" were generated. Copy them somewhere safe right now — they can't be retrieved from the panel again:",
    },
    "new_node_title": {"fa": "افزودن نود جدید", "en": "Add new node"},
    "node_label_hint": {"fa": "لیبل نود (مثال: Isfahan)", "en": "Node label (e.g. Isfahan)"},
    "node_label_placeholder": {"fa": "فقط حروف انگلیسی/عدد/خط‌تیره", "en": "letters, numbers, dashes only"},
    "node_tunnel_hint": {"fa": "آدرس IP تونل (endpoint داخلی L2TP، مثال: 10.10.10.2)", "en": "Tunnel IP (internal L2TP endpoint, e.g. 10.10.10.2)"},
    "node_subnet_hint": {"fa": "رنج شبکه LAN پشت روتر (مثال: 192.168.10.0/24)", "en": "LAN subnet behind the router (e.g. 192.168.10.0/24)"},
    "create_node_submit": {"fa": "ساخت نود + تولید PSK/رمز PPP", "en": "Create node + generate PSK/PPP secret"},

    # --- Connections ---
    "connections_title": {"fa": "اتصالات و مسیریابی", "en": "Connections & Routing"},
    "connections_count": {"fa": "مسیر تعریف‌شده", "en": "route(s) defined"},
    "add_connection": {"fa": "+ اتصال جدید", "en": "+ New connection"},
    "confirm_delete_connection": {"fa": "حذف این مسیر؟", "en": "Delete this route?"},
    "new_connection_title": {"fa": "اتصال جدید", "en": "New connection"},
    "conn_label_hint": {"fa": "لیبل اتصال (مثال: isf2teh)", "en": "Connection label (e.g. isf2teh)"},
    "source_node": {"fa": "نود مبدأ (Server A)", "en": "Source node (Server A)"},
    "target_node": {"fa": "نود مقصد (Server B)", "en": "Target node (Server B)"},
    "access_mode": {"fa": "نوع دسترسی", "en": "Access mode"},
    "mode_two_way": {"fa": "دوطرفه (Two-Way / Unrestricted)", "en": "Two-Way (unrestricted)"},
    "mode_one_way": {"fa": "یک‌طرفه (One-Way: فقط مبدأ ← مقصد)", "en": "One-Way (source → target only)"},
    "l7_proxy_label": {
        "fa": "علاوه بر مسیریابی subnet-to-subnet، یک پراکسی Nginx اختصاصی هم روی یک پورت برای این مسیر بساز (اختیاری)",
        "en": "Also create a dedicated Nginx proxy on a port for this route, in addition to subnet-to-subnet routing (optional)",
    },
    "create_connection_submit": {"fa": "ساخت اتصال", "en": "Create connection"},
    "subnet_route_label": {"fa": "مسیر subnet", "en": "subnet-route"},

    # --- Server-side dynamic messages (duplicate checks, not-found) ---
    "err_label_taken": {"fa": "لیبل «{value}» قبلاً استفاده شده.", "en": "Label \"{value}\" is already in use."},
    "err_tunnel_ip_taken": {"fa": "آی‌پی تونل «{value}» قبلاً به نود دیگری اختصاص یافته.", "en": "Tunnel IP \"{value}\" is already assigned to another node."},
    "err_subnet_taken": {"fa": "رنج «{value}» قبلاً به نود دیگری اختصاص یافته.", "en": "Subnet \"{value}\" is already assigned to another node."},
    "err_node_not_found": {"fa": "نود یافت نشد.", "en": "Node not found."},
    "err_connection_label_taken": {"fa": "لیبل «{value}» قبلاً استفاده شده.", "en": "Label \"{value}\" is already in use."},
    "err_username_taken": {"fa": "نام کاربری «{value}» قبلاً وجود دارد.", "en": "Username \"{value}\" already exists."},
    "err_user_not_found": {"fa": "کاربر یافت نشد.", "en": "User not found."},
    "err_cannot_delete_self": {"fa": "نمی‌توانید حساب کاربری خودتان را حذف کنید.", "en": "You cannot delete your own account."},
    "err_cannot_delete_last_admin": {"fa": "نمی‌توان آخرین کاربر Admin را حذف کرد.", "en": "You cannot delete the last remaining Admin user."},
    "err_backup_not_found": {"fa": "فایل بک‌آپ یافت نشد.", "en": "Backup file not found."},
    "msg_backup_created": {"fa": "بک‌آپ «{filename}» ساخته شد ({size_kb} کیلوبایت).", "en": "Backup \"{filename}\" created ({size_kb} KB)."},
    "msg_restore_done": {"fa": "بازیابی از «{filename}» انجام شد. برای اعمال کامل، سرویس پنل را ری‌استارت کنید.", "en": "Restored from \"{filename}\". Restart the panel service to fully apply it."},
    "msg_restore_dryrun": {"fa": "در حالت DEV، بازیابی واقعی اجرا نشد (dry-run).", "en": "DEV mode is active - the restore wasn't actually applied (dry-run)."},
    "msg_configs_rebuilt": {"fa": "کانفیگ IPsec/xl2tpd/Nginx و قوانین iptables بازسازی شدند.", "en": "IPsec/xl2tpd/Nginx configs and iptables rules were rebuilt."},

    # --- Users ---
    "users_title": {"fa": "کاربران پنل", "en": "Panel users"},
    "users_count": {"fa": "کاربر", "en": "user(s)"},
    "add_user": {"fa": "+ کاربر جدید", "en": "+ New user"},
    "col_username": {"fa": "نام کاربری", "en": "Username"},
    "col_role": {"fa": "نقش", "en": "Role"},
    "self_marker": {"fa": "(شما)", "en": "(you)"},
    "confirm_delete_user": {"fa": "حذف کاربر «{username}»؟", "en": "Delete user \"{username}\"?"},
    "new_user_title": {"fa": "کاربر جدید", "en": "New user"},
    "password_hint": {"fa": "رمز عبور (حداقل ۸ کاراکتر)", "en": "Password (min. 8 characters)"},
    "role_hint": {"fa": "نقش", "en": "Role"},
    "role_viewer": {"fa": "Viewer (فقط مشاهده)", "en": "Viewer (read-only)"},
    "role_admin": {"fa": "Admin (دسترسی کامل)", "en": "Admin (full access)"},
    "create_user_submit": {"fa": "ساخت کاربر", "en": "Create user"},

    # --- Backup ---
    "backup_title": {"fa": "پشتیبان‌گیری و بازیابی", "en": "Backup & Restore"},
    "auto_backup_title": {"fa": "بک‌آپ خودکار شبانه (کرون‌جاب)", "en": "Nightly automatic backup (cron)"},
    "status_label": {"fa": "وضعیت", "en": "Status"},
    "status_enabled": {"fa": "فعال", "en": "Enabled"},
    "status_disabled": {"fa": "غیرفعال", "en": "Disabled"},
    "disable": {"fa": "غیرفعال‌سازی", "en": "Disable"},
    "enable_nightly": {"fa": "فعال‌سازی (هر شب ساعت ۰۰:۰۰)", "en": "Enable (nightly at 00:00)"},
    "saved_backups_title": {"fa": "بک‌آپ‌های ذخیره‌شده", "en": "Saved backups"},
    "backup_now": {"fa": "+ بک‌آپ دستی همین الان", "en": "+ Manual backup now"},
    "col_filename": {"fa": "نام فایل", "en": "Filename"},
    "col_size": {"fa": "حجم", "en": "Size"},
    "col_date": {"fa": "تاریخ", "en": "Date"},
    "restore": {"fa": "بازیابی", "en": "Restore"},
    "confirm_restore": {
        "fa": "بازیابی از این بک‌آپ، دیتابیس فعلی را جایگزین می‌کند. ادامه می‌دهید؟",
        "en": "Restoring this backup will replace the current database. Continue?",
    },
    "no_backups": {"fa": "هنوز بک‌آپی گرفته نشده.", "en": "No backups yet."},

    # --- System ---
    "system_resources": {"fa": "منابع سیستم", "en": "System Resources"},
    "danger_zone": {"fa": "منطقه‌ی خطر", "en": "Danger Zone"},
    "rotate_secrets_warning": {
        "fa": "چرخش سکرت‌ها بلافاصله این نود را قطع می‌کند تا وقتی اسکریپت نصب جدید را روی آن اجرا کنید.",
        "en": "Rotating secrets will immediately disconnect this node until you run the new setup script on it.",
    },
    "confirm_rotate_secrets": {
        "fa": "مطمئنید می‌خواهید سکرت‌ها را بچرخانید؟ این کار نود را قطع می‌کند.",
        "en": "Are you sure you want to rotate secrets? This will disconnect the node.",
    },
    "system_title": {"fa": "سیستم و پایداری", "en": "System & Persistence"},
    "autostart_title": {"fa": "اجرای خودکار پنل هنگام ری‌استارت سرور", "en": "Auto-start panel on server reboot"},
    "service_status_label": {"fa": "وضعیت سرویس", "en": "Service status"},
    "enable_autostart": {"fa": "فعال‌سازی Auto-Start", "en": "Enable auto-start"},
    "rebuild_title": {"fa": "بازسازی دستی کانفیگ‌ها", "en": "Manually rebuild configs"},
    "rebuild_desc": {
        "fa": "اگر مشکوکی که کانفیگ IPsec/xl2tpd/Nginx یا قوانین iptables با دیتابیس هماهنگ نیست، این دکمه همه‌چیز رو از صفر بازتولید و اعمال می‌کنه.",
        "en": "If you suspect the IPsec/xl2tpd/Nginx configs or iptables rules are out of sync with the database, this rebuilds and re-applies everything from scratch.",
    },
    "rebuild_now": {"fa": "بازسازی الان", "en": "Rebuild now"},
    "service_preview_title": {"fa": "پیش‌نمایش فایل سرویس systemd", "en": "systemd unit file preview"},

    # --- Live Logs ---
    "nav_logs": {"fa": "لاگ زنده", "en": "Live Logs"},
    "logs_title": {"fa": "لاگ زنده", "en": "Live Logs"},
    "logs_pause": {"fa": "توقف", "en": "Pause"},
    "logs_resume": {"fa": "ادامه", "en": "Resume"},
    "logs_clear": {"fa": "پاک‌سازی", "en": "Clear"},
    "logs_all": {"fa": "همه", "en": "All"},

    # --- Settings / DEV mode ---
    "settings_title": {"fa": "تنظیمات", "en": "Settings"},
    "dev_mode_label": {"fa": "حالت توسعه (DEV_MODE)", "en": "Development mode (DEV_MODE)"},
    "dev_mode_on": {"fa": "فعال — عملیات نوشتن روی سیستم dry-run هستند", "en": "Active — system write operations are dry-run"},
    "dev_mode_off": {"fa": "غیرفعال — حالت تولید (production)", "en": "Inactive — production mode"},

    # --- Node form (new fields) ---
    "col_router_ip": {"fa": "آی‌پی روتر", "en": "Router IP"},
    "node_router_ip_label": {"fa": "آی‌پی روتر (پابلیک)", "en": "Router IP (public)"},
    "node_router_ip_hint": {"fa": "آی‌پی اصلی سرور/روتر نود", "en": "Main IP of the node's server/router"},
    "has_subnet_label": {"fa": "رنج آی‌پی (Subnet) هم دارم", "en": "I also have an IP range (Subnet)"},
    "subnet_cidr_label": {"fa": "رنج شبکه (Subnet CIDR)", "en": "Network range (Subnet CIDR)"},
    "subnet_cidr_hint": {"fa": "با وارد کردن رنج، تمام آی‌پی‌های این بازه مجاز به عبور خواهند بود و با فلگ آی‌پی اصلی عبور داده می‌شوند.", "en": "By entering a range, all IPs in this range will be authorized to pass through, flagged with the main IP."},
    "edit_node_title": {"fa": "ویرایش نود", "en": "Edit node"},
    "save_changes": {"fa": "ذخیره تغییرات", "en": "Save changes"},
    "edit": {"fa": "ویرایش", "en": "Edit"},
    "col_log": {"fa": "لاگ", "en": "Log"},
    "view_log": {"fa": "مشاهده لاگ", "en": "View log"},
    "close": {"fa": "بستن", "en": "Close"},
    "auto_refresh_label": {"fa": "آپدیت خودکار:", "en": "Auto-refresh:"},
    "refresh_off": {"fa": "خاموش", "en": "Off"},
    "refresh_5s": {"fa": "هر 5 ثانیه", "en": "Every 5s"},
    "refresh_15s": {"fa": "هر 15 ثانیه", "en": "Every 15s"},
    "refresh_30s": {"fa": "هر 30 ثانیه", "en": "Every 30s"},

    # --- Setup script ---
    "setup_script_title": {"fa": "اسکریپت نصب نود", "en": "Node Setup Script"},
    "setup_script_warning": {"fa": "⚠ این اسکریپت حاوی رمزهای محرمانه نود است. فقط روی سرور نود اجرا کنید.", "en": "⚠ This script contains sensitive node credentials. Only run it on the node server."},
    "setup_step_1": {"fa": "۱. اسکریپت زیر را با دکمه سبز رنگ کپی کنید.", "en": "1. Copy the script using the green button."},
    "setup_step_2": {"fa": "۲. در ترمینال سرور نود وارد شده و فایل را ایجاد کنید: <code>nano setup_l2tp.sh</code>", "en": "2. SSH into the node server and create a file: <code>nano setup_l2tp.sh</code>"},
    "setup_step_3": {"fa": "۳. محتوای اسکریپت را Paste کرده، سپس کلیدهای <code>Ctrl+X</code> و بعد <code>Y</code> و در نهایت <code>Enter</code> را بزنید تا فایل ذخیره شود.", "en": "3. Paste the script, then press <code>Ctrl+X</code>, <code>Y</code>, and <code>Enter</code> to save."},
    "setup_step_4": {"fa": "۴. اسکریپت را با دستور <code>sudo bash setup_l2tp.sh</code> اجرا کنید.", "en": "4. Run the script with: <code>sudo bash setup_l2tp.sh</code>"},
    "copy_script": {"fa": "کپی اسکریپت", "en": "Copy script"},
    "copied": {"fa": "✓ کپی شد!", "en": "✓ Copied!"},
    "get_setup_script": {"fa": "اسکریپت نصب", "en": "Setup script"},
    "back_to_nodes": {"fa": "← بازگشت به نودها", "en": "← Back to nodes"},
    "uninstall_script_title": {"fa": "اسکریپت حذف نود (Uninstall)", "en": "Node Uninstall Script"},
    "uninstall_step_1": {"fa": "۱. اسکریپت زیر را با دکمه قرمز رنگ کپی کنید.", "en": "1. Copy the script using the red button."},
    "uninstall_step_2": {"fa": "۲. در سرور نود فایل را بسازید: <code>nano uninstall_l2tp.sh</code>", "en": "2. On the node server create the file: <code>nano uninstall_l2tp.sh</code>"},
    "uninstall_step_3": {"fa": "۳. محتوا را Paste کرده، با <code>Ctrl+X</code>، <code>Y</code> و <code>Enter</code> ذخیره کنید.", "en": "3. Paste the content, save with <code>Ctrl+X</code>, <code>Y</code>, and <code>Enter</code>."},
    "uninstall_step_4": {"fa": "۴. با دستور <code>sudo bash uninstall_l2tp.sh</code> اجرا کنید.", "en": "4. Run with: <code>sudo bash uninstall_l2tp.sh</code>"},
    "copy_uninstall_script": {"fa": "کپی اسکریپت حذف", "en": "Copy uninstall script"},
}


def translate(key: str, lang: str) -> str:
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    return entry.get(lang, entry.get("en", key))
