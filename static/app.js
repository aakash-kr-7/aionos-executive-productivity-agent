/**
 * AIONOS Executive OS — Frontend Client Application
 * Grounded action intelligence for Arjun Malhotra
 */

// Utility functions
const $ = selector => document.querySelector(selector);
const $$ = selector => document.querySelectorAll(selector);

const esc = str => {
  if (str === null || str === undefined) return '';
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  }[m]));
};

// Application state
const state = {
  activeDate: '2026-09-23',
  activeFilter: 'all',
  brief: null,
  sources: null,
  trace: null,
  audit: null,
};

// Formatting helpers
function formatActionType(type) {
  switch (type) {
    case 'my_action': return 'EXECUTIVE ACTION';
    case 'waiting_on_other': return 'WAITING ON OTHER';
    case 'unclear_ownership': return 'UNCLEAR OWNERSHIP';
    default: return type.replace(/_/g, ' ').toUpperCase();
  }
}

function formatStatus(status) {
  switch (status) {
    case 'due_today': return 'DUE TODAY';
    case 'overdue': return 'OVERDUE';
    case 'upcoming': return 'UPCOMING';
    case 'completed': return 'COMPLETED';
    case 'ambiguous': return 'AMBIGUOUS';
    default: return status.toUpperCase();
  }
}

function formatDateDisplay(isoDate) {
  const d = new Date(isoDate + 'T00:00:00');
  const day = d.getDate();
  const month = d.toLocaleString('en-US', { month: 'short' });
  const year = d.getFullYear();
  return `${day} ${month} ${year}`;
}

// Data loading
async function loadAll() {
  $('#activeDateDisplay').textContent = formatDateDisplay(state.activeDate);
  try {
    const [briefRes, sourcesRes, traceRes, auditRes] = await Promise.all([
      fetch(`/api/brief?date=${state.activeDate}`),
      fetch('/api/sources'),
      fetch(`/api/pipeline-trace?date=${state.activeDate}`),
      fetch('/api/audit'),
    ]);

    state.brief = await briefRes.json();
    state.sources = await sourcesRes.json();
    state.trace = await traceRes.json();
    state.audit = await auditRes.json();

    renderMetrics();
    renderCards();
    renderCommitments();
    renderPipelineTrace();
    renderSources();
    renderAudit();
  } catch (err) {
    console.error('Failed to load application data:', err);
  }
}

// 1. Render Metrics Ribbon
function renderMetrics() {
  const m = state.brief.metrics;
  const metricsContainer = $('#metrics');
  
  metricsContainer.innerHTML = `
    <div class="metric-card">
      <div class="metric-num" style="color: #60a5fa;">${m.my_actions}</div>
      <div class="metric-label">MY ACTIONS</div>
    </div>
    <div class="metric-card">
      <div class="metric-num" style="color: #a78bfa;">${m.waiting_on_others}</div>
      <div class="metric-label">WAITING ON OTHERS</div>
    </div>
    <div class="metric-card">
      <div class="metric-num" style="color: #fbbf24;">${m.unclear_ownership}</div>
      <div class="metric-label">UNCLEAR OWNERSHIP</div>
    </div>
    <div class="metric-card">
      <div class="metric-num" style="color: #34d399;">${m.completed}</div>
      <div class="metric-label">COMPLETED</div>
    </div>
    <div class="metric-card">
      <div class="metric-num" style="color: #f87171;">${m.overdue}</div>
      <div class="metric-label">OVERDUE / URGENT</div>
    </div>
  `;
}

