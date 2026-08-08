/**
 * API Wrapper for Smart Expense Tracker Backend with Automatic Retry & Safe Error Handling
 */
const API_BASE = '/api';

async function fetchWithRetry(url, options = {}, retries = 4, delay = 2500) {
  for (let attempt = 0; attempt < retries; attempt++) {
    try {
      const res = await fetch(url, options);
      // Retry on transient Render startup status codes: 404 (route warming), 500, 502, 503, 504
      if ((res.status >= 500 || res.status === 404 || res.status === 502 || res.status === 503) && attempt < retries - 1) {
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      return res;
    } catch (err) {
      if (attempt < retries - 1) {
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        throw err;
      }
    }
  }
}

async function handleResponse(res, fallbackMsg) {
  if (res.ok) {
    if (res.status === 204) return true;
    return await res.json();
  }
  let detailMsg = fallbackMsg;
  try {
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const errData = await res.json();
      detailMsg = errData.detail || errData.message || fallbackMsg;
    } else {
      const rawText = await res.text();
      detailMsg = rawText.trim() || fallbackMsg;
    }
  } catch (_) {
    detailMsg = fallbackMsg;
  }
  throw new Error(detailMsg);
}

const API = {
  async getCategories() {
    const res = await fetchWithRetry(`${API_BASE}/categories`);
    return await handleResponse(res, 'Failed to load categories');
  },

  async createCategory(categoryData) {
    const res = await fetchWithRetry(`${API_BASE}/categories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(categoryData)
    });
    return await handleResponse(res, 'Failed to create category');
  },

  async getExpenses(month = null, categoryId = null, search = null) {
    const params = new URLSearchParams();
    if (month) params.append('month', month);
    if (categoryId) params.append('category_id', categoryId);
    if (search) params.append('search', search);

    const res = await fetchWithRetry(`${API_BASE}/expenses?${params.toString()}`);
    return await handleResponse(res, 'Failed to load expenses');
  },

  async createExpense(expenseData) {
    const res = await fetchWithRetry(`${API_BASE}/expenses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(expenseData)
    });
    return await handleResponse(res, 'Failed to add expense');
  },

  async deleteExpense(expenseId) {
    const res = await fetchWithRetry(`${API_BASE}/expenses/${expenseId}`, {
      method: 'DELETE'
    });
    return await handleResponse(res, 'Failed to delete expense');
  },

  async getDashboard(month) {
    const res = await fetchWithRetry(`${API_BASE}/dashboard/${month}`);
    return await handleResponse(res, 'Failed to load dashboard statistics');
  },

  async getMonthlyReport(month, refresh = false) {
    const res = await fetchWithRetry(`${API_BASE}/reports/${month}?refresh=${refresh}`);
    return await handleResponse(res, 'Failed to load monthly AI report');
  },

  async parseExpenseText(text) {
    const res = await fetchWithRetry(`${API_BASE}/ai/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    return await handleResponse(res, 'AI parsing failed');
  }
};
