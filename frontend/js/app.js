/**
 * Main Application Controller for Smart Expense Tracker
 */

const state = {
  currentView: 'dashboard',
  selectedMonth: new Date().toISOString().slice(0, 7), // 'YYYY-MM'
  currentUser: null,
  categories: [],
  expenses: [],
  friends: [],
  splits: [],
  parsedAIExpense: null,
  dashboardData: null,
  monthlyReport: null
};

// --- DOM Ready Initialization ---
document.addEventListener('DOMContentLoaded', async () => {
  initMonthSelector();
  setupEventListeners();
  setupAuthEventListeners();
  await initAuth();
  await loadCategories();
  await refreshCurrentView();
});

async function initAuth() {
  const token = localStorage.getItem('access_token');
  if (token) {
    try {
      state.currentUser = await API.getMe();
    } catch (err) {
      console.warn('Token expired or invalid:', err.message);
      localStorage.removeItem('access_token');
      state.currentUser = null;
    }
  }
  updateAuthHeaderUI();
}

function updateAuthHeaderUI() {
  const container = document.getElementById('auth-header-container');
  if (!container) return;

  if (state.currentUser) {
    container.innerHTML = `
      <div class="flex items-center gap-1.5 sm:gap-2">
        <div class="flex items-center gap-1 px-2 py-1 sm:px-2.5 sm:py-1 rounded-lg bg-purple-500/10 border border-purple-500/30 text-[11px] sm:text-xs font-semibold text-purple-200 max-w-[100px] sm:max-w-[160px]">
          <span>👤</span>
          <span class="truncate">${state.currentUser.username}</span>
        </div>
        <button id="logout-btn" class="px-2 py-1 sm:px-2.5 sm:py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] sm:text-xs font-medium text-gray-300 transition shrink-0" title="Log Out">
          🚪 Logout
        </button>
      </div>
    `;
    document.getElementById('logout-btn')?.addEventListener('click', handleLogout);
  } else {
    container.innerHTML = `
      <button id="open-auth-modal-btn" class="px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-purple-600/30 hover:bg-purple-600/50 border border-purple-500/40 text-[11px] sm:text-xs font-semibold text-purple-200 transition flex items-center gap-1">
        <span>🔐</span> Login / Register
      </button>
    `;
    document.getElementById('open-auth-modal-btn')?.addEventListener('click', openAuthModal);
  }
}


function openAuthModal() {
  document.getElementById('auth-modal')?.classList.remove('hidden');
}

function closeAuthModal() {
  document.getElementById('auth-modal')?.classList.add('hidden');
}

