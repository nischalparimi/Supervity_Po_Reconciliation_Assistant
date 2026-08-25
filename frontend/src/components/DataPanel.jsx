import { useEffect, useState, useMemo } from 'react';
import { fetchPOs } from '../api';

const FILTERS = [
  { key: null,              label: 'All' },
  { key: 'Matched',         label: 'Matched' },
  { key: 'Amount Mismatch', label: 'Amount Mismatch' },
  { key: 'Quantity Mismatch',label: 'Qty Mismatch' },
  { key: 'Qty & Amount Mismatch', label: 'Qty & Amt' },
  { key: 'Missing Receipt', label: 'Missing' },
];

function fmt(n, opts = {}) {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency', currency: 'USD',
    minimumFractionDigits: 2, maximumFractionDigits: 2,
    ...opts,
  }).format(n);
}

function ReconBadge({ status }) {
  const map = {
    'Matched':               'matched',
    'Amount Mismatch':       'mismatch-amount',
    'Quantity Mismatch':     'mismatch-qty',
    'Qty & Amount Mismatch': 'mismatch-both',
    'Missing Receipt':       'missing',
  };
  const cls = map[status] || 'missing';
  return (
    <span className={`recon-badge ${cls}`}>
      <span className="recon-badge-dot" />
      {status}
    </span>
  );
}

function VarianceCell({ value }) {
  if (value === 0 || value === null) return <span className="variance-zero">—</span>;
  const cls = value > 0 ? 'variance-positive' : 'variance-negative';
  const sign = value > 0 ? '+' : '';
  return <span className={`amount-cell ${cls}`}>{sign}{fmt(value)}</span>;
}

function SkeletonRows({ count = 12 }) {
  return Array.from({ length: count }, (_, i) => (
    <tr key={i} className="skeleton-row">
      {Array.from({ length: 8 }, (_, j) => (
        <td key={j}>
          <div className="skeleton-cell" style={{ width: `${60 + (j * 17) % 60}%` }} />
        </td>
      ))}
    </tr>
  ));
}

function SearchIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5">
      <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
  );
}

export default function DataPanel({ refreshSignal }) {
  const [pos, setPos] = useState([]);
  const [filter, setFilter] = useState(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState('po_number');
  const [sortDir, setSortDir] = useState(1); // 1 = asc, -1 = desc

  const load = () => {
    setLoading(true);
    fetchPOs(filter)
      .then(setPos)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filter, refreshSignal]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return pos
      .filter(p =>
        !q ||
        p.po_number.toLowerCase().includes(q) ||
        p.vendor.toLowerCase().includes(q) ||
        p.po_item?.toLowerCase().includes(q)
      )
      .sort((a, b) => {
        const av = a[sortKey];
        const bv = b[sortKey];
        if (av === bv) return 0;
        return av < bv ? -sortDir : sortDir;
      });
  }, [pos, search, sortKey, sortDir]);

  function handleSort(key) {
    if (key === sortKey) setSortDir(d => -d);
    else { setSortKey(key); setSortDir(1); }
  }

  function SortIndicator({ col }) {
    if (col !== sortKey) return <span style={{ color: 'var(--border-strong)', marginLeft: 2 }}>↕</span>;
    return <span style={{ color: 'var(--teal-400)', marginLeft: 2 }}>{sortDir === 1 ? '↑' : '↓'}</span>;
  }

  return (
    <main className="data-panel">
      <div className="data-panel-header">
        <span className="data-panel-title">PO Reconciliation</span>

        <div className="data-filter-tabs">
          {FILTERS.map(f => (
            <button
              key={String(f.key)}
              className={`filter-tab ${filter === f.key ? 'active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="data-search">
          <SearchIcon />
          <input
            className="data-search-input"
            placeholder="Search PO, vendor, item…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {[
                { key: 'po_number', label: 'PO Number' },
                { key: 'vendor', label: 'Vendor' },
                { key: 'po_item', label: 'Item' },
                { key: 'quantity_ordered', label: 'Qty Ord.' },
                { key: 'total_qty_received', label: 'Qty Rec.' },
                { key: 'po_total_value', label: 'PO Value' },
                { key: 'total_invoiced', label: 'Invoiced' },
                { key: 'invoice_variance', label: 'Variance' },
                { key: 'reconciliation_status', label: 'Status' },
              ].map(({ key, label }) => (
                <th key={key} onClick={() => handleSort(key)}>
                  {label}<SortIndicator col={key} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <SkeletonRows />
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: 40, color: 'var(--text-tertiary)' }}>
                  No purchase orders match the current filter.
                </td>
              </tr>
            ) : (
              filtered.map(row => (
                <tr key={row.po_number}>
                  <td className="po-num">{row.po_number}</td>
                  <td className="vendor-name" title={row.vendor}>{row.vendor}</td>
                  <td style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis' }}
                    title={row.po_item}>{row.po_item}</td>
                  <td>{row.quantity_ordered}</td>
                  <td>
                    {row.total_qty_received}
                    {row.qty_shortfall !== 0 && row.qty_shortfall !== null && (
                      <span style={{ marginLeft: 4, fontSize: 11, color: 'var(--amber-400)' }}>
                        ({row.qty_shortfall > 0 ? '-' : '+'}{Math.abs(row.qty_shortfall)})
                      </span>
                    )}
                  </td>
                  <td className="amount-cell">{fmt(row.po_total_value)}</td>
                  <td className="amount-cell">{row.total_invoiced ? fmt(row.total_invoiced) : '—'}</td>
                  <td><VarianceCell value={row.invoice_variance} /></td>
                  <td><ReconBadge status={row.reconciliation_status} /></td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