// 2. Render Commitment Cards with Filters
function renderCards() {
  const cardsContainer = $('#cards');
  let commitments = state.brief.commitments;

  if (state.activeFilter === 'my_action') {
    commitments = commitments.filter(c => c.action_type === 'my_action');
  } else if (state.activeFilter === 'waiting_on_other') {
    commitments = commitments.filter(c => c.action_type === 'waiting_on_other');
  } else if (state.activeFilter === 'unclear_ownership') {
    commitments = commitments.filter(c => c.action_type === 'unclear_ownership');
  } else if (state.activeFilter === 'overdue') {
    commitments = commitments.filter(c => c.status === 'overdue' || c.status === 'due_today');
  }

  $('#cardCount').textContent = `${commitments.length} items`;

  if (!commitments.length) {
    cardsContainer.innerHTML = `
      <div class="commitment-card" style="text-align: center; color: var(--text-muted); padding: 36px;">
        No commitments match the current filter (${state.activeFilter}) as of ${state.activeDate}.
      </div>
    `;
    return;
  }

  cardsContainer.innerHTML = commitments.map(c => {
    const actionBadgeClass = `badge-${c.action_type}`;
    const statusBadgeClass = `badge-${c.status}`;
    const confPercent = Math.round(c.confidence * 100);
    const ownerText = c.owner_display ? esc(c.owner_display) : '<span style="color:#fcd34d;">UNASSIGNED (FLAGGED)</span>';
    const counterpartyText = c.counterparty ? esc(c.counterparty) : '—';
    const deadlineText = c.deadline_label ? esc(c.deadline_label) : '<span class="text-muted">None specified</span>';

    // Group evidence by source type
    const sourceTypes = c.reconciliation ? c.reconciliation.source_types_involved : [];
    const sourceBadges = sourceTypes.map(st => `<span class="badge" style="background: rgba(255,255,255,0.06); color: #cbd5e1;">${st.toUpperCase()}</span>`).join(' ');

    // Deadline History
    const hasSlippage = c.deadline_history && c.deadline_history.length > 1;
    let slippageHtml = '';
    if (c.deadline_history && c.deadline_history.length > 0) {
      slippageHtml = `
        <details>
          <summary>Deadline History &amp; Slippage Tracking (${c.deadline_history.length} revision${c.deadline_history.length > 1 ? 's' : ''})</summary>
          <div class="details-content">
            ${c.deadline_history.map((rev, idx) => `
              <div class="slippage-step">
                <div style="font-weight: 700; color: #fff;">Revision ${idx + 1} (${esc(rev.revised_at)}): <strong>${esc(rev.new_deadline)}</strong></div>
                <div style="color: var(--text-secondary); font-size: 11px;">Source: ${esc(rev.source_id)} &bull; ${esc(rev.reason || 'Stated requirement')}</div>
              </div>
            `).join('')}
          </div>
        </details>
      `;
    }

    // Classification Rationale
    const rationaleHtml = `
      <details>
        <summary>Classification Rationale &amp; Evidence Basis (${c.rationale.length})</summary>
        <div class="details-content">
          <ul class="rationale-list">
            ${c.rationale.map(r => `<li>${esc(r)}</li>`).join('')}
          </ul>
        </div>
      </details>
    `;

    // Trace
    const traceHtml = c.extraction_trace && c.extraction_trace.length > 0 ? `
      <details>
        <summary>Pipeline Extraction Trace (${c.extraction_trace.length} steps)</summary>
        <div class="details-content">
          <ul class="trace-list">
            ${c.extraction_trace.map(t => `<li>&gt; ${esc(t)}</li>`).join('')}
          </ul>
        </div>
      </details>
    ` : '';

    // Evidence
    const evidenceHtml = `
      <details>
        <summary>Corroborating Source Signals (${c.evidence.length})</summary>
        <div class="details-content">
          ${c.evidence.map(e => `
            <div class="evidence-quote">
              <div class="quote-source">${esc(e.source_type.toUpperCase())} &bull; ${esc(e.title)} (${esc(e.date)})</div>
              <div style="color: #cbd5e1; font-size: 12px;">&ldquo;${esc(e.excerpt)}&rdquo;</div>
            </div>
          `).join('')}
        </div>
      </details>
    `;

    return `
      <article class="commitment-card" data-id="${esc(c.id)}">
        <div class="card-top">
          <div>
            <div class="card-subject">${esc(c.subject)}</div>
            <div style="margin-top: 4px; display: flex; gap: 6px;">${sourceBadges}</div>
          </div>
          <div class="card-badges">
            <span class="badge ${actionBadgeClass}">${formatActionType(c.action_type)}</span>
            <span class="badge ${statusBadgeClass}">${formatStatus(c.status)}</span>
          </div>
        </div>

        <div class="card-action">${esc(c.action)}</div>

        <div class="card-meta-row">
          <div class="meta-item">Owner: <strong>${ownerText}</strong></div>
          <div class="meta-item">Counterparty: <strong>${counterpartyText}</strong></div>
          <div class="meta-item">Deadline: <strong>${deadlineText}</strong></div>
          <div class="meta-item confidence-bar-wrap">
            <span>Confidence: <strong>${confPercent}%</strong></span>
            <div class="confidence-bar">
              <div class="confidence-fill" style="width: ${confPercent}%;"></div>
            </div>
          </div>
        </div>

        <div class="card-details">
          ${slippageHtml}
          ${rationaleHtml}
          ${traceHtml}
          ${evidenceHtml}
        </div>
      </article>
    `;
  }).join('');
}

