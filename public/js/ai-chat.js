/**
 * AI Chat Assistant Widget - مركز تحفيظ القرآن الكريم بأسريجه
 * ملف الجافاسكريبت المستقل لتشغيل المساعد الذكي التفاعلي
 */

(function () {
    'use strict';

    // مفتاح تخزين السجل في المتصفح
    const STORAGE_KEY = 'asrijah_ai_chat_history';
    const MAX_HISTORY = 20;

    let chatHistory = [];
    let isOpen = false;
    let isWaitingForBot = false;
    let suggestionsList = [
        "ما هي المسارات المتاحة بالمنصة؟",
        "كيف أصمم خطة حفظ تناسب وقتي؟",
        "ما هي شروط التقدم للإجازة القرآنية؟",
        "كيف أشترك وأدفع الرسوم؟"
    ];

    // ضمان تضمين ملف CSS تلقائياً إن لم يكن موجوداً
    function ensureStylesLoaded() {
        const href = '/css/ai-chat.css';
        if (!document.querySelector(`link[href="${href}"]`)) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = href;
            document.head.appendChild(link);
        }
    }

    // بناء الواجهة البرمجية للزر ونافذة المحادثة
    function initChatWidget() {
        if (document.getElementById('aiChatWidgetRoot')) return;

        // تفعيل المساعد الذكي فقط وحصرياً في الصفحة الرئيسية (home.html)
        const path = window.location.pathname.toLowerCase();
        const isHomePage = path.includes('home.html') || path.endsWith('/home');
        if (!isHomePage) return;

        ensureStylesLoaded();

        const root = document.createElement('div');
        root.id = 'aiChatWidgetRoot';
        root.innerHTML = `
            <!-- زر فتح الشات العائم كالصورة المرفقة -->
            <button class="ai-chat-launcher" id="aiChatLauncher" title="المساعد الذكي للمنصة" aria-label="فتح المساعد الذكي">
                <span class="ai-chat-launcher-icon">
                    <i class="fa-regular fa-comment-dots"></i>
                </span>
                <span class="ai-chat-launcher-close">
                    <i class="fa-solid fa-xmark"></i>
                </span>
                <span class="ai-launcher-badge" id="aiLauncherBadge"></span>
                <div class="ai-launcher-tooltip">تحدث مع مرشد المنصة الذكي 🌸</div>
            </button>

            <!-- نافذة المحادثة -->
            <div class="ai-chat-box" id="aiChatBox" role="dialog" aria-label="نافذة مرشد المنصة الذكي">
                <!-- الشريط العلوي -->
                <div class="ai-chat-header">
                    <div class="ai-header-info">
                        <div class="ai-avatar-wrapper">
                            <i class="fa-solid fa-wand-magic-sparkles"></i>
                            <span class="ai-status-indicator" title="متصل الآن"></span>
                        </div>
                        <div class="ai-header-text">
                            <h3>مرشد المنصة الذكي</h3>
                            <p>مركز تحفيظ القرآن الكريم بأسريجه</p>
                        </div>
                    </div>
                    <div class="ai-header-actions">
                        <button class="ai-btn-header" id="aiBtnReset" title="بدء محادثة جديدة" aria-label="إعادة ضبط المحادثة">
                            <i class="fa-solid fa-rotate-right"></i>
                        </button>
                        <button class="ai-btn-header" id="aiBtnClose" title="إغلاق" aria-label="إغلاق النافذة">
                            <i class="fa-solid fa-chevron-down"></i>
                        </button>
                    </div>
                </div>

                <!-- شريط الرسائل -->
                <div class="ai-chat-messages" id="aiChatMessages">
                    <!-- مؤشر جاري الكتابة -->
                    <div class="ai-typing-indicator" id="aiTypingIndicator">
                        <span class="ai-typing-dot"></span>
                        <span class="ai-typing-dot"></span>
                        <span class="ai-typing-dot"></span>
                    </div>
                </div>

                <!-- شريط الأسئلة المقترحة السريعة -->
                <div class="ai-suggestions-container" id="aiSuggestionsContainer"></div>

                <!-- حقل الإدخال والإرسال -->
                <div class="ai-chat-input-area">
                    <div class="ai-chat-input-wrapper">
                        <input type="text" class="ai-chat-input" id="aiChatInput" placeholder="اسأل أي سؤال عن المنصة والمسارات..." autocomplete="off">
                    </div>
                    <button class="ai-btn-send" id="aiBtnSend" title="إرسال" aria-label="إرسال الرسالة">
                        <i class="fa-solid fa-paper-plane"></i>
                    </button>
                </div>

                <!-- تذييل -->
                <div class="ai-chat-footer">
                    <span>مدعوم بالذكاء الاصطناعي لخدمة طلاب القرآن الكريم</span>
                </div>
            </div>
        `;

        document.body.appendChild(root);

        // ربط الأحداث
        bindEvents();

        // استرجاع السجل أو عرض رسالة الترحيب
        loadChatHistory();

        // جلب المقترحات الأولية من السيرفر
        fetchSuggestionsFromServer();
    }

    // ربط مستمعات الأحداث
    function bindEvents() {
        const launcher = document.getElementById('aiChatLauncher');
        const closeBtn = document.getElementById('aiBtnClose');
        const resetBtn = document.getElementById('aiBtnReset');
        const sendBtn = document.getElementById('aiBtnSend');
        const input = document.getElementById('aiChatInput');

        launcher.addEventListener('click', toggleChat);
        closeBtn.addEventListener('click', closeChat);
        resetBtn.addEventListener('click', resetConversation);

        sendBtn.addEventListener('click', handleSendMessage);
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSendMessage();
            }
        });
    }

    // فتح وإغلاق النافذة
    function toggleChat() {
        if (isOpen) {
            closeChat();
        } else {
            openChat();
        }
    }

    function openChat() {
        isOpen = true;
        const box = document.getElementById('aiChatBox');
        const launcher = document.getElementById('aiChatLauncher');
        const badge = document.getElementById('aiLauncherBadge');
        const input = document.getElementById('aiChatInput');

        box.classList.add('is-open');
        launcher.classList.add('is-active');
        if (badge) badge.style.display = 'none';

        scrollToBottom();
        setTimeout(() => input && input.focus(), 300);
    }

    function closeChat() {
        isOpen = false;
        const box = document.getElementById('aiChatBox');
        const launcher = document.getElementById('aiChatLauncher');
        box.classList.remove('is-open');
        launcher.classList.remove('is-active');
    }

    // تنسيق الوقت (س:د ص/م)
    function formatTime(dateObj = new Date()) {
        const hours = dateObj.getHours();
        const minutes = dateObj.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'م' : 'ص';
        const formattedHours = hours % 12 || 12;
        return `${formattedHours}:${minutes} ${ampm}`;
    }

    // تحويل نصوص الماركداون المبسطة إلى HTML آمن
    function formatMarkdown(text) {
        if (!text) return '';
        let escaped = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // الروابط: [نص](مسار)
        escaped = escaped.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

        // الروابط المباشرة بين أقواس مثل: (`/courses.html`)
        escaped = escaped.replace(/`(\/[a-zA-Z0-9\-_.]+\.html)`/g, '<a href="$1">$1</a>');

        // الخط العريض: **نص**
        escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // أسطر وتنسيقات
        escaped = escaped.replace(/\n/g, '<br>');

        return escaped;
    }

    // إضافة رسالة في واجهة المستخدم
    function appendMessage(role, content, time = formatTime()) {
        const messagesContainer = document.getElementById('aiChatMessages');
        const typingIndicator = document.getElementById('aiTypingIndicator');

        const msgDiv = document.createElement('div');
        msgDiv.className = `ai-message ${role === 'user' ? 'user' : 'bot'}`;

        msgDiv.innerHTML = `
            <div class="ai-message-bubble">
                ${formatMarkdown(content)}
            </div>
            <span class="ai-message-time">${time}</span>
        `;

        messagesContainer.insertBefore(msgDiv, typingIndicator);
        scrollToBottom();
    }

    // التمرير لأسفل المحادثة
    function scrollToBottom() {
        const messagesContainer = document.getElementById('aiChatMessages');
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    // إظهار وإخفاء مؤشر الكتابة
    function setTyping(active) {
        isWaitingForBot = active;
        const typingIndicator = document.getElementById('aiTypingIndicator');
        const sendBtn = document.getElementById('aiBtnSend');
        const input = document.getElementById('aiChatInput');

        if (active) {
            typingIndicator.classList.add('active');
            sendBtn.disabled = true;
            scrollToBottom();
        } else {
            typingIndicator.classList.remove('active');
            sendBtn.disabled = false;
            if (input) input.focus();
        }
    }

    // عرض الأسئلة المقترحة السريعة
    function renderSuggestions(suggestions) {
        const container = document.getElementById('aiSuggestionsContainer');
        if (!container) return;

        if (!suggestions || suggestions.length === 0) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'flex';
        container.innerHTML = '';

        suggestions.forEach(text => {
            const chip = document.createElement('button');
            chip.type = 'button';
            chip.className = 'ai-suggestion-chip';
            chip.textContent = text;
            chip.addEventListener('click', () => {
                if (isWaitingForBot) return;
                sendMessage(text);
            });
            container.appendChild(chip);
        });
    }

    // جلب الترحيب والمقترحات من السيرفر
    async function fetchSuggestionsFromServer() {
        try {
            const token = localStorage.getItem('token');
            const headers = {};
            if (token) headers['Authorization'] = 'Bearer ' + token;

            const res = await fetch('/api/ai-chat/suggestions', { headers });
            if (res.ok) {
                const data = await res.json();
                if (data.suggestions && data.suggestions.length > 0) {
                    suggestionsList = data.suggestions;
                    renderSuggestions(suggestionsList);
                }
                if (chatHistory.length === 0 && data.welcomeMessage) {
                    appendMessage('bot', data.welcomeMessage);
                    saveMessageToHistory('assistant', data.welcomeMessage);
                }
            }
        } catch (e) {
            // استخدام المقترحات الافتراضية
            renderSuggestions(suggestionsList);
            if (chatHistory.length === 0) {
                const defaultWelcome = "السلام عليكم ورحمة الله وبركاته 🌸\nأهلاً بك في مركز تحفيظ القرآن الكريم بأسريجه! أنا مرشدك الذكي، كيف يمكنني مساعدتك في مسارات الحفظ والتجويد اليوم؟";
                appendMessage('bot', defaultWelcome);
                saveMessageToHistory('assistant', defaultWelcome);
            }
        }
    }

    // إرسال رسالة المستخدم
    function handleSendMessage() {
        const input = document.getElementById('aiChatInput');
        if (!input) return;
        const text = input.value.trim();
        if (!text || isWaitingForBot) return;

        input.value = '';
        sendMessage(text);
    }

    async function sendMessage(text) {
        appendMessage('user', text);
        saveMessageToHistory('user', text);

        setTyping(true);

        try {
            const token = localStorage.getItem('token');
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = 'Bearer ' + token;

            // إرسال آخر رسائل كتاريخ للمحادثة
            const historyPayload = chatHistory.slice(-6).map(m => ({
                role: m.role,
                content: m.content
            }));

            const response = await fetch('/api/ai-chat/send', {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({
                    message: text,
                    history: historyPayload
                })
            });

            if (!response.ok) {
                throw new Error('فشل استلام الرد من المساعد الذكي');
            }

            const data = await response.json();
            const reply = data.reply || "عذراً، لم أستطع معالجة السؤال حالياً. يمكنك تكرار السؤال أو التواصل مع الدعم.";

            appendMessage('bot', reply);
            saveMessageToHistory('assistant', reply);

            if (data.suggestions && data.suggestions.length > 0) {
                renderSuggestions(data.suggestions);
            }
        } catch (error) {
            console.error('AI Chat Error:', error);
            const fallbackMsg = "عذراً، حدث خطأ في الاتصال بالخادم. يرجى التأكد من اتصال الإنترنت أو المحاولة بعد قليل.";
            appendMessage('bot', fallbackMsg);
        } finally {
            setTyping(false);
        }
    }

    // حفظ المحادثة في الذاكرة
    function saveMessageToHistory(role, content) {
        chatHistory.push({
            role: role,
            content: content,
            time: formatTime()
        });

        if (chatHistory.length > MAX_HISTORY) {
            chatHistory = chatHistory.slice(-MAX_HISTORY);
        }

        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(chatHistory));
        } catch (e) {}
    }

    // استرجاع المحادثة المحفوظة
    function loadChatHistory() {
        try {
            const raw = sessionStorage.getItem(STORAGE_KEY);
            if (raw) {
                chatHistory = JSON.parse(raw);
                chatHistory.forEach(item => {
                    appendMessage(item.role === 'user' ? 'user' : 'bot', item.content, item.time);
                });
                renderSuggestions(suggestionsList);
            }
        } catch (e) {
            chatHistory = [];
        }
    }

    // إعادة ضبط المحادثة
    function resetConversation() {
        if (!confirm('هل تريد بدء محادثة جديدة وحذف الرسائل الحالية؟')) return;

        chatHistory = [];
        try {
            sessionStorage.removeItem(STORAGE_KEY);
        } catch (e) {}

        const messagesContainer = document.getElementById('aiChatMessages');
        const typingIndicator = document.getElementById('aiTypingIndicator');
        if (messagesContainer) {
            messagesContainer.innerHTML = '';
            messagesContainer.appendChild(typingIndicator);
        }

        fetchSuggestionsFromServer();
    }

    // تشغيل عند اكتمال تحميل الصفحة
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChatWidget);
    } else {
        initChatWidget();
    }
})();