function setupAuthEventListeners() {
  document.getElementById('open-auth-modal-btn')?.addEventListener('click', openAuthModal);
  document.getElementById('close-auth-modal-btn')?.addEventListener('click', closeAuthModal);

  const loginTab = document.getElementById('tab-login-btn');
  const regTab = document.getElementById('tab-register-btn');
  const loginForm = document.getElementById('login-form');
  const regForm = document.getElementById('register-form');

  if (loginTab && regTab) {
    loginTab.addEventListener('click', () => {
      loginTab.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition bg-purple-600 text-white';
      regTab.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition text-gray-400 hover:text-white';
      loginForm?.classList.remove('hidden');
      regForm?.classList.add('hidden');
    });

    regTab.addEventListener('click', () => {
      regTab.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition bg-purple-600 text-white';
      loginTab.className = 'flex-1 py-2 text-xs font-bold rounded-lg transition text-gray-400 hover:text-white';
      regForm?.classList.remove('hidden');
      loginForm?.classList.add('hidden');
    });
  }

  loginForm?.addEventListener('submit', handleLoginSubmit);
  regForm?.addEventListener('submit', handleRegisterSubmit);
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  const btn = document.getElementById('login-submit-btn');
  const origText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = 'Signing in...';

  try {
    const res = await API.login(email, password);
    localStorage.setItem('access_token', res.access_token);
    state.currentUser = res.user;
    updateAuthHeaderUI();
    closeAuthModal();
    showToast(`Welcome back, ${res.user.username}!`, 'success');
    await loadCategories();
    await refreshCurrentView();
  } catch (err) {
    showToast('Login failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = origText;
  }
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const username = document.getElementById('reg-username').value.trim();
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;

  const btn = document.getElementById('register-submit-btn');
  const origText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = 'Creating account...';

  try {
    const res = await API.register(email, username, password);
    localStorage.setItem('access_token', res.access_token);
    state.currentUser = res.user;
    updateAuthHeaderUI();
    closeAuthModal();
    showToast(`Account created! Welcome, ${res.user.username}.`, 'success');
    await loadCategories();
    await refreshCurrentView();
  } catch (err) {
    showToast('Registration failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = origText;
  }
}

function handleLogout() {
  localStorage.removeItem('access_token');
  state.currentUser = null;
  updateAuthHeaderUI();
  showToast('Logged out.', 'info');
  loadCategories();
  refreshCurrentView();
}


function initMonthSelector() {
  const monthInput = document.getElementById('month-selector');
  if (monthInput) {
    monthInput.value = state.selectedMonth;
    monthInput.addEventListener('change', async (e) => {
      state.selectedMonth = e.target.value || new Date().toISOString().slice(0, 7);
      await refreshCurrentView();
    });
  }
}

function setupEventListeners() {
  // Navigation tabs
  document.querySelectorAll('[data-view-target]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetView = btn.getAttribute('data-view-target');
      switchView(targetView);
    });
  });

  // AI Parse Form
  const aiForm = document.getElementById('ai-parse-form');
  if (aiForm) {
    aiForm.addEventListener('submit', handleAIParseSubmit);
  }

  // Confirm Parsed Expense Button
  const confirmBtn = document.getElementById('confirm-parsed-btn');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', handleSaveExpenseFromParsed);
  }

  // Manual Expense Form
  const manualForm = document.getElementById('manual-expense-form');
  if (manualForm) {
    manualForm.addEventListener('submit', handleManualExpenseSubmit);
  }

  // Add Category Form
  const catForm = document.getElementById('add-category-form');
  if (catForm) {
    catForm.addEventListener('submit', handleAddCategorySubmit);
  }

  // History Search & Filters
  const searchInput = document.getElementById('history-search');
  const catFilter = document.getElementById('history-cat-filter');
  if (searchInput) {
    searchInput.addEventListener('input', debounce(loadHistoryExpenses, 300));
  }
  if (catFilter) {
    catFilter.addEventListener('change', loadHistoryExpenses);
  }

  // Regenerate AI Report Button
  const regenBtn = document.getElementById('regen-report-btn');
  if (regenBtn) {
    regenBtn.addEventListener('click', async () => {
      showToast('Generating AI report narrative...', 'info');
      await loadMonthlyReport(true);
    });
  }

  // --- Split & Friends Modal Triggers ---
  document.getElementById('open-add-friend-modal-btn')?.addEventListener('click', () => {
    document.getElementById('add-friend-modal')?.classList.remove('hidden');
  });

  document.getElementById('open-add-split-modal-btn')?.addEventListener('click', openAddSplitModal);
  document.getElementById('open-direct-loan-modal-btn')?.addEventListener('click', openDirectLoanModal);
  document.getElementById('open-settle-modal-btn')?.addEventListener('click', openSettleUpModal);

  // Form Submits
  document.getElementById('add-friend-form')?.addEventListener('submit', handleAddFriendSubmit);
  document.getElementById('add-split-form')?.addEventListener('submit', handleAddSplitSubmit);
  document.getElementById('direct-loan-form')?.addEventListener('submit', handleDirectLoanSubmit);
  document.getElementById('settle-up-form')?.addEventListener('submit', handleSettleUpSubmit);

  // Personal expense toggle checkbox in split bill
  document.getElementById('split-log-personal')?.addEventListener('change', (e) => {
    const wrapper = document.getElementById('split-category-select-wrapper');
    if (wrapper) {
      if (e.target.checked) wrapper.classList.remove('hidden');
      else wrapper.classList.add('hidden');
    }
  });

  // Dynamic share preview calculation on total amount or participant change
  document.getElementById('split-total-amount')?.addEventListener('input', updateSplitSharePreview);
}

function switchView(viewName) {
  state.currentView = viewName;

  // Update Nav links active state
  document.querySelectorAll('[data-view-target]').forEach(btn => {
    if (btn.getAttribute('data-view-target') === viewName) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Toggle View Containers
  document.querySelectorAll('.view-container').forEach(el => {
    el.classList.add('hidden');
  });

  const activeContainer = document.getElementById(`view-${viewName}`);
  if (activeContainer) {
    activeContainer.classList.remove('hidden');
  }

  refreshCurrentView();
}

async function refreshCurrentView() {
  switch (state.currentView) {
    case 'dashboard':
      await loadDashboardView();
      break;
    case 'quick-add':
      populateCategoryDropdowns();
      break;
    case 'splits':
      await loadSplitsView();
      break;
    case 'report':
      await loadMonthlyReport(false);
      break;
    case 'history':
      populateCategoryFilterDropdown();
      await loadHistoryExpenses();
      break;
    case 'categories':
      renderCategoriesGrid();
      break;
  }
}

// --- Data Loaders ---
async function loadCategories() {
  try {
    state.categories = await API.getCategories();
    populateCategoryDropdowns();
    populateCategoryFilterDropdown();
  } catch (err) {
    showToast('Failed to load categories: ' + err.message, 'error');
  }
}

function populateCategoryDropdowns() {
  const selects = ['manual-category-select', 'confirm-category-select'];
  selects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = state.categories.map(c => 
      `<option value="${c.id}">${c.icon} ${c.name}</option>`
    ).join('');
  });
}

