// Global state variables
let currentRules = [];
let currentConfig = {};
let currentCache = [];

// DOM Elements
const elements = {
  // Navigation
  navItems: document.querySelectorAll('.nav-item'),
  tabPanels: document.querySelectorAll('.tab-panel'),
  
  // Status Card
  statusDot: document.getElementById('status-dot'),
  statusLabel: document.getElementById('status-label'),
  statusDetails: document.getElementById('status-details'),
  connectionCard: document.getElementById('connection-status-card'),
  
  // Credentials
  credentialsForm: document.getElementById('credentials-form'),
  accessTokenInput: document.getElementById('access_token'),
  igAccountIdInput: document.getElementById('instagram_business_account_id'),
  fbPageIdInput: document.getElementById('facebook_page_id'),
  verifyTokenInput: document.getElementById('webhook_verify_token'),
  maxMediaInput: document.getElementById('max_media_to_scan'),
  maxCommentsInput: document.getElementById('max_comments_per_media'),
  lookbackHoursInput: document.getElementById('comment_lookback_hours'),
  toggleTokenBtn: document.getElementById('toggle-token-visibility'),
  testConnectionBtn: document.getElementById('test-connection-btn'),
  saveCredentialsBtn: document.getElementById('save-credentials-btn'),
  
  // Rules
  rulesContainer: document.getElementById('rules-list-container'),
  addRuleBtn: document.getElementById('add-rule-btn'),
  
  // Cache
  cacheCount: document.getElementById('cache-count'),
  cacheListEntries: document.getElementById('cache-list-entries'),
  clearCacheBtn: document.getElementById('clear-cache-btn'),
  
  // Logs
  logsConsole: document.getElementById('logs-console'),
  refreshLogsBtn: document.getElementById('refresh-logs-btn'),
  triggerPollBtn: document.getElementById('trigger-poll-btn'),
  
  // Modal
  ruleModal: document.getElementById('rule-modal'),
  ruleForm: document.getElementById('rule-form'),
  modalTitle: document.getElementById('modal-title'),
  modalCloseBtn: document.getElementById('modal-close-btn'),
  modalCancelBtn: document.getElementById('modal-cancel-btn'),
  modalSubmitBtn: document.getElementById('modal-submit-btn'),
  ruleId: document.getElementById('rule-id'),
  ruleName: document.getElementById('rule-name'),
  ruleTrigger: document.getElementById('rule-trigger'),
  keywordsGroup: document.getElementById('keywords-group'),
  ruleKeywords: document.getElementById('rule-keywords'),
  ruleDm: document.getElementById('rule-dm'),
  rulePublic: document.getElementById('rule-public'),
  ruleActive: document.getElementById('rule-active'),
  
  // Toast
  toastContainer: document.getElementById('toast-container')
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initVisibilityToggles();
  loadAllData();
  
  // Event Listeners
  elements.credentialsForm.addEventListener('submit', handleSaveCredentials);
  elements.testConnectionBtn.addEventListener('click', handleTestConnection);
  elements.addRuleBtn.addEventListener('click', () => openRuleModal());
  elements.modalCloseBtn.addEventListener('click', closeRuleModal);
  elements.modalCancelBtn.addEventListener('click', closeRuleModal);
  elements.ruleForm.addEventListener('submit', handleSaveRule);
  elements.ruleTrigger.addEventListener('change', toggleKeywordsVisibility);
  elements.clearCacheBtn.addEventListener('click', handleClearCache);
  elements.refreshLogsBtn.addEventListener('click', loadLogs);
  elements.triggerPollBtn.addEventListener('click', handleTriggerPoll);
});

// --- Tab Navigation ---
function initNavigation() {
  elements.navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.dataset.tab;
      
      // Update active nav button
      elements.navItems.forEach(btn => btn.classList.remove('active'));
      item.classList.add('active');
      
      // Update active panel
      elements.tabPanels.forEach(panel => {
        panel.classList.remove('active');
        if (panel.id === `panel-${targetTab}`) {
          panel.classList.add('active');
        }
      });
      
      // Specific action on tab load
      if (targetTab === 'logs') {
        loadLogs();
      } else if (targetTab === 'cache') {
        loadCache();
      }
    });
  });
}

