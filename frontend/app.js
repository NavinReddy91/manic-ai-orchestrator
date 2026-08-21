// Manic AI — Frontend Application with Real API Integration

const API_BASE = window.location.origin;
let currentOrgId = null;
let currentTaskId = null;
let eventSource = null;

// Agent mapping for visualization
const AGENT_MAP = {
    ceo: 'chief',
    coding_head: 'engineering',
    marketing_head: 'marketing',
    growth_head: 'growth',
    accounting_head: 'finance',
    sales_head: 'sales',
    operations_head: 'operations'
};

const departments = ["engineering", "marketing", "growth", "finance", "sales", "operations"];
const specialists = ["spec1", "spec2", "spec3", "spec4", "spec5", "spec6"];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadOrganizations();
    loadTasks();
    setupEventListeners();
    activate('chief');
    startAmbientActivity();
});

// Setup event listeners
function setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const view = e.target.dataset.view;
            switchView(view);
        });
    });

    // Task submission
    document.getElementById('prompt').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') runTask();
    });

    // Organization select
    document.getElementById('org-select').addEventListener('change', (e) => {
        currentOrgId = e.target.value;
        loadTasks();
    });
}

// Switch between views
function switchView(viewName) {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    document.querySelectorAll('.view').forEach(view => {
        view.classList.toggle('active', view.id === `${viewName}-view`);
    });

    if (viewName === 'tasks') loadTasks();
}

// Load organizations
async function loadOrganizations() {
    try {
        const response = await fetch(`${API_BASE}/organizations`);
        if (!response.ok) throw new Error('Failed to load organizations');
        
        const orgs = await response.json();
        const select = document.getElementById('org-select');
        
        select.innerHTML = '<option value="">Select Org</option>';
        
        orgs.forEach(org => {
            const option = document.createElement('option');
            option.value = org.id;
            option.textContent = org.name;
            select.appendChild(option);
        });
        
        if (orgs.length > 0) {
            select.value = orgs[0].id;
            currentOrgId = orgs[0].id;
        }
    } catch (error) {
        console.error('Error loading organizations:', error);
        showToast('Failed to load organizations', 'error');
    }
}

