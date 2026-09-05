// فتح وإغلاق القائمة الجانبية
function toggleSideMenu() {
    const sideMenu = document.getElementById('sideMenu');
    const overlay = document.getElementById('sideMenuOverlay');
    if (sideMenu && overlay) {
        sideMenu.classList.toggle('active');
        overlay.classList.toggle('active');
    }
}

// ---------- الوضع الليلي / النهاري ----------
function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.querySelectorAll('.theme-icon').forEach(function (icon) {
        icon.classList.remove('fa-moon', 'fa-sun');
        icon.classList.add(theme === 'dark' ? 'fa-sun' : 'fa-moon');
    });
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem('theme', next);
}

// استرجاع بيانات المستخدم المحفوظة
function loadUserData() {
    const savedName = localStorage.getItem('fullName');
    const savedCode = localStorage.getItem('userCode');
    const savedAvatar = localStorage.getItem('profileImage');

    if (savedName) {
        const userNameEl = document.getElementById('userName');
        if (userNameEl) userNameEl.textContent = savedName;

        const sideName = document.getElementById('sideMenuUserName');
        if (sideName) sideName.textContent = savedName;
    }
    if (savedCode) {
        const userCodeEl = document.getElementById('userCode');
        if (userCodeEl) userCodeEl.textContent = savedCode;
    }
    if (savedAvatar) {
        renderAvatar(savedAvatar);
    }

    // إظهار زر لوحة التحكم والإدارة للأدمن فقط
    let role = localStorage.getItem('role');
    if (!role) {
        try {
            const u = JSON.parse(localStorage.getItem('user'));
            if (u && u.role) role = u.role;
        } catch (e) {}
    }
    const adminLink = document.getElementById('sideAdminLink');
    if (adminLink) {
        adminLink.style.display = (role === 'ADMIN') ? 'block' : 'none';
    }
}

// ---------- صورة الملف الشخصي ----------
function renderAvatar(dataUrl) {
    if (!dataUrl) return;

    // تحديث الصورة داخل القائمة الجانبية
    const sideImg = document.getElementById('sideMenuAvatarImg');
    const sidePlaceholder = document.getElementById('sideMenuAvatarPlaceholder');
    if (sideImg) {
        sideImg.src = dataUrl;
        sideImg.style.display = 'block';
        if (sidePlaceholder) sidePlaceholder.style.display = 'none';
    }

    // تحديث شارة المستخدم في الشريط العلوي
    const navBadge = document.getElementById('navUserInfo');
    if (navBadge) {
        let navImg = document.getElementById('navUserAvatarImg');
        if (!navImg) {
            navImg = document.createElement('img');
            navImg.id = 'navUserAvatarImg';
            navImg.className = 'nav-user-avatar-img';
            navImg.alt = 'صورة المستخدم';
            navImg.style.cssText = 'width: 24px; height: 24px; border-radius: 50%; object-fit: cover; border: 1.5px solid var(--emerald, #10b981); display: inline-block; vertical-align: middle; flex-shrink: 0;';
            const navIcon = navBadge.querySelector('i');
            if (navIcon) {
                navBadge.replaceChild(navImg, navIcon);
            } else {
                navBadge.prepend(navImg);
            }
        }
        navImg.src = dataUrl;
        navImg.style.display = 'inline-block';
        const remainingIcon = navBadge.querySelector('i');
        if (remainingIcon && remainingIcon !== navImg) {
            remainingIcon.style.display = 'none';
        }
    }
}

