// Manic AI — Frontend Application

const API_BASE = window.location.origin;
let currentOrgId = null;
let refreshInterval = null;

// Organization chart structure
const ORG_CHART = {
    ceo: { label: "Chief Agent", team: "executive", reports: ["coding_head", "marketing_head", "growth_head", "accounting_head", "sales_head", "operations_head"] },
    coding_head: { label: "Coding Manager", team: "coding", reports: ["frontend_dev", "backend_dev", "bug_checker_frontend", "bug_checker_backend", "integration_checker"] },
    frontend_dev: { label: "Frontend Dev", team: "coding", reports: [] },
    backend_dev: { label: "Backend Dev", team: "coding", reports: [] },
    bug_checker_frontend: { label: "Frontend QA", team: "coding", reports: [] },
    bug_checker_backend: { label: "Backend QA", team: "coding", reports: [] },
    integration_checker: { label: "Integration QA", team: "coding", reports: [] },
    marketing_head: { label: "Marketing Manager", team: "marketing", reports: ["traditional_marketing", "digital_marketing"] },
    traditional_marketing: { label: "Traditional Marketing", team: "marketing", reports: [] },
    digital_marketing: { label: "Digital Marketing", team: "marketing", reports: [] },
    growth_head: { label: "Growth Manager", team: "growth", reports: ["market_researcher", "business_analyst"] },
    market_researcher: { label: "Market Researcher", team: "growth", reports: [] },
    business_analyst: { label: "Business Analyst", team: "growth", reports: [] },
    accounting_head: { label: "Accounting Manager", team: "accounting", reports: ["bookkeeper"] },
    bookkeeper: { label: "Bookkeeper", team: "accounting", reports: [] },
    sales_head: { label: "Sales Manager", team: "sales", reports: ["sales_rep"] },
    sales_rep: { label: "Sales Rep", team: "sales", reports: [] },
    operations_head: { label: "Operations Manager", team: "operations", reports: ["ops_coordinator"] },
    ops_coordinator: { label: "Ops Coordinator", team: "operations", reports: [] }
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderOrgChart();
    loadOrganizations();
    loadTasks();
    
    // Auto-refresh tasks every 5 seconds
    refreshInterval = setInterval(loadTasks, 5000);
    
    // Event listeners
    document.getElementById('deploy-task').addEventListener('click', deployTask);
    document.getElementById('org-select').addEventListener('change', (e) => {
        currentOrgId = e.target.value;
        loadTasks();
    });

    // Organization Modal handlers
    document.getElementById('open-create-org-btn').addEventListener('click', openCreateOrgModal);
    document.getElementById('close-create-org-modal').addEventListener('click', closeCreateOrgModal);
    document.getElementById('cancel-create-org-btn').addEventListener('click', closeCreateOrgModal);
    document.getElementById('confirm-create-org-btn').addEventListener('click', createOrganization);
    
    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeCreateOrgModal();
    });
});

// Render organization chart
function renderOrgChart() {
    const container = document.getElementById('org-chart');
    container.innerHTML = '';
    
    // Render CEO first
    const ceoNode = createAgentNode('ceo', ORG_CHART.ceo);
    ceoNode.classList.add('ceo');
    container.appendChild(ceoNode);
    
    // Render department heads
    ORG_CHART.ceo.reports.forEach(deptKey => {
        const dept = ORG_CHART[deptKey];
        const deptNode = createAgentNode(deptKey, dept);
        container.appendChild(deptNode);
    });
    
    // Render specialists
    Object.keys(ORG_CHART).forEach(key => {
        const agent = ORG_CHART[key];
        if (agent.team !== 'executive' && !ORG_CHART.ceo.reports.includes(key)) {
            // Skip if already rendered as department head
            const isDeptHead = Object.values(ORG_CHART).some(a => a.reports.includes(key));
            if (!isDeptHead) {
                const node = createAgentNode(key, agent);
                container.appendChild(node);
            }
        }
    });
}

function createAgentNode(key, agent) {
    const node = document.createElement('div');
    node.className = 'agent-node';
    node.dataset.agentKey = key;
    node.innerHTML = `
        <div class="agent-label">${agent.label}</div>
        <div class="agent-team">${agent.team}</div>
    `;
    return node;
}