// Load tasks
async function loadTasks() {
    try {
        const url = currentOrgId 
            ? `${API_BASE}/tasks?organization_id=${currentOrgId}`
            : `${API_BASE}/tasks`;
            
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load tasks');
        
        const tasks = await response.json();
        renderTaskList(tasks);
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

// Render task list
function renderTaskList(tasks) {
    const container = document.getElementById('task-list');
    
    if (tasks.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No tasks yet</p></div>';
        return;
    }
    
    container.innerHTML = tasks.map(task => `
        <div class="task-item" onclick="showTaskDetail('${task.id}')">
            <div class="task-item-header">
                <span class="task-id">${task.id.substring(0, 8)}...</span>
                <span class="task-status ${task.status}">${task.status}</span>
            </div>
            <div class="task-prompt">${escapeHtml(task.prompt.substring(0, 120))}${task.prompt.length > 120 ? '...' : ''}</div>
            <div class="task-meta">
                <span>Tokens: ${task.tokens_used || 0} / ${task.token_budget || 15000}</span>
                <span>LLM Calls: ${task.llm_call_count || 0}</span>
                <span>Created: ${formatDate(task.created_at)}</span>
            </div>
        </div>
    `).join('');
}

// Run task with real API integration
async function runTask() {
    const prompt = document.getElementById('prompt').value.trim();
    const runBtn = document.getElementById('run-btn');
    
    if (!prompt) {
        showToast('Please enter a task', 'error');
        return;
    }
    
    if (!currentOrgId) {
        showToast('Please select an organization', 'error');
        return;
    }
    
    runBtn.disabled = true;
    runBtn.innerHTML = '<span>⏳</span> RUNNING...';
    
    try {
        const response = await fetch(`${API_BASE}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                organization_id: currentOrgId,
                prompt: prompt,
                token_budget: 15000
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create task');
        }
        
        const task = await response.json();
        currentTaskId = task.id;
        
        showToast(`Task created: ${task.id.substring(0, 8)}...`, 'success');
        
        // Start real-time monitoring
        startTaskMonitoring(task.id);
        
        // Clear form
        document.getElementById('prompt').value = '';
        
    } catch (error) {
        console.error('Error creating task:', error);
        showToast(error.message, 'error');
        runBtn.disabled = false;
        runBtn.innerHTML = '<span>⚡</span> RUN';
    }
}

// Start real-time task monitoring via SSE
function startTaskMonitoring(taskId) {
    if (eventSource) {
        eventSource.close();
    }
    
    document.getElementById('token-bar').style.display = 'block';
    document.getElementById('task-result').style.display = 'none';
    
    eventSource = new EventSource(`${API_BASE}/tasks/${taskId}/stream`);
    
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateTaskProgress(data);
        
        if (data.completed) {
            eventSource.close();
            showTaskResult(data);
            document.getElementById('run-btn').disabled = false;
            document.getElementById('run-btn').innerHTML = '<span>⚡</span> RUN';
            loadTasks();
        }
    };
    
    eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        showToast('Connection lost. Refreshing...', 'error');
        eventSource.close();
        document.getElementById('run-btn').disabled = false;
        document.getElementById('run-btn').innerHTML = '<span>⚡</span> RUN';
        setTimeout(() => loadTasks(), 2000);
    };
}

// Update task progress in real-time
function updateTaskProgress(data) {
    // Update token bar
    const tokenCount = document.getElementById('token-count');
    const tokenFill = document.getElementById('token-fill');
    
    tokenCount.textContent = `${data.tokens_used || 0} / ${data.token_budget || 15000}`;
    const percentage = ((data.tokens_used || 0) / (data.token_budget || 15000)) * 100;
    tokenFill.style.width = `${Math.min(percentage, 100)}%`;
    
    // Update agent statuses
    if (data.agents) {
        data.agents.forEach(agent => {
            const agentId = AGENT_MAP[agent.key] || agent.key;
            const element = document.getElementById(agentId);
            const statusElement = document.getElementById(`${agentId}-status`);
            
            if (element) {
                if (agent.status === 'running') {
                    element.classList.add('active');
                    if (statusElement) {
                        statusElement.textContent = 'RUNNING';
                        statusElement.style.color = 'var(--cyan)';
                    }
                } else if (agent.status === 'done') {
                    element.classList.remove('active');
                    if (statusElement) {
                        statusElement.textContent = '✓ DONE';
                        statusElement.style.color = 'var(--success)';
                    }
                } else if (agent.status === 'failed') {
                    element.classList.remove('active');
                    if (statusElement) {
                        statusElement.textContent = '✗ FAILED';
                        statusElement.style.color = 'var(--error)';
                    }
                }
            }
        });
    }
    
    // Update status text
    const status = document.getElementById('status');
    status.innerHTML = `TASK RUNNING • <strong>TOKENS: ${data.tokens_used || 0}</strong>`;
}

// Show task result
function showTaskResult(data) {
    const resultDiv = document.getElementById('task-result');
    const resultContent = document.getElementById('result-content');
    
    resultDiv.style.display = 'block';
    
    let html = '<div class="result-summary">';
    
    if (data.final_report) {
        try {
            const report = typeof data.final_report === 'string' 
                ? JSON.parse(data.final_report) 
                : data.final_report;
            
            html += `<h4 style="color: var(--cyan); margin-bottom: 10px;">Summary</h4>`;
            html += `<p style="line-height: 1.6;">${escapeHtml(report.summary || 'Task completed')}</p>`;
            
            if (report.pr_url) {
                html += `<p style="margin-top: 15px;"><strong>Pull Request:</strong> <a href="${report.pr_url}" target="_blank" style="color: var(--cyan);">${report.pr_url}</a></p>`;
            }
            
            if (report.files_changed && report.files_changed.length > 0) {
                html += `<p style="margin-top: 10px;"><strong>Files Changed:</strong> ${report.files_changed.join(', ')}</p>`;
            }
        } catch (e) {
            html += `<pre style="white-space: pre-wrap;">${escapeHtml(data.final_report)}</pre>`;
        }
    }
    
    html += '</div>';
    resultContent.innerHTML = html;
    
    document.getElementById('status').innerHTML = `TASK COMPLETE • <strong>RESULT DELIVERED</strong>`;
    
    showToast('Task completed successfully!', 'success');
}

// Show task detail
async function showTaskDetail(taskId) {
    try {
        const response = await fetch(`${API_BASE}/tasks/${taskId}`);
        if (!response.ok) throw new Error('Failed to load task');
        
        const task = await response.json();
        currentTaskId = taskId;
        
        if (task.status === 'running' || task.status === 'planning') {
            startTaskMonitoring(taskId);
        } else {
            showTaskResult(task);
        }
    } catch (error) {
        console.error('Error loading task:', error);
        showToast('Failed to load task details', 'error');
    }
}

// Close result
function closeResult() {
    document.getElementById('task-result').style.display = 'none';
    document.getElementById('token-bar').style.display = 'none';
    clearAgents();
}

// Agent visualization functions
function clearAgents() {
    document.querySelectorAll('.agent, .specialist').forEach(el => {
        el.classList.remove('active');
        const status = el.querySelector('.agent-status');
        if (status) {
            status.textContent = '';
            status.style.color = '';
        }
    });
}

function activate(id) {
    const element = document.getElementById(id);
    if (element) {
        element.classList.add('active');
    }
}

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<div class="toast-message">${escapeHtml(message)}</div>`;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Ambient activity animation
function startAmbientActivity() {
    setInterval(() => {
        if (currentTaskId && document.getElementById('token-bar').style.display === 'block') {
            return; // Don't run ambient activity during task execution
        }
        
        const randomDept = departments[Math.floor(Math.random() * departments.length)];
        const randomSpec = specialists[Math.floor(Math.random() * specialists.length)];
        
        activate(randomDept);
        activate(randomSpec);
        
        setTimeout(() => {
            document.getElementById(randomDept)?.classList.remove('active');
            document.getElementById(randomSpec)?.classList.remove('active');
        }, 900);
    }, 2200);
}

// Utility functions
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

function escapeHtml(value) {
    if (!value) return '';
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
