// ═══════════════════════════════════════════
// AgentOS Frontend — app.js
// ═══════════════════════════════════════════

const API = '';  // same origin

// ── State ──
let currentPage = 'dashboard';
let conversationHistory = [];
let searchTimeout = null;
let isSending = false;

// ══════════ INITIALIZATION ══════════
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initSidebar();
    initChat();
    checkHealth();
    loadDashboard();
    setInterval(checkHealth, 30000);
});

// ══════════ NAVIGATION ══════════
function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            if (page) navigateTo(page);
        });
    });
}

function navigateTo(page) {
    currentPage = page;
    // Update nav active state
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const navItem = document.querySelector(`[data-page="${page}"]`);
    if (navItem) navItem.classList.add('active');

    // Show page
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const pageEl = document.getElementById(`page-${page}`);
    if (pageEl) pageEl.classList.add('active');

    // Update title
    const titles = {
        dashboard: ['Dashboard', 'System overview and statistics'],
        chat: ['AI Chat', 'Orchestrator-powered natural language interface'],
        tasks: ['Tasks', 'Manage your task list'],
        calendar: ['Calendar', 'Schedule and manage events'],
        notes: ['Notes', 'Your knowledge base'],
        agents: ['Agents', 'Multi-agent system architecture'],
        logs: ['Logs', 'Agent execution history']
    };
    const [title, subtitle] = titles[page] || [page, ''];
    document.querySelector('.page-title h1').textContent = title;
    document.querySelector('.page-subtitle').textContent = subtitle;

    // Load data
    const loaders = { dashboard: loadDashboard, tasks: loadTasks, calendar: loadEvents, notes: loadNotes, agents: loadAgents, logs: loadLogs };
    if (loaders[page]) loaders[page]();

    // Close mobile sidebar
    document.getElementById('sidebar').classList.remove('mobile-open');
}

// ══════════ SIDEBAR ══════════
function initSidebar() {
    document.getElementById('sidebarToggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('collapsed');
    });
    document.getElementById('mobileMenuBtn').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('mobile-open');
    });
}

// ══════════ HEALTH CHECK ══════════
async function checkHealth() {
    const ind = document.getElementById('healthIndicator');
    try {
        const res = await fetch(`${API}/health`);
        if (res.ok) {
            ind.className = 'health-indicator online';
            ind.querySelector('span').textContent = 'System Online';
            document.querySelector('.status-dot').className = 'status-dot online';
        } else { throw new Error(); }
    } catch {
        ind.className = 'health-indicator';
        ind.querySelector('span').textContent = 'Offline';
        document.querySelector('.status-dot').className = 'status-dot offline';
    }
}

// ══════════ DASHBOARD ══════════
async function loadDashboard() {
    try {
        const [stats, tasks, events, logs] = await Promise.all([
            fetch(`${API}/api/stats`).then(r => r.json()),
            fetch(`${API}/api/tasks`).then(r => r.json()),
            fetch(`${API}/api/events`).then(r => r.json()),
            fetch(`${API}/api/logs?limit=10`).then(r => r.json())
        ]);

        document.getElementById('statTotalTasks').textContent = stats.total_tasks;
        document.getElementById('statPendingTasks').textContent = `${stats.pending_tasks} pending`;
        document.getElementById('statTotalEvents').textContent = stats.total_events;
        document.getElementById('statTodayEvents').textContent = `${stats.events_today} today`;
        document.getElementById('statTotalNotes').textContent = stats.total_notes;
        document.getElementById('statAgentActions').textContent = stats.total_agent_actions;

        // Recent tasks
        const tasksEl = document.getElementById('dashRecentTasks');
        if (tasks.length === 0) {
            tasksEl.innerHTML = '<div class="empty-state-sm">No tasks yet</div>';
        } else {
            tasksEl.innerHTML = tasks.slice(0, 5).map(t => `
                <div class="dash-task-item">
                    <div class="priority-dot ${t.priority}"></div>
                    <span style="flex:1;color:var(--text-primary)">${escHtml(t.title)}</span>
                    <span class="status-badge ${t.status}">${t.status.replace('_', ' ')}</span>
                </div>
            `).join('');
        }

        // Upcoming events
        const eventsEl = document.getElementById('dashUpcomingEvents');
        if (events.length === 0) {
            eventsEl.innerHTML = '<div class="empty-state-sm">No events scheduled</div>';
        } else {
            eventsEl.innerHTML = events.slice(0, 5).map(e => `
                <div class="dash-event-item">
                    <i class="fas fa-calendar-day" style="color:var(--accent-taupe);font-size:13px"></i>
                    <span style="flex:1;color:var(--text-primary)">${escHtml(e.title)}</span>
                    <span style="font-size:12px;color:var(--text-muted)">${e.date}${e.time ? ' ' + e.time : ''}</span>
                </div>
            `).join('');
        }

        // Recent logs
        const logsEl = document.getElementById('dashRecentLogs');
        if (logs.length === 0) {
            logsEl.innerHTML = '<div class="empty-state-sm">No agent activity yet</div>';
        } else {
            logsEl.innerHTML = logs.slice(0, 6).map(l => `
                <div class="dash-log-item">
                    <div class="log-icon ${l.status}"><i class="fas fa-${l.status === 'success' ? 'check' : 'exclamation'}"></i></div>
                    <span class="log-agent">${escHtml(l.agent)}</span>
                    <span class="log-action">${escHtml(l.action)}</span>
                    <span style="flex:1"></span>
                    <span class="log-time">${timeAgo(l.created_at)}</span>
                </div>
            `).join('');
        }
    } catch (err) { console.error('Dashboard load error:', err); }
}