// 3. Render Commitment Graph Table
function renderCommitments() {
  const cs = state.brief.commitments;
  const container = $('#commitmentTable');

  container.innerHTML = `
    <table class="comm-table">
      <thead>
        <tr>
          <th>SUBJECT</th>
          <th>CANONICAL ACTION</th>
          <th>TYPE</th>
          <th>OWNER</th>
          <th>DEADLINE</th>
          <th>STATUS</th>
          <th>CONFIDENCE</th>
        </tr>
      </thead>
      <tbody>
        ${cs.map(c => `
          <tr>
            <td>
              <strong>${esc(c.subject)}</strong><br>
              <span class="text-muted" style="font-size: 11px;">ID: ${esc(c.id)}</span>
            </td>
            <td>${esc(c.action)}</td>
            <td><span class="badge badge-${c.action_type}">${formatActionType(c.action_type)}</span></td>
            <td>${c.owner_display ? esc(c.owner_display) : '<span style="color:#fcd34d;">Unassigned</span>'}</td>
            <td>${esc(c.deadline_label || '—')}</td>
            <td><span class="badge badge-${c.status}">${formatStatus(c.status)}</span></td>
            <td><strong>${Math.round(c.confidence * 100)}%</strong></td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;
}

// 4. Render Pipeline Inspector
function renderPipelineTrace() {
  if (!state.trace) return;
  $('#statSignals').textContent = `${state.trace.signal_count} Signals`;
  $('#statCandidates').textContent = `${state.trace.candidate_count} Candidates`;
  $('#statGroups').textContent = `${state.trace.reconciled_count} Groups`;

  const traceLog = $('#pipelineTraceLog');
  traceLog.textContent = JSON.stringify(state.trace, null, 2);
}