function populateCategoryFilterDropdown() {
  const el = document.getElementById('history-cat-filter');
  if (!el) return;
  const currentVal = el.value;
  el.innerHTML = '<option value="">All Categories</option>' + 
    state.categories.map(c => `<option value="${c.id}">${c.icon} ${c.name}</option>`).join('');
  el.value = currentVal;
}

async function loadDashboardView() {
  try {
    const data = await API.getDashboard(state.selectedMonth);
    state.dashboardData = data;

    // Update Metric Cards
    document.getElementById('dash-total-amount').innerText = `₹${data.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    document.getElementById('dash-expense-count').innerText = `${data.expense_count} entries`;
    
    const pctEl = document.getElementById('dash-pct-change');
    if (pctEl) {
      if (data.percentage_change > 0) {
        pctEl.className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30';
        pctEl.innerText = `+${data.percentage_change}% vs last mo`;
      } else if (data.percentage_change < 0) {
        pctEl.className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
        pctEl.innerText = `${data.percentage_change}% vs last mo`;
      } else {
        pctEl.className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-500/20 text-gray-400';
        pctEl.innerText = `0% change`;
      }
    }

    // Top Category
    const topCatEl = document.getElementById('dash-top-category');
    if (topCatEl) {
      if (data.top_categories && data.top_categories.length > 0) {
        const top = data.top_categories[0];
        topCatEl.innerText = `${top.icon} ${top.category_name} (₹${top.amount.toLocaleString('en-IN')})`;
      } else {
        topCatEl.innerText = 'No expenses logged';
      }
    }

    // Render Charts
    renderCategoryDonutChart('donut-chart-canvas', data.category_breakdown);
    renderMonthlyBarChart('bar-chart-canvas', state.selectedMonth, data.total_amount, data.prev_month_total);

    // Render Top Categories List
    renderTopCategoriesList(data.top_categories, data.total_amount);

  } catch (err) {
    showToast('Failed to refresh dashboard: ' + err.message, 'error');
  }
}

function renderTopCategoriesList(topCategories, totalAmount) {
  const container = document.getElementById('top-categories-list');
  if (!container) return;

  if (!topCategories || topCategories.length === 0) {
    container.innerHTML = `<div class="text-center py-6 text-gray-400 text-sm">No expenses logged for ${state.selectedMonth}.</div>`;
    return;
  }

  container.innerHTML = topCategories.map(cat => `
    <div class="flex items-center justify-between p-3 rounded-xl bg-slate-800/40 border border-white/5 hover:border-purple-500/30 transition">
      <div class="flex items-center gap-3">
        <span class="text-2xl p-2 rounded-lg bg-slate-700/50">${cat.icon}</span>
        <div>
          <h4 class="font-medium text-sm text-gray-200">${cat.category_name}</h4>
          <span class="text-xs text-gray-400">${cat.count} transaction${cat.count > 1 ? 's' : ''}</span>
        </div>
      </div>
      <div class="text-right">
        <span class="font-semibold text-sm text-white">₹${cat.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        <div class="text-xs text-purple-400">${cat.percentage}%</div>
      </div>
    </div>
  `).join('');
}

async function loadMonthlyReport(forceRefresh = false) {
  try {
    const report = await API.getMonthlyReport(state.selectedMonth, forceRefresh);
    state.monthlyReport = report;

    document.getElementById('report-month-title').innerText = `Monthly Insight Report — ${state.selectedMonth}`;
    document.getElementById('report-total-spend').innerText = `₹${report.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

    // Render AI summary markdown / HTML
    const summaryContainer = document.getElementById('report-ai-content');
    if (summaryContainer) {
      summaryContainer.innerHTML = formatMarkdownText(report.ai_summary);
    }

    // Render Breakdown Table
    const tableBody = document.getElementById('report-table-body');
    if (tableBody) {
      const breakdown = report.category_breakdown || {};
      const entries = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);

      if (entries.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="3" class="text-center py-4 text-gray-400">No category breakdown data available.</td></tr>`;
      } else {
        tableBody.innerHTML = entries.map(([catName, amt]) => {
          const catObj = state.categories.find(c => c.name === catName) || { icon: '🏷️' };
          const pct = report.total_amount > 0 ? ((amt / report.total_amount) * 100).toFixed(1) : '0';
          return `
            <tr class="border-b border-gray-800 hover:bg-slate-800/30 transition">
              <td class="py-3 px-4 flex items-center gap-2">
                <span>${catObj.icon}</span>
                <span class="font-medium text-gray-200 text-sm">${catName}</span>
              </td>
              <td class="py-3 px-4 text-right font-semibold text-gray-200 text-sm">₹${amt.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
              <td class="py-3 px-4 text-right text-xs text-purple-400">${pct}%</td>
            </tr>
          `;
        }).join('');
      }
    }

  } catch (err) {
    showToast('Failed to load report: ' + err.message, 'error');
  }
}

async function loadHistoryExpenses() {
  try {
    const search = document.getElementById('history-search')?.value || null;
    const catId = document.getElementById('history-cat-filter')?.value || null;

    const expenses = await API.getExpenses(state.selectedMonth, catId, search);
    state.expenses = expenses;

    const container = document.getElementById('history-list-container');
    if (!container) return;

    if (expenses.length === 0) {
      container.innerHTML = `
        <div class="text-center py-12 glass-panel">
          <p class="text-gray-400 text-sm">No expenses found matching filters.</p>
        </div>`;
      return;
    }

    container.innerHTML = expenses.map(e => {
      const cat = e.category || { icon: '🏷️', name: 'Uncategorized' };
      const formattedDate = new Date(e.date).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
      return `
        <div class="glass-panel p-4 flex items-center justify-between hover:border-purple-500/40 transition">
          <div class="flex items-center gap-3.5">
            <span class="text-2xl p-2.5 rounded-xl bg-slate-800/80 border border-white/10">${cat.icon}</span>
            <div>
              <h4 class="font-semibold text-sm text-gray-100">${e.description || cat.name}</h4>
              <div class="flex items-center gap-2 mt-0.5">
                <span class="text-xs px-2 py-0.5 rounded-md bg-purple-500/10 text-purple-300 border border-purple-500/20">${cat.name}</span>
                <span class="text-xs text-gray-400">${formattedDate}</span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <span class="font-bold text-base text-gray-100">₹${e.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
            <button onclick="handleDeleteExpense(${e.id})" class="p-1.5 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 transition" title="Delete Expense">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      `;
    }).join('');

  } catch (err) {
    showToast('Failed to load expense history: ' + err.message, 'error');
  }
}

function renderCategoriesGrid() {
  const container = document.getElementById('categories-grid');
  if (!container) return;

  container.innerHTML = state.categories.map(c => `
    <div class="glass-panel p-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <span class="text-2xl">${c.icon}</span>
        <div>
          <h4 class="font-semibold text-sm text-gray-200">${c.name}</h4>
          <span class="text-xs text-gray-400">${c.is_default ? 'Default Category' : 'Custom Category'}</span>
        </div>
      </div>
    </div>
  `).join('');
}

// --- Event Handlers ---
async function handleAIParseSubmit(e) {
  e.preventDefault();
  const inputEl = document.getElementById('ai-text-input');
  const text = inputEl.value.trim();
  if (!text) return;

  const btn = document.getElementById('ai-parse-btn');
  const originalHTML = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="inline-block animate-spin mr-2">⚙️</span> Parsing with AI...`;

  try {
    const parsed = await API.parseExpenseText(text);
    state.parsedAIExpense = parsed;

    // Show Confirmation Card / Modal
    document.getElementById('confirm-amount-input').value = parsed.amount;
    document.getElementById('confirm-desc-input').value = parsed.description;
    document.getElementById('confirm-date-input').value = parsed.date;
    
    if (parsed.category_id) {
      document.getElementById('confirm-category-select').value = parsed.category_id;
    }

    const confPct = Math.round(parsed.confidence * 100);
    document.getElementById('parsed-confidence-badge').innerText = `${parsed.is_ai ? '✨ AI Parsed' : '⚡ Auto Parsed'} (${confPct}% confidence)`;

    document.getElementById('ai-parsed-preview-modal').classList.remove('hidden');

  } catch (err) {
    showToast('AI Parsing failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHTML;
  }
}

async function handleSaveExpenseFromParsed() {
  if (!state.parsedAIExpense) return;

  const amount = parseFloat(document.getElementById('confirm-amount-input').value);
  const categoryId = parseInt(document.getElementById('confirm-category-select').value);
  const description = document.getElementById('confirm-desc-input').value.trim();
  const dateVal = document.getElementById('confirm-date-input').value;

  if (isNaN(amount) || amount <= 0) {
    showToast('Please enter a valid expense amount.', 'error');
    return;
  }

  try {
    await API.createExpense({
      amount,
      category_id: categoryId,
      description,
      raw_input: state.parsedAIExpense.raw_text,
      date: dateVal
    });

    showToast('Expense logged successfully!', 'success');
    document.getElementById('ai-parsed-preview-modal').classList.add('hidden');
    document.getElementById('ai-text-input').value = '';
    state.parsedAIExpense = null;

    switchView('dashboard');
  } catch (err) {
    showToast('Failed to save expense: ' + err.message, 'error');
  }
}

async function handleManualExpenseSubmit(e) {
  e.preventDefault();

  const amount = parseFloat(document.getElementById('manual-amount').value);
  const categoryId = parseInt(document.getElementById('manual-category-select').value);
  const description = document.getElementById('manual-desc').value.trim();
  const dateVal = document.getElementById('manual-date').value || new Date().toISOString().slice(0, 10);

  if (isNaN(amount) || amount <= 0) {
    showToast('Please enter a valid positive amount.', 'error');
    return;
  }

  try {
    await API.createExpense({
      amount,
      category_id: categoryId,
      description,
      raw_input: null,
      date: dateVal
    });

    showToast('Expense added successfully!', 'success');
    document.getElementById('manual-expense-form').reset();
    switchView('dashboard');
  } catch (err) {
    showToast('Error adding expense: ' + err.message, 'error');
  }
}

async function handleAddCategorySubmit(e) {
  e.preventDefault();
  const name = document.getElementById('cat-name-input').value.trim();
  const icon = document.getElementById('cat-icon-input').value.trim() || '🏷️';

  if (!name) return;

  try {
    const newCat = await API.createCategory({ name, icon });
    showToast(`Category "${newCat.name}" created!`, 'success');
    document.getElementById('add-category-form').reset();
    await loadCategories();
    renderCategoriesGrid();
  } catch (err) {
    showToast('Failed to create category: ' + err.message, 'error');
  }
}

async function handleDeleteExpense(expenseId) {
  if (!confirm('Are you sure you want to delete this expense entry?')) return;

  try {
    await API.deleteExpense(expenseId);
    showToast('Expense deleted.', 'success');
    await refreshCurrentView();
  } catch (err) {
    showToast('Failed to delete: ' + err.message, 'error');
  }
}

// --- Utilities ---
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const bg = type === 'success' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' :
             type === 'error' ? 'bg-rose-500/20 text-rose-300 border-rose-500/30' :
             'bg-purple-500/20 text-purple-300 border-purple-500/30';

  toast.className = `p-3 px-4 rounded-xl border ${bg} backdrop-blur-lg shadow-xl text-sm font-medium transition-all duration-300 transform translate-y-2 opacity-0 flex items-center gap-2`;
  toast.innerHTML = `<span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span> <span>${message}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function formatMarkdownText(text) {
  if (!text) return '';
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
    .replace(/\n\n/g, '</p><p class="mt-3 text-gray-300 text-sm leading-relaxed">')
    .replace(/\n/g, '<br>');
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// --- Split & Friends Logic ---

async function loadSplitsView() {
  try {
    state.friends = await API.getFriends();
    state.splits = await API.getSplits();

    renderFriendsList();
    renderSplitsHistory();
    updateSplitsSummary();
  } catch (err) {
    showToast('Failed to load splits data: ' + err.message, 'error');
  }
}

function updateSplitsSummary() {
  let totalOwed = 0.0;
  let totalOwe = 0.0;

  state.friends.forEach(f => {
    if (f.net_balance > 0) {
      totalOwed += f.net_balance;
    } else if (f.net_balance < 0) {
      totalOwe += Math.abs(f.net_balance);
    }
  });

  const overallNet = totalOwed - totalOwe;

  const totalOwedEl = document.getElementById('splits-total-owed');
  const totalOweEl = document.getElementById('splits-total-owe');
  const netStatusEl = document.getElementById('splits-net-status');

  if (totalOwedEl) totalOwedEl.innerText = `₹${totalOwed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  if (totalOweEl) totalOweEl.innerText = `₹${totalOwe.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

  if (netStatusEl) {
    if (overallNet > 0) {
      netStatusEl.className = 'text-lg font-extrabold text-emerald-400';
      netStatusEl.innerText = `You are owed ₹${overallNet.toLocaleString('en-IN', { minimumFractionDigits: 2 })} net`;
    } else if (overallNet < 0) {
      netStatusEl.className = 'text-lg font-extrabold text-rose-400';
      netStatusEl.innerText = `You owe ₹${Math.abs(overallNet).toLocaleString('en-IN', { minimumFractionDigits: 2 })} net`;
    } else {
      netStatusEl.className = 'text-lg font-extrabold text-purple-300';
      netStatusEl.innerText = 'Settled Up';
    }
  }

  const badge = document.getElementById('friends-count-badge');
  if (badge) badge.innerText = `${state.friends.length} Friend${state.friends.length !== 1 ? 's' : ''}`;
}

function renderFriendsList() {
  const container = document.getElementById('friends-list-container');
  if (!container) return;

  if (state.friends.length === 0) {
    container.innerHTML = `
      <div class="col-span-full text-center py-8 text-gray-400 text-sm">
        No friends added yet. Click <strong>+ Add Friend</strong> above to get started!
      </div>
    `;
    return;
  }

  container.innerHTML = state.friends.map(f => {
    let balBadgeClass = 'bg-slate-700/40 text-gray-300 border-slate-600/30';
    let balText = 'Settled Up';

    if (f.net_balance > 0) {
      balBadgeClass = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      balText = `Owes you ₹${f.net_balance.toFixed(2)}`;
    } else if (f.net_balance < 0) {
      balBadgeClass = 'bg-rose-500/20 text-rose-300 border-rose-500/30';
      balText = `You owe ₹${Math.abs(f.net_balance).toFixed(2)}`;
    }

    return `
      <div class="glass-panel p-4 flex flex-col justify-between hover:border-purple-500/40 transition gap-3">
        <div class="flex items-start justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-purple-600/30 border border-purple-500/30 flex items-center justify-center text-lg font-bold text-purple-200">
              ${f.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h4 class="font-bold text-sm text-gray-100">${f.name}</h4>
              <span class="text-[11px] text-gray-400 block">${f.email || f.phone || 'Contact'}</span>
            </div>
          </div>
          <button onclick="handleDeleteFriend(${f.id})" class="text-gray-500 hover:text-rose-400 text-xs p-1" title="Delete Friend">
            ✕
          </button>
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-white/5">
          <span class="text-xs font-semibold px-2.5 py-1 rounded-full border ${balBadgeClass}">
            ${balText}
          </span>
          ${f.net_balance !== 0 ? `
            <button onclick="openSettleUpForFriend(${f.id}, ${Math.abs(f.net_balance)})" class="text-xs font-bold px-2.5 py-1 rounded-lg bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-200 border border-emerald-500/40 transition">
              Settle
            </button>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function renderSplitsHistory() {
  const container = document.getElementById('splits-history-list');
  if (!container) return;

  if (state.splits.length === 0) {
    container.innerHTML = `
      <div class="text-center py-8 text-gray-400 text-sm">
        No split expenses or loan records yet.
      </div>
    `;
    return;
  }

  container.innerHTML = state.splits.map(s => {
    const formattedDate = new Date(s.date).toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
    const isSettlement = s.transaction_type === 'SETTLEMENT';
    const isLoan = s.transaction_type === 'DIRECT_LOAN';

    const typeIcon = isSettlement ? '🤝' : isLoan ? '💸' : '🍕';
    const typeLabel = isSettlement ? 'Settlement' : isLoan ? 'Direct Loan' : 'Shared Bill';

    const participantsText = s.participants.map(p => `${p.friend_name}: ₹${p.share_amount.toFixed(2)}`).join(', ');

    return `
      <div class="glass-panel p-4 flex items-center justify-between hover:border-purple-500/40 transition">
        <div class="flex items-center gap-3.5">
          <span class="text-2xl p-2.5 rounded-xl bg-slate-800/80 border border-white/10">${typeIcon}</span>
          <div>
            <div class="flex items-center gap-2">
              <h4 class="font-semibold text-sm text-gray-100">${s.title}</h4>
              <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-md ${isSettlement ? 'bg-emerald-500/20 text-emerald-300' : isLoan ? 'bg-indigo-500/20 text-indigo-300' : 'bg-purple-500/20 text-purple-300'}">
                ${typeLabel}
              </span>
            </div>
            <p class="text-xs text-gray-400 mt-1">
              Paid by <strong class="text-gray-200">${s.paid_by_name}</strong> • Split: ${participantsText}
            </p>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <div class="text-right">
            <span class="font-extrabold text-sm text-white">₹${s.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
            <span class="text-xs text-gray-400 block">${formattedDate}</span>
          </div>
          <button onclick="handleDeleteSplit(${s.id})" class="p-1.5 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 transition" title="Delete Split Record">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    `;
  }).join('');
}

async function openAddSplitModal() {
  if (state.friends.length === 0) {
    showToast('Please add at least 1 friend before splitting bills.', 'error');
    document.getElementById('add-friend-modal')?.classList.remove('hidden');
    return;
  }

  // Populate Paid By select dropdown
  const paidBySelect = document.getElementById('split-paid-by');
  if (paidBySelect) {
    paidBySelect.innerHTML = `<option value="user">You (Logged-in User)</option>` +
      state.friends.map(f => `<option value="${f.id}">${f.name}</option>`).join('');
  }

  // Populate Category select dropdown for personal logging
  const catSelect = document.getElementById('split-category-select');
  if (catSelect) {
    catSelect.innerHTML = state.categories.map(c => `<option value="${c.id}">${c.icon} ${c.name}</option>`).join('');
  }

  // Populate Participant Checkboxes (You + all friends)
  const checkboxesContainer = document.getElementById('split-participants-checkboxes');
  if (checkboxesContainer) {
    checkboxesContainer.innerHTML = `
      <label class="flex items-center gap-2 text-xs font-semibold text-gray-200 cursor-pointer">
        <input type="checkbox" class="split-part-cb accent-purple-500" value="user" checked> You (Logged-in User)
      </label>
    ` + state.friends.map(f => `
      <label class="flex items-center gap-2 text-xs font-semibold text-gray-200 cursor-pointer">
        <input type="checkbox" class="split-part-cb accent-purple-500" value="${f.id}" checked> ${f.name}
      </label>
    `).join('');

    // Attach listeners to checkboxes to update live share preview
    checkboxesContainer.querySelectorAll('.split-part-cb').forEach(cb => {
      cb.addEventListener('change', updateSplitSharePreview);
    });
  }

  // Set default date to today
  document.getElementById('split-date').value = new Date().toISOString().slice(0, 10);
  updateSplitSharePreview();

  document.getElementById('add-split-modal')?.classList.remove('hidden');
}

function updateSplitSharePreview() {
  const amount = parseFloat(document.getElementById('split-total-amount')?.value) || 0;
  const checked = document.querySelectorAll('.split-part-cb:checked');
  const previewEl = document.getElementById('split-preview-text');

  if (!previewEl) return;

  if (checked.length === 0) {
    previewEl.innerText = 'Please select at least 1 participant.';
    return;
  }

  const share = (amount / checked.length).toFixed(2);
  previewEl.innerText = `₹${amount.toFixed(2)} total ÷ ${checked.length} participant${checked.length > 1 ? 's' : ''} = ₹${share} per person.`;
}

function openDirectLoanModal() {
  if (state.friends.length === 0) {
    showToast('Please add at least 1 friend first.', 'error');
    document.getElementById('add-friend-modal')?.classList.remove('hidden');
    return;
  }

  const friendSelect = document.getElementById('loan-friend-select');
  if (friendSelect) {
    friendSelect.innerHTML = state.friends.map(f => `<option value="${f.id}">${f.name}</option>`).join('');
  }

  document.getElementById('direct-loan-modal')?.classList.remove('hidden');
}

function openSettleUpModal() {
  if (state.friends.length === 0) {
    showToast('No friends to settle up with.', 'error');
    return;
  }

  const friendSelect = document.getElementById('settle-friend-select');
  if (friendSelect) {
    friendSelect.innerHTML = state.friends.map(f => `<option value="${f.id}">${f.name}</option>`).join('');
  }

  document.getElementById('settle-up-modal')?.classList.remove('hidden');
}

function openSettleUpForFriend(friendId, amount) {
  openSettleUpModal();
  const select = document.getElementById('settle-friend-select');
  if (select) select.value = friendId;
  const amtInput = document.getElementById('settle-amount');
  if (amtInput) amtInput.value = amount;
}

// --- Submit Handlers ---

async function handleAddFriendSubmit(e) {
  e.preventDefault();
  const name = document.getElementById('friend-name-input').value.trim();
  const email = document.getElementById('friend-email-input').value.trim() || null;
  const phone = document.getElementById('friend-phone-input').value.trim() || null;

  if (!name) return;

  try {
    const friend = await API.createFriend({ name, email, phone });
    showToast(`Added friend ${friend.name}!`, 'success');
    document.getElementById('add-friend-form').reset();
    document.getElementById('add-friend-modal')?.classList.add('hidden');
    await loadSplitsView();
  } catch (err) {
    showToast('Failed to add friend: ' + err.message, 'error');
  }
}

async function handleDeleteFriend(friendId) {
  if (!confirm('Are you sure you want to delete this friend? This will also remove associated split records.')) return;

  try {
    await API.deleteFriend(friendId);
    showToast('Friend deleted.', 'success');
    await loadSplitsView();
  } catch (err) {
    showToast('Failed to delete friend: ' + err.message, 'error');
  }
}

async function handleAddSplitSubmit(e) {
  e.preventDefault();
  const title = document.getElementById('split-title').value.trim();
  const totalAmount = parseFloat(document.getElementById('split-total-amount').value);
  const paidByVal = document.getElementById('split-paid-by').value;
  const dateVal = document.getElementById('split-date').value || new Date().toISOString().slice(0, 10);
  const notes = document.getElementById('split-notes').value.trim() || null;

  const logPersonal = document.getElementById('split-log-personal').checked;
  const categoryId = logPersonal ? parseInt(document.getElementById('split-category-select').value) : null;

  if (!title || isNaN(totalAmount) || totalAmount <= 0) {
    showToast('Please enter a valid title and total amount.', 'error');
    return;
  }

  const selectedCBs = Array.from(document.querySelectorAll('.split-part-cb:checked'));
  if (selectedCBs.length === 0) {
    showToast('Select at least one participant.', 'error');
    return;
  }

  const paid_by_user = paidByVal === 'user';
  const paid_by_friend_id = paid_by_user ? null : parseInt(paidByVal);

  const participants = selectedCBs.map(cb => {
    if (cb.value === 'user') {
      return { is_user: true, friend_id: null };
    } else {
      return { is_user: false, friend_id: parseInt(cb.value) };
    }
  });

  try {
    await API.createSplit({
      title,
      total_amount: totalAmount,
      transaction_type: 'EXPENSE',
      paid_by_user,
      paid_by_friend_id,
      date: dateVal,
      notes,
      participants,
      log_as_personal_expense: logPersonal,
      category_id: categoryId
    });

    showToast('Shared expense saved!', 'success');
    document.getElementById('add-split-form').reset();
    document.getElementById('add-split-modal')?.classList.add('hidden');
    await loadSplitsView();
  } catch (err) {
    showToast('Failed to save shared bill: ' + err.message, 'error');
  }
}

async function handleDeleteSplit(splitId) {
  if (!confirm('Are you sure you want to delete this split record?')) return;

  try {
    await API.deleteSplit(splitId);
    showToast('Split record deleted.', 'success');
    await loadSplitsView();
  } catch (err) {
    showToast('Failed to delete split record: ' + err.message, 'error');
  }
}

async function handleDirectLoanSubmit(e) {
  e.preventDefault();
  const friendId = parseInt(document.getElementById('loan-friend-select').value);
  const direction = document.getElementById('loan-direction').value;
  const amount = parseFloat(document.getElementById('loan-amount').value);
  const note = document.getElementById('loan-note').value.trim() || 'Direct loan transfer';

  if (isNaN(amount) || amount <= 0) {
    showToast('Please enter a valid loan amount.', 'error');
    return;
  }

  const friend = state.friends.find(f => f.id === friendId);
  const friendName = friend ? friend.name : 'Friend';

  let paid_by_user = true;
  let paid_by_friend_id = null;
  let participants = [];

  if (direction === 'gave') {
    // User gave money to Friend
    paid_by_user = true;
    paid_by_friend_id = null;
    participants = [{ is_user: false, friend_id: friendId, share_amount: amount }];
  } else {
    // Friend gave money to User
    paid_by_user = false;
    paid_by_friend_id = friendId;
    participants = [{ is_user: true, friend_id: null, share_amount: amount }];
  }

  try {
    await API.createSplit({
      title: direction === 'gave' ? `Money lent to ${friendName}` : `Money borrowed from ${friendName}`,
      total_amount: amount,
      transaction_type: 'DIRECT_LOAN',
      paid_by_user,
      paid_by_friend_id,
      date: new Date().toISOString().slice(0, 10),
      notes: note,
      participants
    });

    showToast('Direct loan record saved!', 'success');
    document.getElementById('direct-loan-form').reset();
    document.getElementById('direct-loan-modal')?.classList.add('hidden');
    await loadSplitsView();
  } catch (err) {
    showToast('Failed to save loan record: ' + err.message, 'error');
  }
}

async function handleSettleUpSubmit(e) {
  e.preventDefault();
  const friendId = parseInt(document.getElementById('settle-friend-select').value);
  const amount = parseFloat(document.getElementById('settle-amount').value);
  const notes = document.getElementById('settle-notes').value.trim() || 'Settled up';

  if (isNaN(amount) || amount <= 0) {
    showToast('Please enter a valid settlement amount.', 'error');
    return;
  }

  try {
    await API.settleUp({ friend_id: friendId, amount, notes });
    showToast('Settlement recorded!', 'success');
    document.getElementById('settle-up-form').reset();
    document.getElementById('settle-up-modal')?.classList.add('hidden');
    await loadSplitsView();
  } catch (err) {
    showToast('Failed to record settlement: ' + err.message, 'error');
  }
}