// ══════════ CHAT ══════════
function initChat() {
    const input = document.getElementById('chatInput');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });
}

function sendSuggestion(text) {
    document.getElementById('chatInput').value = text;
    sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg || isSending) return;

    isSending = true;
    document.getElementById('sendBtn').disabled = true;

    // Remove welcome
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    // Add user bubble
    addChatBubble(msg, 'user');
    input.value = '';
    input.style.height = 'auto';

    // Typing indicator
    const typing = document.createElement('div');
    typing.className = 'typing-indicator';
    typing.innerHTML = '<span></span><span></span><span></span>';
    document.getElementById('chatMessages').appendChild(typing);
    scrollChat();

    try {
        const res = await fetch(`${API}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, conversation_history: conversationHistory })
        });
        const data = await res.json();
        typing.remove();

        if (data.detail) {
            addChatBubble(`Error: ${data.detail}`, 'assistant');
        } else {
            addChatBubble(data.response, 'assistant', data.workflow, data.agents_involved);
            conversationHistory.push({ role: 'user', content: msg });
            conversationHistory.push({ role: 'assistant', content: data.response });
            // Keep history manageable
            if (conversationHistory.length > 20) conversationHistory = conversationHistory.slice(-16);
        }
        // Refresh dashboard data in background
        if (currentPage === 'dashboard') loadDashboard();
    } catch (err) {
        typing.remove();
        addChatBubble('Failed to connect to the server. Make sure the backend is running.', 'assistant');
    }

    isSending = false;
    document.getElementById('sendBtn').disabled = false;
}

function addChatBubble(text, role, workflow, agents) {
    const container = document.getElementById('chatMessages');
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;

    const label = role === 'user' ? 'You' : 'AgentOS';
    let html = `<span class="bubble-label">${label}</span><div>${formatResponse(text)}</div>`;

    if (workflow && workflow.length > 0) {
        html += `<div class="workflow-steps"><h4>Workflow Steps (${workflow.length})</h4>`;
        workflow.forEach(s => {
            html += `<div class="workflow-step">
                <span class="step-icon"><i class="fas fa-check-circle"></i></span>
                <span class="step-agent">${escHtml(s.agent)}</span>
                <span>${escHtml(s.step)}</span>
            </div>`;
        });
        html += '</div>';
    }
    bubble.innerHTML = html;
    container.appendChild(bubble);
    scrollChat();
}

function formatResponse(text) {
    if (!text) return '';
    return escHtml(text).replace(/\n/g, '<br>');
}

function scrollChat() {
    const el = document.getElementById('chatMessages');
    el.scrollTop = el.scrollHeight;
}

// ══════════ TASKS ══════════
async function loadTasks() {
    const status = document.getElementById('taskStatusFilter').value;
    const priority = document.getElementById('taskPriorityFilter').value;
    try {
        const res = await fetch(`${API}/api/tasks?status=${status}&priority=${priority}`);
        const tasks = await res.json();
        const el = document.getElementById('tasksList');
        if (tasks.length === 0) {
            el.innerHTML = '<div class="empty-state"><i class="fas fa-tasks"></i><h3>No tasks found</h3><p>Create your first task or ask the AI!</p></div>';
            return;
        }
        el.innerHTML = tasks.map(t => `
            <div class="list-item" data-id="${t.id}">
                <div class="priority-dot ${t.priority}"></div>
                <div class="list-item-content">
                    <div class="list-item-title">${escHtml(t.title)}</div>
                    <div class="list-item-meta">
                        <span><i class="fas fa-flag"></i> ${t.priority}</span>
                        ${t.due_date ? `<span><i class="fas fa-calendar"></i> ${t.due_date}</span>` : ''}
                        <span><i class="fas fa-clock"></i> ${timeAgo(t.created_at)}</span>
                    </div>
                </div>
                <span class="status-badge ${t.status}">${t.status.replace('_', ' ')}</span>
                <div class="list-item-actions">
                    <button class="btn-ghost" onclick="editTask(${t.id},'${escAttr(t.title)}','${t.priority}','${t.status}','${t.due_date || ''}')"><i class="fas fa-pen"></i></button>
                    <button class="btn-danger" onclick="deleteTask(${t.id})"><i class="fas fa-trash-alt"></i></button>
                </div>
            </div>
        `).join('');
    } catch (err) { showToast('Failed to load tasks', 'error'); }
}

function openTaskModal() {
    document.getElementById('taskEditId').value = '';
    document.getElementById('taskTitle').value = '';
    document.getElementById('taskPriority').value = 'medium';
    document.getElementById('taskStatus').value = 'pending';
    document.getElementById('taskDueDate').value = '';
    document.getElementById('taskModalTitle').innerHTML = '<i class="fas fa-plus-circle"></i> New Task';
    openModal('taskModal');
}

function editTask(id, title, priority, status, dueDate) {
    document.getElementById('taskEditId').value = id;
    document.getElementById('taskTitle').value = title;
    document.getElementById('taskPriority').value = priority;
    document.getElementById('taskStatus').value = status;
    document.getElementById('taskDueDate').value = dueDate;
    document.getElementById('taskModalTitle').innerHTML = '<i class="fas fa-pen"></i> Edit Task';
    openModal('taskModal');
}

async function saveTask() {
    const editId = document.getElementById('taskEditId').value;
    const payload = {
        title: document.getElementById('taskTitle').value.trim(),
        priority: document.getElementById('taskPriority').value,
        status: document.getElementById('taskStatus').value,
        due_date: document.getElementById('taskDueDate').value || null
    };
    if (!payload.title) { showToast('Title is required', 'error'); return; }
    try {
        if (editId) {
            await fetch(`${API}/api/tasks/${editId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            showToast('Task updated!', 'success');
        } else {
            await fetch(`${API}/api/tasks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            showToast('Task created!', 'success');
        }
        closeModal('taskModal');
        loadTasks();
    } catch { showToast('Failed to save task', 'error'); }
}

async function deleteTask(id) {
    if (!confirm('Delete this task?')) return;
    try {
        await fetch(`${API}/api/tasks/${id}`, { method: 'DELETE' });
        showToast('Task deleted', 'success');
        loadTasks();
    } catch { showToast('Failed to delete task', 'error'); }
}

// ══════════ EVENTS ══════════
async function loadEvents() {
    const dateFilter = document.getElementById('eventDateFilter').value;
    const url = dateFilter ? `${API}/api/events?date=${dateFilter}` : `${API}/api/events`;
    try {
        const res = await fetch(url);
        const events = await res.json();
        const el = document.getElementById('eventsList');
        if (events.length === 0) {
            el.innerHTML = '<div class="empty-state"><i class="fas fa-calendar-alt"></i><h3>No events found</h3><p>Schedule your first event!</p></div>';
            return;
        }
        el.innerHTML = events.map(e => `
            <div class="list-item">
                <div class="stat-icon events-icon" style="width:40px;height:40px;font-size:16px"><i class="fas fa-calendar-day"></i></div>
                <div class="list-item-content">
                    <div class="list-item-title">${escHtml(e.title)}</div>
                    <div class="list-item-meta">
                        <span><i class="fas fa-calendar"></i> ${e.date}</span>
                        ${e.time ? `<span><i class="fas fa-clock"></i> ${e.time}</span>` : ''}
                        <span><i class="fas fa-hourglass-half"></i> ${e.duration_minutes}min</span>
                        ${e.attendees ? `<span><i class="fas fa-users"></i> ${escHtml(e.attendees)}</span>` : ''}
                    </div>
                </div>
                <button class="btn-danger" onclick="deleteEvent(${e.id})"><i class="fas fa-trash-alt"></i></button>
            </div>
        `).join('');
    } catch { showToast('Failed to load events', 'error'); }
}

function openEventModal() {
    document.getElementById('eventTitle').value = '';
    document.getElementById('eventDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('eventTime').value = '';
    document.getElementById('eventDuration').value = 60;
    document.getElementById('eventAttendees').value = '';
    document.getElementById('eventNotes').value = '';
    openModal('eventModal');
}

function clearEventFilter() {
    document.getElementById('eventDateFilter').value = '';
    loadEvents();
}

async function saveEvent() {
    const payload = {
        title: document.getElementById('eventTitle').value.trim(),
        date: document.getElementById('eventDate').value,
        time: document.getElementById('eventTime').value || null,
        duration_minutes: parseInt(document.getElementById('eventDuration').value) || 60,
        attendees: document.getElementById('eventAttendees').value || null,
        notes: document.getElementById('eventNotes').value || null
    };
    if (!payload.title || !payload.date) { showToast('Title and date are required', 'error'); return; }
    try {
        await fetch(`${API}/api/events`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        showToast('Event created!', 'success');
        closeModal('eventModal');
        loadEvents();
    } catch { showToast('Failed to save event', 'error'); }
}

async function deleteEvent(id) {
    if (!confirm('Delete this event?')) return;
    try {
        await fetch(`${API}/api/events/${id}`, { method: 'DELETE' });
        showToast('Event deleted', 'success');
        loadEvents();
    } catch { showToast('Failed to delete event', 'error'); }
}

// ══════════ NOTES ══════════
function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(loadNotes, 400);
}

async function loadNotes() {
    const search = document.getElementById('notesSearch').value.trim();
    const url = search ? `${API}/api/notes?search=${encodeURIComponent(search)}` : `${API}/api/notes`;
    try {
        const res = await fetch(url);
        const notes = await res.json();
        const el = document.getElementById('notesList');
        if (notes.length === 0) {
            el.innerHTML = '<div class="empty-state"><i class="fas fa-sticky-note"></i><h3>No notes found</h3><p>Save your first note!</p></div>';
            return;
        }
        el.innerHTML = notes.map(n => `
            <div class="note-card">
                <div class="note-card-title">${escHtml(n.title)}</div>
                ${n.content ? `<div class="note-card-content">${escHtml(n.content)}</div>` : ''}
                ${n.tags ? `<div class="note-card-tags">${n.tags.split(',').map(t => `<span class="tag">${escHtml(t.trim())}</span>`).join('')}</div>` : ''}
                <div class="note-card-footer">
                    <span>${timeAgo(n.created_at)}</span>
                    <button class="btn-danger" onclick="deleteNote(${n.id})"><i class="fas fa-trash-alt"></i></button>
                </div>
            </div>
        `).join('');
    } catch { showToast('Failed to load notes', 'error'); }
}

function openNoteModal() {
    document.getElementById('noteTitle').value = '';
    document.getElementById('noteContent').value = '';
    document.getElementById('noteTags').value = '';
    openModal('noteModal');
}

async function saveNote() {
    const payload = {
        title: document.getElementById('noteTitle').value.trim(),
        content: document.getElementById('noteContent').value || null,
        tags: document.getElementById('noteTags').value || null
    };
    if (!payload.title) { showToast('Title is required', 'error'); return; }
    try {
        await fetch(`${API}/api/notes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        showToast('Note saved!', 'success');
        closeModal('noteModal');
        loadNotes();
    } catch { showToast('Failed to save note', 'error'); }
}

async function deleteNote(id) {
    if (!confirm('Delete this note?')) return;
    try {
        await fetch(`${API}/api/notes/${id}`, { method: 'DELETE' });
        showToast('Note deleted', 'success');
        loadNotes();
    } catch { showToast('Failed to delete note', 'error'); }
}

// ══════════ AGENTS ══════════
async function loadAgents() {
    try {
        const res = await fetch(`${API}/api/agents`);
        const data = await res.json();

        // Network viz
        document.getElementById('agentNetwork').innerHTML = `
            <div class="agent-hub">
                <div class="agent-node orchestrator">
                    <div class="agent-node-icon"><i class="fas fa-brain"></i></div>
                    <div class="agent-node-name">Orchestrator</div>
                    <div class="agent-node-status"><i class="fas fa-circle" style="font-size:6px"></i> Active</div>
                </div>
                <div class="agent-connector"><i class="fas fa-arrows-alt-h"></i></div>
                <div class="agent-node">
                    <div class="agent-node-icon"><i class="fas fa-tasks"></i></div>
                    <div class="agent-node-name">Task Agent</div>
                    <div class="agent-node-status"><i class="fas fa-circle" style="font-size:6px"></i> Active</div>
                </div>
                <div class="agent-node">
                    <div class="agent-node-icon"><i class="fas fa-calendar-alt"></i></div>
                    <div class="agent-node-name">Calendar Agent</div>
                    <div class="agent-node-status"><i class="fas fa-circle" style="font-size:6px"></i> Active</div>
                </div>
                <div class="agent-node">
                    <div class="agent-node-icon"><i class="fas fa-sticky-note"></i></div>
                    <div class="agent-node-name">Notes Agent</div>
                    <div class="agent-node-status"><i class="fas fa-circle" style="font-size:6px"></i> Active</div>
                </div>
            </div>
        `;

        // Agent details
        const icons = { 'Primary Orchestrator': 'brain', 'Task Agent': 'tasks', 'Calendar Agent': 'calendar-alt', 'Notes Agent': 'sticky-note' };
        document.getElementById('agentsList').innerHTML = data.agents.map(a => `
            <div class="agent-detail-card">
                <div class="agent-detail-header">
                    <div class="agent-detail-icon"><i class="fas fa-${icons[a.name] || 'robot'}"></i></div>
                    <div class="agent-detail-name">${escHtml(a.name)}</div>
                </div>
                <div class="agent-detail-role">${escHtml(a.role)}</div>
                <div class="agent-tools">${(a.mcp_tools || a.tools || []).map(t => `<span class="agent-tool">${escHtml(t)}</span>`).join('')}</div>
            </div>
        `).join('');
    } catch { showToast('Failed to load agents', 'error'); }
}

// ══════════ LOGS ══════════
async function loadLogs() {
    try {
        const res = await fetch(`${API}/api/logs?limit=50`);
        const logs = await res.json();
        const el = document.getElementById('logsList');
        if (logs.length === 0) {
            el.innerHTML = '<div class="empty-state"><i class="fas fa-terminal"></i><h3>No logs yet</h3><p>Agent activity will appear here</p></div>';
            return;
        }
        el.innerHTML = logs.map(l => `
            <div class="log-entry">
                <div class="log-icon ${l.status}"><i class="fas fa-${l.status === 'success' ? 'check' : 'exclamation-triangle'}"></i></div>
                <div class="log-content">
                    <span class="log-agent">${escHtml(l.agent)}</span>
                    <span class="log-action">${escHtml(l.action)}</span>
                    ${l.detail ? `<div class="log-detail">${escHtml(l.detail)}</div>` : ''}
                </div>
                <span class="log-time">${timeAgo(l.created_at)}</span>
            </div>
        `).join('');
    } catch { showToast('Failed to load logs', 'error'); }
}

// ══════════ MODALS ══════════
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

// Close on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('open');
    }
});

// ══════════ TOAST ══════════
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i> ${escHtml(message)}`;
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3500);
}

// ══════════ UTILITIES ══════════
function escHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function escAttr(str) {
    return (str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return d.toLocaleDateString();
}
