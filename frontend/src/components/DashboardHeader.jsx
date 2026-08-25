import { useEffect, useState } from 'react';
import { fetchSummary } from '../api';

function fmt(n) {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD', maximumFractionDigits: 0,
  }).format(n);
}

function StatChip({ dot, label, value, loading }) {
  return (
    <div className="stat-chip">
      <div className={`stat-chip-dot ${dot}`} />
      <span className="stat-chip-label">{label}</span>
      {loading
        ? <div className="skeleton-cell" style={{ width: 48, height: 14 }} />
        : <span className="stat-chip-value">{value}</span>
      }
    </div>
  );
}

export default function DashboardHeader() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSummary()
      .then(setStats)
      .catch(console.error)
      .finally(() => setLoading(false));
    // Refresh every 30s
    const id = setInterval(() => {
      fetchSummary().then(setStats).catch(console.error);
    }, 30000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="dashboard-header">
      <div className="header-brand">
        <div className="header-brand-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
            <rect x="9" y="3" width="6" height="4" rx="1"/>
            <path d="M9 12h6M9 16h4"/>
          </svg>
        </div>
        <div>
          <div className="header-brand-name">PO Reconciliation</div>
          <div className="header-brand-tag">Procurement Intelligence</div>
        </div>
      </div>

      <div className="header-divider" />

      <div className="header-stats">
        <StatChip dot="matched" label="Total POs" value={stats?.total_pos ?? '—'} loading={loading} />
        <StatChip dot="matched" label="Matched" value={stats?.total_matched ?? '—'} loading={loading} />
        <StatChip dot="mismatch" label="Mismatched" value={stats?.total_mismatched ?? '—'} loading={loading} />
        <StatChip dot="missing" label="Missing Receipt" value={stats?.total_missing_receipt ?? '—'} loading={loading} />
        <StatChip dot="value" label="Flagged Value" value={loading ? null : fmt(stats?.flagged_value)} loading={loading} />
        <StatChip dot="value" label="Total Invoiced" value={loading ? null : fmt(stats?.total_invoiced)} loading={loading} />
      </div>

      <div className="header-actions">
        <div className="status-badge">
          <div className="status-badge-dot" />
          Live
        </div>
      </div>
    </header>
  );
}