// جلب صورة وبيانات الملف الشخصي من السيرفر ومزامنتها محلياً
async function loadProfileFromServer() {
    const token = localStorage.getItem('token');
    const userCode = localStorage.getItem('userCode');
    const phone = localStorage.getItem('phone');
    const email = localStorage.getItem('email');

    // 1. محاولة الجلب عبر التوكن المعتمد
    if (token) {
        try {
            const response = await fetch('/api/auth/profile', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (response.ok) {
                const profile = await response.json();
                if (profile) {
                    if (profile.fullName) localStorage.setItem('fullName', profile.fullName);
                    if (profile.userCode) localStorage.setItem('userCode', profile.userCode);
                    if (profile.phone) localStorage.setItem('phone', profile.phone);
                    if (profile.email) localStorage.setItem('email', profile.email);
                    if (profile.profileImage) {
                        localStorage.setItem('profileImage', profile.profileImage);
                        renderAvatar(profile.profileImage);
                    }
                    loadUserData();
                    return;
                }
            }
        } catch (err) {
            console.warn('تعذر جلب الملف الشخصي بالتوكن:', err);
        }
    }

    // 2. بديل فوري في حال عدم توفر التوكن أو انتهاء صلاحيته لضمان بقاء الصورة دائماً
    if (userCode || phone || email) {
        try {
            const q = new URLSearchParams();
            if (userCode) q.append('userCode', userCode);
            if (phone) q.append('phone', phone);
            if (email) q.append('email', email);

            const res = await fetch('/api/auth/public-avatar?' + q.toString());
            if (res.ok) {
                const data = await res.json();
                if (data && data.profileImage) {
                    localStorage.setItem('profileImage', data.profileImage);
                    renderAvatar(data.profileImage);
                }
            }
        } catch (err) {
            console.warn('تعذر جلب صورة المستخدم العامة:', err);
        }
    }
}

// تحميل القائمة الجانبية ديناميكياً من ملف sidebar.html
function loadSidebar() {
    fetch('/sidebar.html')
        .then(response => response.text())
        .then(html => {
            const container = document.getElementById('sidebar-container');
            if (container) {
                container.innerHTML = html;
            }

            // مزامنة البيانات بعد حقن القائمة الجانبية
            loadUserData();
            loadProfileFromServer();
            highlightActiveSidebarLink();
            updateSideNotificationBadge();
            const currentTheme = localStorage.getItem('theme') || 'light';
            applyTheme(currentTheme);
        })
        .catch(err => console.error('خطأ في تحميل القائمة الجانبية. تأكد من فتح الموقع عبر سيرفر محلي وليس بفتح الملف مباشرة:', err));
}

// تحديث مؤشرات الإشعارات (البادج داخل القائمة الجانبية فقط دون إظهار علامة على زر القائمة نفسه)
function applyNotificationIndicators(unreadCount) {
    // 1. تحديث البادج داخل القائمة الجانبية على أيقونة الإشعارات
    const badge = document.getElementById('sideNotifBadge');
    if (badge) {
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
            badge.style.display = 'inline-flex';
        } else {
            badge.style.display = 'none';
        }
    }

    // 2. إزالة أي علامة حمراء على زر القائمة الجانبية الرئيسي لمنع التشويش البصري
    const toggleBtns = document.querySelectorAll('.menu-toggle-btn');
    toggleBtns.forEach(btn => {
        const dot = btn.querySelector('.nav-menu-notif-dot');
        if (dot) {
            dot.remove();
        }
    });
}

// تحديث بادج ونقطة الإشعارات غير المقروءة من السيرفر مباشرة
function updateSideNotificationBadge() {
    const userCode = localStorage.getItem('userCode') || '';
    const email = localStorage.getItem('email') || '';
    const token = localStorage.getItem('token') || '';

    if (!userCode && !email && !token) {
        applyNotificationIndicators(0);
        return;
    }

    const headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;

    fetch(`/api/notifications/unread-count?userCode=${encodeURIComponent(userCode)}&email=${encodeURIComponent(email)}`, {
        headers: headers
    })
    .then(res => res.ok ? res.json() : null)
    .then(data => {
        if (data && typeof data.unread === 'number') {
            applyNotificationIndicators(data.unread);
        } else {
            try {
                const raw = localStorage.getItem('user_notifications');
                if (raw) {
                    const list = JSON.parse(raw);
                    const unread = list.filter(n => !n.read && !n.isRead).length;
                    applyNotificationIndicators(unread);
                }
            } catch (e) {}
        }
    })
    .catch(() => {
        try {
            const raw = localStorage.getItem('user_notifications');
            if (raw) {
                const list = JSON.parse(raw);
                const unread = list.filter(n => !n.read && !n.isRead).length;
                applyNotificationIndicators(unread);
            }
        } catch (e) {}
    });
}

// فحص دوري للإشعارات كل 20 ثانية لتحديث العلامة الحمراء فور وصول إشعار جديد
if (!window._notifIntervalStarted) {
    window._notifIntervalStarted = true;
    setInterval(updateSideNotificationBadge, 20000);
}

// تشغيل الفحص فور تحميل الصفحة مباشرة
document.addEventListener('DOMContentLoaded', function() {
    updateSideNotificationBadge();
});

// تحديد الرابط النشط في القائمة الجانبية حسب الصفحة المفتوحة حالياً
function highlightActiveSidebarLink() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.side-nav-links a').forEach(function (link) {
        const linkPath = link.getAttribute('href');
        if (linkPath && linkPath === currentPath) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