// 5. Render Evidence Registry
function renderSources() {
  if (!state.sources || !state.brief) return;
  const s = state.sources;

  $('#sourceStats').innerHTML = `
    <div class="metric-card">
      <div class="metric-num">${s.email_threads}</div>
      <div class="metric-label">EMAIL THREADS</div>
    </div>
    <div class="metric-card">
      <div class="metric-num">${s.voice_notes}</div>
      <div class="metric-label">VOICE MEMOS</div>
    </div>
    <div class="metric-card">
      <div class="metric-num">${s.calendar_people}</div>
      <div class="metric-label">CALENDARS INDEXED</div>
    </div>
    <div class="metric-card">
      <div class="metric-num">${s.people.length}</div>
      <div class="metric-label">CANONICAL PEOPLE</div>
    </div>
  `;

  $('#evidenceList').innerHTML = state.brief.commitments.map(c => `
    <div class="evidence-group-card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h3 style="color: #fff; font-size: 16px;">${esc(c.subject)}</h3>
        <span class="badge badge-${c.action_type}">${formatActionType(c.action_type)}</span>
      </div>
      <p style="color: var(--text-secondary); font-size: 13px; margin-bottom: 14px;"><strong>Canonical action:</strong> ${esc(c.action)}</p>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${c.evidence.map(e => `
          <div class="evidence-quote">
            <div class="quote-source">${esc(e.source_type.toUpperCase())} &bull; ${esc(e.title)} (${esc(e.date)})</div>
            <div style="color: #cbd5e1; font-size: 12px;">&ldquo;${esc(e.excerpt)}&rdquo;</div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');
}

// 6. Render Audit Trail
function renderAudit() {
  if (!state.audit) return;
  const list = $('#auditList');
  if (!state.audit.events || !state.audit.events.length) {
    list.innerHTML = `
      <div class="audit-event-card" style="color: var(--text-muted); text-align: center;">
        No grounded queries logged yet. Use the Q&A assistant to record an audit trail event.
      </div>
    `;
    return;
  }

  list.innerHTML = state.audit.events.map(ev => `
    <div class="audit-event-card">
      <div class="audit-id">AUDIT EVENT: ${esc(ev.id)} &bull; AS OF ${esc(ev.as_of)}</div>
      <div style="color: #fff; font-weight: 700; margin-bottom: 4px;">&ldquo;${esc(ev.question)}&rdquo;</div>
      <div style="color: var(--text-secondary); font-size: 11px;">
        Type: ${esc(ev.type)} &bull; Matched Commitment IDs: [${esc(ev.matched_commitments.join(', ') || 'none')}]
      </div>
    </div>
  `).reverse().join('');
}

// 7. Grounded Q&A Assistant Execution
async function askQuestion(queryText) {
  const input = $('#questionInput');
  if (queryText) {
    input.value = queryText;
  }
  const q = input.value.trim();
  if (!q) return;

  const resultBox = $('#qaResult');
  resultBox.style.display = 'block';
  resultBox.innerHTML = `<div style="color: var(--accent); font-weight: 600;">Consulting grounded evidence graph as of ${state.activeDate}…</div>`;

  try {
    const res = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, as_of: state.activeDate }),
    });

    const data = await res.json();

    const interpretationText = data.interpretation && data.interpretation.length
      ? `Intent Scopes: ${data.interpretation.join(' • ')}`
      : 'Grounded keyword scan';

    const evidenceHtml = data.evidence && data.evidence.length
      ? `
        <details style="margin-top: 10px;">
          <summary>Grounded Sources (${data.evidence.length}) &bull; Audit ID: ${esc(data.audit_id)}</summary>
          <div class="details-content">
            ${data.evidence.map(e => `
              <div class="evidence-quote">
                <div class="quote-source">${esc(e.title)} (${esc(e.date)})</div>
                <div style="color: #cbd5e1; font-size: 11px;">&ldquo;${esc(e.excerpt)}&rdquo;</div>
              </div>
            `).join('')}
          </div>
        </details>
      `
      : '';

    resultBox.innerHTML = `
      <div class="answer-text">${esc(data.answer)}</div>
      <div class="interpretation-text">${esc(interpretationText)}</div>
      ${evidenceHtml}
    `;

    // Refresh audit trail after query
    const auditRes = await fetch('/api/audit');
    state.audit = await auditRes.json();
    renderAudit();
  } catch (err) {
    resultBox.innerHTML = `<div style="color: var(--status-overdue);">Error querying agent: ${esc(err.message)}</div>`;
  }
}

// Setup Event Listeners
function setupEvents() {
  // Navigation Tabs
  $$('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('.nav-tab').forEach(t => t.classList.remove('active'));
      $$('.panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      const panelId = tab.dataset.tab;
      $(`#${panelId}`).classList.add('active');
    });
  });

  // Date Navigator Pills (Time Travel)
  $$('.date-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      $$('.date-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.activeDate = pill.dataset.date;
      loadAll();
    });
  });

  // Filter Pills
  $$('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      $$('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.activeFilter = pill.dataset.filter;
      renderCards();
    });
  });

  // Preset Query Chips
  $$('.query-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      askQuestion(chip.dataset.q);
    });
  });

  // Ask Button & Enter Key
  $('#askBtn').addEventListener('click', () => askQuestion());
  $('#questionInput').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      askQuestion();
    }
  });

  // Refresh Buttons
  $('#refreshBtn').addEventListener('click', loadAll);
  $('#refreshTraceBtn').addEventListener('click', async () => {
    const traceRes = await fetch(`/api/pipeline-trace?date=${state.activeDate}`);
    state.trace = await traceRes.json();
    renderPipelineTrace();
  });
}

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
  setupEvents();
  loadAll();
});