// Load organizations
async function loadOrganizations() {
    try {
        const response = await fetch(`${API_BASE}/organizations`);
        if (!response.ok) throw new Error('Failed to load organizations');
        
        const orgs = await response.json();
        const select = document.getElementById('org-select');
        
        // Clear existing options except first
        select.innerHTML = '<option value="">Select Organization</option>';
        
        orgs.forEach(org => {
            const option = document.createElement('option');
            option.value = org.id;
            option.textContent = org.name;
            select.appendChild(option);
        });
        
        // Auto-select first org if available
        if (orgs.length > 0) {
            select.value = orgs[0].id;
            currentOrgId = orgs[0].id;
        }
    } catch (error) {
        console.error('Error loading organizations:', error);
        showNotification('Failed to load organizations', 'error');
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
        
        // Update task count
        document.getElementById('task-count').textContent = tasks.length;
    } catch (error) {
        console.error('Error loading tasks:', error);
    }
}

// Render task list
function renderTaskList(tasks) {
    const container = document.getElementById('task-list-container');
    
    if (tasks.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">◇</div>
                <p>No active missions for this organization</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = tasks.map(task => {
        const isRunning = task.status === 'running' || task.status === 'planning';
        return `
            <div class="task-item ${isRunning ? 'task-running-pulse' : ''}" onclick="showTaskDetail('${task.id}')">
                <div class="task-item-header">
                    <span class="task-id">${task.id.substring(0, 8)}...</span>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <span class="task-status ${task.status}">${task.status}</span>
                        ${isRunning ? `<button class="btn-danger-sm" onclick="event.stopPropagation(); cancelTask('${task.id}')" title="Stop running mission">⏹ Stop</button>` : ''}
                    </div>
                </div>
                <div class="task-prompt">${escapeHtml(task.prompt.substring(0, 150))}${task.prompt.length > 150 ? '...' : ''}</div>
                <div class="task-meta">
                    <span>LLM Calls: ${task.llm_call_count}</span>
                    <span>Tokens: ~${task.estimated_tokens}</span>
                    <span>Created: ${formatDate(task.created_at)}</span>
                </div>
            </div>
        `;
    }).join('');
}

// Deploy new task
async function deployTask() {
    const prompt = document.getElementById('task-prompt').value.trim();
    const repo = document.getElementById('task-repo').value.trim();
    const priority = parseInt(document.getElementById('task-priority').value);
    
    if (!prompt) {
        showNotification('Please enter a mission briefing', 'error');
        return;
    }
    
    if (!currentOrgId) {
        showNotification('Please select an organization', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/tasks`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                organization_id: currentOrgId,
                prompt: prompt,
                repo: repo || null,
                priority: priority
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to deploy task');
        }
        
        const task = await response.json();
        showNotification(`Mission deployed: ${task.id.substring(0, 8)}...`, 'success');
        
        // Clear form
        document.getElementById('task-prompt').value = '';
        document.getElementById('task-repo').value = '';
        document.getElementById('task-priority').value = '0';
        
        // Reload tasks
        loadTasks();
        
        // Show task detail
        showTaskDetail(task.id);
    } catch (error) {
        console.error('Error deploying task:', error);
        showNotification(error.message, 'error');
    }
}

// Show task detail
async function showTaskDetail(taskId) {
    try {
        const response = await fetch(`${API_BASE}/tasks/${taskId}`);
        if (!response.ok) throw new Error('Failed to load task');
        
        const task = await response.json();
        renderTaskDetail(task);
        
        document.getElementById('task-detail').style.display = 'block';
        document.getElementById('task-detail').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        console.error('Error loading task detail:', error);
        showNotification('Failed to load task details', 'error');
    }
}

// Render task detail
function renderTaskDetail(task) {
    const container = document.getElementById('task-detail-content');
    const isRunning = task.status === 'running' || task.status === 'planning';
    
    let html = `
        <div class="detail-section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h4>Mission Info</h4>
                ${isRunning ? `
                    <button class="btn-danger abort-btn" onclick="cancelTask('${task.id}')">
                        <span class="btn-icon">⏹</span> ABORT MISSION (STOP RUNNING)
                    </button>
                ` : ''}
            </div>
            <div class="detail-field">
                <span class="detail-label">Task ID:</span>
                <span class="detail-value">${task.id}</span>
            </div>
            <div class="detail-field">
                <span class="detail-label">Status:</span>
                <span class="detail-value"><span class="task-status ${task.status}">${task.status}</span></span>
            </div>
            <div class="detail-field">
                <span class="detail-label">Priority:</span>
                <span class="detail-value">${['Normal', 'High', 'Urgent'][task.priority]}</span>
            </div>
            <div class="detail-field">
                <span class="detail-label">Created:</span>
                <span class="detail-value">${formatDate(task.created_at)}</span>
            </div>
            <div class="detail-field">
                <span class="detail-label">LLM Calls:</span>
                <span class="detail-value">${task.llm_call_count}</span>
            </div>
            <div class="detail-field">
                <span class="detail-label">Est. Tokens:</span>
                <span class="detail-value">~${task.estimated_tokens}</span>
            </div>
        </div>
        
        <div class="detail-section">
            <h4>Mission Briefing</h4>
            <div class="detail-value" style="white-space: pre-wrap; background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 4px;">
                ${escapeHtml(task.prompt)}
            </div>
        </div>
    `;
    
    // Add agent tree
    if (task.org_tree) {
        html += `
            <div class="detail-section">
                <h4>Agent Execution Tree</h4>
                <div class="agent-tree">
                    ${renderAgentTree(task.org_tree, true)}
                </div>
            </div>
        `;
    }
    
    // Add final report or execution error report
    if (task.final_report) {
        const isFailed = task.status === 'failed';
        const isCancelled = task.status === 'cancelled';
        const titleText = isFailed ? '⚠ Execution Failure Log' : (isCancelled ? '⏹ Mission Aborted Log' : 'Final Report');
        const borderColor = isFailed ? '#ff3366' : (isCancelled ? '#ffaa00' : '#00f0ff');
        const bgColor = isFailed ? 'rgba(255, 51, 102, 0.1)' : (isCancelled ? 'rgba(255, 170, 0, 0.1)' : 'rgba(0, 240, 255, 0.05)');
        
        html += `
            <div class="detail-section">
                <div class="final-report">
                    <h4 style="color: ${borderColor};">${titleText}</h4>
                    <div class="final-report-content" style="border-color: ${borderColor}; background: ${bgColor}; color: ${isFailed ? '#ff99aa' : (isCancelled ? '#ffddaa' : '#e0f7ff')};">${escapeHtml(task.final_report)}</div>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// Cancel / Abort task execution
async function cancelTask(taskId) {
    if (!confirm('Are you sure you want to stop and abort this mission?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/tasks/${taskId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to stop task');
        }
        
        showNotification('Mission execution stopped', 'warning');
        loadTasks();
        showTaskDetail(taskId);
    } catch (error) {
        console.error('Error stopping task:', error);
        showNotification(error.message, 'error');
    }
}

// Create new organization boundary
async function createOrganization() {
    const input = document.getElementById('new-org-name');
    const name = input.value.trim();
    if (!name) {
        showNotification('Please enter an organization name', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/organizations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name })
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Failed to create organization');
        }
        
        const newOrg = await response.json();
        showNotification(`Organization boundary '${newOrg.name}' created!`, 'success');
        input.value = '';
        closeCreateOrgModal();
        
        // Reload organizations & set active org boundary
        await loadOrganizations();
        const select = document.getElementById('org-select');
        select.value = newOrg.id;
        currentOrgId = newOrg.id;
        loadTasks();
    } catch (error) {
        console.error('Error creating organization:', error);
        showNotification(error.message, 'error');
    }
}

function openCreateOrgModal() {
    document.getElementById('create-org-modal').style.display = 'flex';
    document.getElementById('new-org-name').focus();
}

function closeCreateOrgModal() {
    document.getElementById('create-org-modal').style.display = 'none';
}

// Render agent tree recursively
function renderAgentTree(node, isRoot = false) {
    const statusClass = node.status;
    let html = `
        <div class="tree-node ${isRoot ? 'tree-node-root' : ''}">
            <div class="tree-node-header">
                <span class="tree-node-label">${node.label}</span>
                <span class="tree-node-status task-status ${statusClass}">${node.status}</span>
            </div>
    `;
    
    if (node.result && node.status === 'done') {
        try {
            const result = JSON.parse(node.result);
            const summary = result.summary || node.result;
            html += `<div class="tree-node-result">${escapeHtml(summary)}</div>`;
        } catch {
            html += `<div class="tree-node-result">${escapeHtml(node.result)}</div>`;
        }
    }
    
    if (node.children && node.children.length > 0) {
        node.children.forEach(child => {
            html += renderAgentTree(child, false);
        });
    }
    
    html += '</div>';
    return html;
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification show ${type}`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Create default organization if none exists
async function ensureOrganization() {
    try {
        const response = await fetch(`${API_BASE}/organizations`);
        const orgs = await response.json();
        
        if (orgs.length === 0) {
            // Create default organization
            const createResponse = await fetch(`${API_BASE}/organizations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: 'Default Organization' })
            });
            
            if (createResponse.ok) {
                await loadOrganizations();
            }
        }
    } catch (error) {
        console.error('Error ensuring organization:', error);
    }
}

// Check if we need to create an organization
setTimeout(ensureOrganization, 1000);