function logout() {
    localStorage.clear();
    window.location.href = '/index.html';
}

function openContactModal(event) {
    if (event) event.preventDefault();
    const overlay = document.getElementById('contactModalOverlay');
    if (!overlay) return;
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeContactModal() {
    const overlay = document.getElementById('contactModalOverlay');
    if (!overlay) return;
    overlay.classList.remove('active');
    document.body.style.overflow = '';
}

function copyContactValue(text, button) {
    const feedback = document.getElementById('contactCopyFeedback');
    const icon = button ? button.querySelector('i') : null;

    function showCopied() {
        if (icon) icon.className = 'fa-solid fa-check';
        if (feedback) {
            feedback.hidden = false;
            feedback.textContent = 'تم النسخ';
        }
        setTimeout(function () {
            if (icon) icon.className = 'fa-regular fa-copy';
            if (feedback) feedback.hidden = true;
        }, 1600);
    }

    function fallbackCopy() {
        const input = document.createElement('textarea');
        input.value = text;
        input.setAttribute('readonly', '');
        input.style.position = 'absolute';
        input.style.left = '-9999px';
        document.body.appendChild(input);
        input.select();
        try {
            document.execCommand('copy');
            showCopied();
        } finally {
            document.body.removeChild(input);
        }
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(showCopied).catch(fallbackCopy);
    } else {
        fallbackCopy();
    }
}

function initContactModal() {
    const overlay = document.getElementById('contactModalOverlay');
    const openLink = document.getElementById('openContactModal');
    const closeBtn = document.getElementById('closeContactModal');
    if (!overlay) return;

    if (openLink) {
        openLink.addEventListener('click', openContactModal);
    }
    if (closeBtn) {
        closeBtn.addEventListener('click', closeContactModal);
    }
    overlay.addEventListener('click', function (event) {
        if (event.target === overlay) closeContactModal();
    });
    overlay.querySelectorAll('.contact-copy-btn').forEach(function (button) {
        button.addEventListener('click', function () {
            copyContactValue(button.getAttribute('data-copy'), button);
        });
    });
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && overlay.classList.contains('active')) {
            closeContactModal();
        }
    });
}

// ---------- لوحة الصدارة ----------
function loadLeaderboardData() {
    fetch('/api/leaderboard/weekly')
        .then(response => response.json())
        .then(data => {
            updateLeaderboardUI(data);
        })
        .catch(err => {
            console.error('خطأ في تحميل بيانات لوحة الصدارة:', err);
            showLeaderboardError();
        });
}

function showLeaderboardError() {
    // إخفاء التحميل وإظهار رسالة خطأ
    const loadingPodium = document.getElementById('loading-podium');
    const actualPodium = document.getElementById('actual-podium');
    const loadingRank = document.getElementById('loading-rank');
    
    if (loadingPodium) loadingPodium.style.display = 'none';
    if (actualPodium) actualPodium.style.display = 'none';
    if (loadingRank) {
        loadingRank.innerHTML = '<p>حدث خطأ في تحميل بيانات الترتيب. يرجى المحاولة مرة أخرى.</p>';
    }
}

function updateLeaderboardUI(data) {
    if (!data || !data.entries || data.entries.length === 0) {
        console.log('لا توجد بيانات للوحة الصدارة');
        showEmptyLeaderboard();
        return;
    }

    const entries = data.entries;
    const totalUsers = data.totalUsers || 0;
    const displayedUsers = data.displayedUsers || 0;
    
    // إخفاء التحميل وإظهار المحتوى الفعلي
    const loadingPodium = document.getElementById('loading-podium');
    const actualPodium = document.getElementById('actual-podium');
    const loadingRank = document.getElementById('loading-rank');
    
    if (loadingPodium) loadingPodium.style.display = 'none';
    if (actualPodium) actualPodium.style.display = 'flex';
    if (loadingRank) loadingRank.style.display = 'none';
    
    // تحديث منصة التتويج (أول 3)
    updatePodium(entries);
    
    // تحديث باقي الترتيب
    updateRankList(entries, totalUsers, displayedUsers);
}

function showEmptyLeaderboard() {
    const loadingPodium = document.getElementById('loading-podium');
    const actualPodium = document.getElementById('actual-podium');
    const loadingRank = document.getElementById('loading-rank');
    
    if (loadingPodium) loadingPodium.style.display = 'none';
    if (actualPodium) actualPodium.style.display = 'none';
    if (loadingRank) {
        loadingRank.innerHTML = '<p>لا توجد بيانات ترتيب متاحة حالياً. ستبدأ البيانات بالظهور عندما يسجل الطلاب تقدمهم.</p>';
    }
}

