import { useState } from 'react';

function ChevronRight({ className }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5" className={className}>
      <path d="M9 18l6-6-6-6"/>
    </svg>
  );
}

function CodeIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.5">
      <polyline points="16 18 22 12 16 6"/>
      <polyline points="8 6 2 12 8 18"/>
    </svg>
  );
}

const MAX_PREVIEW_ROWS = 8;

export default function SqlExpander({ sql, rows, columns, rowCount }) {
  const [open, setOpen] = useState(false);

  if (!sql) {
    return (
      <div className="sql-expander">
        <div className="no-sql-notice">No SQL query was executed for this response.</div>
      </div>
    );
  }

  const previewRows = rows?.slice(0, MAX_PREVIEW_ROWS) ?? [];
  const hasMore = (rows?.length ?? 0) > MAX_PREVIEW_ROWS;
  const displayCols = columns?.slice(0, 8) ?? []; // cap columns for display

  return (
    <div className="sql-expander">
      <button className="sql-expander-toggle" onClick={() => setOpen(o => !o)}>
        <CodeIcon />
        <ChevronRight className={open ? 'open' : ''} />
        <span className="sql-expander-label">Query &amp; Source Rows</span>
        <span className="sql-expander-rows-badge">{rowCount} row{rowCount !== 1 ? 's' : ''}</span>
      </button>

      {open && (
        <div className="sql-expander-body">
          {/* SQL block */}
          <div className="sql-block">
            <div className="sql-block-label">SQL Executed</div>
            <pre className="sql-code">{sql}</pre>
          </div>

          {/* Results block */}
          {previewRows.length > 0 ? (
            <div className="sql-results-block">
              <div className="sql-block-label" style={{ marginBottom: 8 }}>
                Result Set
              </div>
              <div className="sql-results-table-wrap">
                <table className="sql-mini-table">
                  <thead>
                    <tr>
                      {displayCols.map(col => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {previewRows.map((row, i) => (
                      <tr key={i}>
                        {displayCols.map(col => (
                          <td key={col} title={String(row[col] ?? '')}>
                            {row[col] !== null && row[col] !== undefined
                              ? String(row[col])
                              : <span style={{ color: 'var(--text-tertiary)' }}>null</span>
                            }
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {hasMore && (
                <div className="sql-more-rows">
                  … and {rows.length - MAX_PREVIEW_ROWS} more rows
                </div>
              )}
            </div>
          ) : (
            <div className="sql-results-block">
              <div className="sql-block-label">Result Set</div>
              <div className="sql-more-rows">No rows returned.</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
