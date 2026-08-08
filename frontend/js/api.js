/**
 * API Wrapper for Smart Expense Tracker Backend
 */
const API_BASE = '/api';

const API = {
  async getCategories() {
    const res = await fetch(`${API_BASE}/categories`);
    if (!res.ok) throw new Error('Failed to load categories');
    return await res.json();
  },

  async createCategory(categoryData) {
    const res = await fetch(`${API_BASE}/categories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(categoryData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create category');
    }
    return await res.json();
  },

  async getExpenses(month = null, categoryId = null, search = null) {
    const params = new URLSearchParams();
    if (month) params.append('month', month);
    if (categoryId) params.append('category_id', categoryId);
    if (search) params.append('search', search);

    const res = await fetch(`${API_BASE}/expenses?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to load expenses');
    return await res.json();
  },

  async createExpense(expenseData) {
    const res = await fetch(`${API_BASE}/expenses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(expenseData)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to add expense');
    }
    return await res.json();
  },

  async deleteExpense(expenseId) {
    const res = await fetch(`${API_BASE}/expenses/${expenseId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to delete expense');
    return true;
  },

  async getDashboard(month) {
    const res = await fetch(`${API_BASE}/dashboard/${month}`);
    if (!res.ok) throw new Error('Failed to load dashboard statistics');
    return await res.json();
  },

  async getMonthlyReport(month, refresh = false) {
    const res = await fetch(`${API_BASE}/reports/${month}?refresh=${refresh}`);
    if (!res.ok) throw new Error('Failed to load monthly AI report');
    return await res.json();
  },

  async parseExpenseText(text) {
    const res = await fetch(`${API_BASE}/ai/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'AI parsing failed');
    }
    return await res.json();
  }
};