function updatePodium(entries) {
    const podiumContainer = document.getElementById('actual-podium');
    if (!podiumContainer) return;

    const podiumCards = podiumContainer.querySelectorAll('.podium-card');
    
    // إعادة تعيين جميع البطاقات
    podiumCards.forEach(card => {
        const rankBadge = card.querySelector('.podium-rank-badge');
        const avatar = card.querySelector('.podium-avatar');
        const name = card.querySelector('.podium-name');
        const path = card.querySelector('.podium-path');
        const points = card.querySelector('.podium-points');
        
        if (rankBadge) rankBadge.textContent = '--';
        if (avatar) avatar.src = '/images/brand/default-avatar.png';
        if (name) name.textContent = '--';
        if (path) path.textContent = '--';
        if (points) points.innerHTML = '0 <span>نقطة</span>';
    });

    // التعامل مع عدد المستخدمين المختلف
    if (entries.length >= 1) {
        // المركز الأول (الوسط - البطاقة الثانية)
        updatePodiumCard(podiumCards[1], entries[0], 1);
    }
    
    if (entries.length >= 2) {
        // المركز الثاني (اليمين - البطاقة الثالثة)
        updatePodiumCard(podiumCards[2], entries[1], 2);
    }
    
    if (entries.length >= 3) {
        // المركز الثالث (اليسار - البطاقة الأولى)
        updatePodiumCard(podiumCards[0], entries[2], 3);
    }
}

function updatePodiumCard(card, entry, expectedRank) {
    if (!card || !entry) return;
    
    const rankBadge = card.querySelector('.podium-rank-badge');
    const avatar = card.querySelector('.podium-avatar');
    const name = card.querySelector('.podium-name');
    const path = card.querySelector('.podium-path');
    const points = card.querySelector('.podium-points');

    if (rankBadge) rankBadge.textContent = entry.rank;
    if (avatar) avatar.src = entry.profileImage || '/images/brand/default-avatar.png';
    if (name) name.textContent = entry.fullName;
    if (path) path.textContent = entry.currentSurah || 'مسار الحفظ';
    if (points) points.innerHTML = `${entry.points} <span>نقطة</span>`;
}

function escapeHtmlText(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function updateRankList(entries, totalUsers, displayedUsers) {
    const rankList = document.getElementById('rank-list');
    if (!rankList) return;

    // إضافة العناصر الديناميكية
    const remainingEntries = entries.slice(3);
    
    // إزالة العناصر الديناميكية القديمة
    const dynamicItems = rankList.querySelectorAll('.rank-list-item.dynamic');
    dynamicItems.forEach(item => item.remove());

    if (remainingEntries.length === 0) {
        const emptyMessage = document.createElement('div');
        emptyMessage.className = 'rank-list-item dynamic';
        emptyMessage.innerHTML = '<p>لا يوجد ترتيب إضافي لهذا الأسبوع</p>';
        rankList.appendChild(emptyMessage);
        return;
    }

    remainingEntries.forEach(entry => {
        const item = document.createElement('div');
        item.className = 'rank-list-item dynamic';
        const safeName = escapeHtmlText(entry.fullName);
        const safeSurah = escapeHtmlText(entry.currentSurah || 'مسار الحفظ');
        const safePoints = escapeHtmlText(entry.points);
        const safeRank = escapeHtmlText(entry.rank);
        const safeImg = entry.profileImage ? entry.profileImage : '/images/brand/default-avatar.png';
        item.innerHTML = `
            <div class="rank-number">${safeRank}</div>
            <img class="rank-avatar" src="${safeImg}" alt="${safeName}">
            <div class="rank-info">
                <h5>${safeName}</h5>
                <p>${safeSurah}</p>
            </div>
            <div class="rank-points">${safePoints} <span>نقطة</span></div>
        `;
        rankList.appendChild(item);
    });
}

// تنفيذ التحميل عند تجهيز الصفحة
document.addEventListener('DOMContentLoaded', function () {
    loadSidebar();

    // استرجاع الثيم والبيانات الأولية للشريط العلوي فوراً
    const savedTheme = localStorage.getItem('theme') || 'light';
    applyTheme(savedTheme);
    loadUserData();
    loadProfileFromServer();
    initContactModal();

    // تحميل بيانات لوحة الصدارة إذا كنا في صفحة أوائل الطلاب
    if (window.location.pathname.includes('top-students.html')) {
        loadLeaderboardData();
    }
});
