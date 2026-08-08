/**
 * Chart.js Integration Helper Module for Smart Expense Tracker
 */

let categoryDonutChart = null;
let monthlyBarChart = null;

const CHART_COLORS = [
  '#8b5cf6', '#6366f1', '#10b981', '#f43f5e', '#06b6d4',
  '#f59e0b', '#ec4899', '#3b82f6', '#84cc16', '#a855f7',
  '#14b8a6', '#64748b'
];

function renderCategoryDonutChart(canvasId, categoryData) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  if (categoryDonutChart) {
    categoryDonutChart.destroy();
  }

  const labels = Object.keys(categoryData);
  const dataValues = Object.values(categoryData);

  if (labels.length === 0) {
    // Empty state
    categoryDonutChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['No Expenses'],
        datasets: [{
          data: [1],
          backgroundColor: ['rgba(255, 255, 255, 0.05)'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        }
      }
    });
    return;
  }

  categoryDonutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: dataValues,
        backgroundColor: CHART_COLORS.slice(0, labels.length),
        borderColor: '#111827',
        borderWidth: 3,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#9ca3af',
            font: { family: 'Outfit', size: 12 },
            padding: 14,
            usePointStyle: true,
            pointStyle: 'circle'
          }
        },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#fff',
          bodyColor: '#a78bfa',
          borderColor: 'rgba(139, 92, 246, 0.3)',
          borderWidth: 1,
          padding: 12,
          boxPadding: 6,
          callbacks: {
            label: function (context) {
              const value = context.raw || 0;
              const total = context.chart._metasets[0].total || 1;
              const pct = ((value / total) * 100).toFixed(1);
              return `  ₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}

function renderMonthlyBarChart(canvasId, currentMonthStr, currentTotal, prevTotal) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  if (monthlyBarChart) {
    monthlyBarChart.destroy();
  }

  // Format month labels e.g. "2026-08" -> "Aug 2026"
  const formatMonth = (mStr) => {
    try {
      const [y, m] = mStr.split('-');
      const d = new Date(parseInt(y), parseInt(m) - 1, 1);
      return d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    } catch (e) {
      return mStr;
    }
  };

  // Get previous month string
  const [y, m] = currentMonthStr.split('-').map(Number);
  const prevDate = new Date(y, m - 2, 1);
  const prevMonthStr = `${prevDate.getFullYear()}-${String(prevDate.getMonth() + 1).padStart(2, '0')}`;

  monthlyBarChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: [formatMonth(prevMonthStr), formatMonth(currentMonthStr)],
      datasets: [{
        label: 'Total Spend (₹)',
        data: [prevTotal, currentTotal],
        backgroundColor: [
          'rgba(99, 102, 241, 0.5)',
          'rgba(139, 92, 246, 0.85)'
        ],
        borderColor: [
          '#6366f1',
          '#8b5cf6'
        ],
        borderWidth: 2,
        borderRadius: 8,
        barThickness: 38
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: {
            color: '#9ca3af',
            font: { family: 'Outfit', size: 11 },
            callback: (val) => '₹' + val.toLocaleString('en-IN')
          }
        },
        x: {
          grid: { display: false },
          ticks: { color: '#9ca3af', font: { family: 'Outfit', size: 12, weight: 'bold' } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#fff',
          bodyColor: '#38bdf8',
          borderColor: 'rgba(56, 189, 248, 0.3)',
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (ctx) => ` Total Spend: ₹${ctx.raw.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
          }
        }
      }
    }
  });
}