// --- Visibility Toggles ---
function initVisibilityToggles() {
  elements.toggleTokenBtn.addEventListener('click', () => {
    const input = elements.accessTokenInput;
    const icon = elements.toggleTokenBtn.querySelector('i');
    if (input.type === 'password') {
      input.type = 'text';
      icon.className = 'fa-solid fa-eye-slash';
    } else {
      input.type = 'password';
      icon.className = 'fa-solid fa-eye';
    }
  });
}

function toggleKeywordsVisibility() {
  if (elements.ruleTrigger.value === 'keyword') {
    elements.keywordsGroup.style.display = 'block';
    elements.ruleKeywords.required = true;
  } else {
    elements.keywordsGroup.style.display = 'none';
    elements.ruleKeywords.required = false;
  }
}

// --- Notification Toast ---
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  let icon = 'fa-info-circle';
  if (type === 'success') icon = 'fa-circle-check';
  if (type === 'error') icon = 'fa-triangle-exclamation';
  
  toast.innerHTML = `
    <i class="fa-solid ${icon}"></i>
    <span>${message}</span>
  `;
  
  elements.toastContainer.appendChild(toast);
  
  // Remove toast after 4s
  setTimeout(() => {
    toast.style.animation = 'slideIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) reverse forwards';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// --- API Helpers ---
async function fetchAPI(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' }
  };
  if (body) {
    options.body = JSON.stringify(body);
  }
  
  try {
    const response = await fetch(endpoint, options);
    const data = await response.json();
    return { ok: response.ok, status: response.status, data };
  } catch (error) {
    console.error(`API Error fetching ${endpoint}:`, error);
    return { ok: false, status: 500, data: { message: 'Connection to local Python server failed.' } };
  }
}

// --- Data Loading ---
async function loadAllData() {
  await loadConfig();
  await loadRules();
  await loadCache();
  await loadLogs();
  checkConnectionStatus();
}

async function loadConfig() {
  const res = await fetchAPI('/api/config');
  if (res.ok) {
    currentConfig = res.data;
    elements.accessTokenInput.value = currentConfig.access_token || '';
    elements.igAccountIdInput.value = currentConfig.instagram_business_account_id || '';
    elements.fbPageIdInput.value = currentConfig.facebook_page_id || '';
    elements.verifyTokenInput.value = currentConfig.webhook_verify_token || 'my_secure_token';
    elements.maxMediaInput.value = currentConfig.max_media_to_scan || 20;
    elements.maxCommentsInput.value = currentConfig.max_comments_per_media || 50;
    elements.lookbackHoursInput.value = currentConfig.comment_lookback_hours || 24;
  }
}

async function loadRules() {
  const res = await fetchAPI('/api/rules');
  if (res.ok) {
    currentRules = res.data;
    renderRules();
  }
}

async function loadCache() {
  const res = await fetchAPI('/api/sent_comments');
  if (res.ok) {
    currentCache = res.data;
    elements.cacheCount.innerText = currentCache.length;
    renderCacheList();
  }
}

async function loadLogs() {
  const res = await fetchAPI('/api/logs');
  if (res.ok) {
    const logs = res.data.logs || [];
    elements.logsConsole.innerHTML = '';
    
    if (logs.length === 0) {
      elements.logsConsole.innerHTML = '<div class="log-line text-muted">No logs recorded yet. Run polling or trigger connection tests.</div>';
      return;
    }
    
    logs.forEach(line => {
      const lineDiv = document.createElement('div');
      lineDiv.className = 'log-line';
      
      // Basic log coloring
      if (line.includes('Error') || line.includes('Failed')) {
        lineDiv.style.color = '#f87171'; // Red
      } else if (line.includes('Success') || line.includes('connected!')) {
        lineDiv.style.color = '#34d399'; // Green
      } else if (line.includes('New comment detected')) {
        lineDiv.style.color = '#60a5fa'; // Blue
      } else if (line.includes('->')) {
        lineDiv.style.color = '#c084fc'; // Purple
      }
      
      lineDiv.textContent = line;
      elements.logsConsole.appendChild(lineDiv);
    });
    
    // Auto-scroll to bottom
    elements.logsConsole.scrollTop = elements.logsConsole.scrollHeight;
  }
}

async function checkConnectionStatus() {
  if (!currentConfig.access_token || !currentConfig.instagram_business_account_id) {
    updateStatus('disconnected', 'Not Configured', 'Setup credentials to connect.');
    return;
  }
  
  updateStatus('checking', 'Verifying Token...', 'Testing Instagram Graph API connection...');
  
  const res = await fetchAPI('/api/test-connection', 'POST', {
    access_token: currentConfig.access_token,
    instagram_business_account_id: currentConfig.instagram_business_account_id
  });
  
  if (res.ok && res.data.success) {
    updateStatus('connected', `@${res.data.username}`, 'API connected & verified.');
  } else {
    const errorMsg = res.data.message || 'Verification failed.';
    updateStatus('disconnected', 'Connection Failed', errorMsg);
  }
}

function updateStatus(state, label, details) {
  elements.statusDot.className = `status-dot ${state}`;
  elements.statusLabel.innerText = label;
  elements.statusDetails.innerText = details;
  elements.statusDetails.title = details;
}

// --- Credentials Actions ---
async function handleSaveCredentials(e) {
  e.preventDefault();
  
  const config = {
    access_token: elements.accessTokenInput.value.trim(),
    instagram_business_account_id: elements.igAccountIdInput.value.trim(),
    facebook_page_id: elements.fbPageIdInput.value.trim(),
    webhook_verify_token: elements.verifyTokenInput.value.trim(),
    max_media_to_scan: parseInt(elements.maxMediaInput.value),
    max_comments_per_media: parseInt(elements.maxCommentsInput.value),
    comment_lookback_hours: parseInt(elements.lookbackHoursInput.value) || 24
  };
  
  elements.saveCredentialsBtn.disabled = true;
  elements.saveCredentialsBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Saving...';
  
  const res = await fetchAPI('/api/config', 'POST', config);
  
  elements.saveCredentialsBtn.disabled = false;
  elements.saveCredentialsBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Configuration';
  
  if (res.ok) {
    showToast('Configuration saved successfully!', 'success');
    currentConfig = config;
    checkConnectionStatus();
  } else {
    showToast(res.data.message || 'Failed to save configuration.', 'error');
  }
}

async function handleTestConnection() {
  const access_token = elements.accessTokenInput.value.trim();
  const instagram_business_account_id = elements.igAccountIdInput.value.trim();
  
  if (!access_token || !instagram_business_account_id) {
    showToast('Please fill in Access Token and Instagram Account ID first.', 'error');
    return;
  }
  
  elements.testConnectionBtn.disabled = true;
  elements.testConnectionBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Testing...';
  
  const res = await fetchAPI('/api/test-connection', 'POST', {
    access_token,
    instagram_business_account_id
  });
  
  elements.testConnectionBtn.disabled = false;
  elements.testConnectionBtn.innerHTML = '<i class="fa-solid fa-plug"></i> Test Connection';
  
  if (res.ok && res.data.success) {
    showToast(res.data.message, 'success');
    updateStatus('connected', `@${res.data.username}`, 'API verified successfully.');
  } else {
    showToast(res.data.message || 'Connection test failed.', 'error');
    updateStatus('disconnected', 'Verification Failed', res.data.message || 'API verification failed.');
  }
}

// --- Rules Rendering & Actions ---
function renderRules() {
  elements.rulesContainer.innerHTML = '';
  
  if (currentRules.length === 0) {
    elements.rulesContainer.innerHTML = `
      <div class="glass-card text-center py-5">
        <i class="fa-solid fa-triangle-exclamation text-muted mb-3" style="font-size: 32px;"></i>
        <h3 class="panel-title">No Rules Configured</h3>
        <p class="panel-subtitle">Create a reply rule to start responding to Instagram comments automatically.</p>
      </div>
    `;
    return;
  }
  
  currentRules.forEach((rule, index) => {
    const card = document.createElement('div');
    card.className = `glass-card rule-card ${rule.active ? '' : 'inactive'}`;
    
    // Generate keywords tags
    let keywordsHTML = '';
    if (rule.trigger_type === 'keyword' && rule.keywords && rule.keywords.length > 0) {
      keywordsHTML = `
        <div class="rule-detail">
          <span class="rule-label">Trigger Keywords</span>
          <div class="keyword-tags">
            ${rule.keywords.map(kw => `<span class="tag">${kw}</span>`).join('')}
          </div>
        </div>
      `;
    }
    
    card.innerHTML = `
      <div class="rule-header">
        <div class="rule-title-area">
          <span class="rule-name">${rule.name}</span>
          <span class="badge ${rule.trigger_type === 'all' ? 'badge-universal' : 'badge-keyword'}">
            ${rule.trigger_type === 'all' ? 'Universal' : 'Keyword'}
          </span>
        </div>
        <div class="rule-actions">
          <label class="switch">
            <input type="checkbox" ${rule.active ? 'checked' : ''} onchange="toggleRuleActive('${rule.id}', this.checked)">
            <span class="slider"></span>
          </label>
          <button class="btn-icon" onclick="editRule('${rule.id}')" title="Edit Rule">
            <i class="fa-solid fa-pen-to-square"></i>
          </button>
          <button class="btn-icon btn-icon-danger" onclick="deleteRule('${rule.id}')" title="Delete Rule">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
      <div class="rule-body">
        ${keywordsHTML}
        <div class="rule-detail">
          <span class="rule-label">Send DM Message</span>
          <div class="rule-value">${escapeHTML(rule.dm_template)}</div>
        </div>
        ${rule.public_reply_template ? `
        <div class="rule-detail">
          <span class="rule-label">Post Public Comment Reply</span>
          <div class="rule-value">${escapeHTML(rule.public_reply_template)}</div>
        </div>
        ` : ''}
      </div>
    `;
    
    elements.rulesContainer.appendChild(card);
  });
}

// Escaping helper
function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

// Global functions linked to generated element onclick triggers
window.toggleRuleActive = async function(ruleId, active) {
  const rule = currentRules.find(r => r.id === ruleId);
  if (rule) {
    rule.active = active;
    
    // Save to server
    const res = await fetchAPI('/api/rules', 'POST', currentRules);
    if (res.ok) {
      showToast(`Rule "${rule.name}" ${active ? 'activated' : 'deactivated'}.`, 'success');
      loadRules();
    } else {
      showToast('Failed to update rule status.', 'error');
      // Reset checkbox in UI
      loadRules();
    }
  }
};

window.editRule = function(ruleId) {
  const rule = currentRules.find(r => r.id === ruleId);
  if (rule) {
    openRuleModal(rule);
  }
};

window.deleteRule = async function(ruleId) {
  const rule = currentRules.find(r => r.id === ruleId);
  if (!rule) return;
  
  if (confirm(`Are you sure you want to delete the rule "${rule.name}"?`)) {
    currentRules = currentRules.filter(r => r.id !== ruleId);
    
    const res = await fetchAPI('/api/rules', 'POST', currentRules);
    if (res.ok) {
      showToast('Rule deleted successfully.', 'success');
      renderRules();
    } else {
      showToast('Failed to delete rule.', 'error');
      loadRules();
    }
  }
};

// --- Rule Modal Functions ---
function openRuleModal(rule = null) {
  elements.ruleModal.classList.add('active');
  elements.ruleForm.reset();
  
  if (rule) {
    // Edit mode
    elements.modalTitle.innerText = 'Edit Reply Rule';
    elements.ruleId.value = rule.id;
    elements.ruleName.value = rule.name;
    elements.ruleTrigger.value = rule.trigger_type;
    elements.ruleKeywords.value = rule.keywords ? rule.keywords.join(', ') : '';
    elements.ruleDm.value = rule.dm_template;
    elements.rulePublic.value = rule.public_reply_template || '';
    elements.ruleActive.checked = rule.active;
  } else {
    // Add mode
    elements.modalTitle.innerText = 'Create Reply Rule';
    elements.ruleId.value = '';
    elements.ruleActive.checked = true;
  }
  
  toggleKeywordsVisibility();
}

function closeRuleModal() {
  elements.ruleModal.classList.remove('active');
}

async function handleSaveRule(e) {
  e.preventDefault();
  
  const id = elements.ruleId.value || 'rule_' + Date.now();
  const name = elements.ruleName.value.trim();
  const trigger_type = elements.ruleTrigger.value;
  const dm_template = elements.ruleDm.value.trim();
  const public_reply_template = elements.rulePublic.value.trim();
  const active = elements.ruleActive.checked;
  
  let keywords = [];
  if (trigger_type === 'keyword') {
    keywords = elements.ruleKeywords.value
      .split(',')
      .map(kw => kw.trim())
      .filter(kw => kw.length > 0);
  }
  
  const ruleData = {
    id,
    name,
    trigger_type,
    keywords,
    dm_template,
    public_reply_template,
    active
  };
  
  let updatedRules = [...currentRules];
  const existingIndex = currentRules.findIndex(r => r.id === id);
  
  if (existingIndex > -1) {
    updatedRules[existingIndex] = ruleData;
  } else {
    // Insert new rules
    updatedRules.push(ruleData);
  }
  
  elements.modalSubmitBtn.disabled = true;
  elements.modalSubmitBtn.innerText = 'Saving...';
  
  const res = await fetchAPI('/api/rules', 'POST', updatedRules);
  
  elements.modalSubmitBtn.disabled = false;
  elements.modalSubmitBtn.innerText = 'Save Rule';
  
  if (res.ok) {
    showToast('Rule saved successfully!', 'success');
    currentRules = updatedRules;
    renderRules();
    closeRuleModal();
  } else {
    showToast('Failed to save rule details.', 'error');
  }
}

// --- Cache Actions ---
function renderCacheList() {
  elements.cacheListEntries.innerHTML = '';
  
  if (currentCache.length === 0) {
    elements.cacheListEntries.innerHTML = '<li class="empty-state">No processed comments in database.</li>';
    return;
  }
  
  // Show list items reversed (latest first)
  const reversedCache = [...currentCache].reverse();
  reversedCache.forEach(id => {
    const li = document.createElement('li');
    li.textContent = id;
    elements.cacheListEntries.appendChild(li);
  });
}

async function handleClearCache() {
  if (currentCache.length === 0) {
    showToast('Cache database is already empty.', 'info');
    return;
  }
  
  if (confirm('Are you sure you want to clear the processed comments database? This will cause the bot to reply to old comments again on the next polling run.')) {
    elements.clearCacheBtn.disabled = true;
    
    const res = await fetchAPI('/api/sent_comments', 'POST', []);
    
    elements.clearCacheBtn.disabled = false;
    
    if (res.ok) {
      showToast('Cache database cleared successfully!', 'success');
      currentCache = [];
      elements.cacheCount.innerText = '0';
      renderCacheList();
    } else {
      showToast('Failed to clear cache database.', 'error');
    }
  }
}

// --- Poll & Trigger Actions ---
async function handleTriggerPoll() {
  if (!currentConfig.access_token || !currentConfig.instagram_business_account_id) {
    showToast('Please configure and save your credentials first.', 'error');
    return;
  }
  
  elements.triggerPollBtn.disabled = true;
  elements.triggerPollBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Polling...';
  
  showToast('Instagram polling run triggered. Check logs panel.', 'info');
  
  const res = await fetchAPI('/api/trigger-poll', 'POST');
  
  elements.triggerPollBtn.disabled = false;
  elements.triggerPollBtn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Run Manual Poll';
  
  if (res.ok && res.data.success) {
    showToast(res.data.message, 'success');
  } else {
    showToast(res.data.message || 'Polling run failed.', 'error');
  }
  
  // Reload logs and cache info
  loadLogs();
  loadCache();
}
