// API client for the PO Reconciliation backend
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchSummary() {
  const res = await fetch(`${BASE}/summary`);
  if (!res.ok) throw new Error(`Summary fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchPOs(filter = null, search = '') {
  const params = new URLSearchParams();
  if (filter) params.set('status', filter);
  if (search) params.set('vendor', search);
  const url = `${BASE}/pos${params.toString() ? '?' + params : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`POs fetch failed: ${res.status}`);
  return res.json();
}

export async function sendChat(question) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Chat failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchDuplicateInvoices() {
  const res = await fetch(`${BASE}/duplicate-invoices`);
  if (!res.ok) throw new Error(`Duplicate invoices fetch failed: ${res.status}`);
  return res.json();
}
