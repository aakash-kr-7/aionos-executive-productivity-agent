/**
 * AIONOS Executive OS — Frontend Client Application
 * Grounded action intelligence for Arjun Malhotra (VP Sales)
 * 
 * Answers the core executive question: "What do I need to know and do right now?"
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
    case 'my_action': return 'ACTION I OWE';
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
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const dayName = days[d.getDay()];
  const day = d.getDate();
  const month = d.toLocaleString('en-US', { month: 'short' });
  const year = d.getFullYear();
  return `${dayName}, ${day} ${month} ${year}`;
}

// Data loading
async function loadAll() {
  const dateDisplay = $('#activeDateDisplay');
  if (dateDisplay) {
    dateDisplay.textContent = formatDateDisplay(state.activeDate);
  }

  // Update date pills active state
  $$('.date-pill').forEach(pill => {
    if (pill.dataset.date === state.activeDate) {
      pill.classList.add('active');
    } else {
      pill.classList.remove('active');
    }
  });

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

    renderExecutiveBrief();
    renderMetrics();
    renderFilterCounts();
    renderActionQueues();
    renderMeetings();
    renderTimeline();
    renderPipelineTrace();
    renderEvidenceMatrix();
    renderAudit();
  } catch (err) {
    console.error('Failed to load application data:', err);
  }
}

// 1. Executive Brief & Urgent Alert
function renderExecutiveBrief() {
  const summaryEl = $('#executiveSummary');
  if (summaryEl && state.brief) {
    summaryEl.textContent = state.brief.executive_summary || 'All commitments are on schedule with no urgent blockers.';
  }

  const alertBox = $('#urgentAlertBox');
  if (alertBox && state.brief) {
    const overdue = state.brief.commitments.filter(c => c.status === 'overdue');
    if (overdue.length > 0) {
      alertBox.style.display = 'flex';
      const itemsStr = overdue.map(c => `<strong>${esc(c.subject)}</strong> (${esc(c.owner_display || 'Unassigned')})`).join(', ');
      alertBox.innerHTML = `<span>&#9888;&#65039; <strong>CRITICAL DEADLINE ALERT:</strong> ${overdue.length} commitment(s) are overdue as of ${formatDateDisplay(state.activeDate)}: ${itemsStr}. Immediate follow-up required.</span>`;
    } else {
      alertBox.style.display = 'none';
    }
  }
}

// 2. Metrics Ribbon (6 KPI Tiles)
function renderMetrics() {
  const m = state.brief.metrics;
  const metricsContainer = $('#metricsRibbon');
  if (!metricsContainer) return;

  metricsContainer.innerHTML = `
    <div class="metric-tile">
      <div class="metric-value" style="color: var(--accent-cyan);">${m.my_actions}</div>
      <div class="metric-label">MY ACTIONS</div>
    </div>
    <div class="metric-tile">
      <div class="metric-value" style="color: #a78bfa;">${m.waiting_on_others}</div>
      <div class="metric-label">WAITING ON OTHERS</div>
    </div>
    <div class="metric-tile">
      <div class="metric-value" style="color: #fbbf24;">${m.unclear_ownership}</div>
      <div class="metric-label">UNCLEAR OWNERSHIP</div>
    </div>
    <div class="metric-tile">
      <div class="metric-value" style="color: var(--status-due-today);">${m.due_today}</div>
      <div class="metric-label">DUE TODAY</div>
    </div>
    <div class="metric-tile">
      <div class="metric-value" style="color: var(--status-overdue);">${m.overdue}</div>
      <div class="metric-label">OVERDUE / URGENT</div>
    </div>
    <div class="metric-tile">
      <div class="metric-value" style="color: var(--status-completed);">${m.completed}</div>
      <div class="metric-label">COMPLETED</div>
    </div>
  `;
}

// 3. Filter Counts
function renderFilterCounts() {
  const cs = state.brief.commitments;
  const countAll = $('#countAll');
  const countMyActions = $('#countMyActions');
  const countWaiting = $('#countWaiting');
  const countUnclear = $('#countUnclear');
  const countCompleted = $('#countCompleted');

  if (countAll) countAll.textContent = cs.length;
  if (countMyActions) countMyActions.textContent = cs.filter(c => c.action_type === 'my_action' && c.status !== 'completed').length;
  if (countWaiting) countWaiting.textContent = cs.filter(c => c.action_type === 'waiting_on_other' && c.status !== 'completed').length;
  if (countUnclear) countUnclear.textContent = cs.filter(c => c.action_type === 'unclear_ownership').length;
  if (countCompleted) countCompleted.textContent = cs.filter(c => c.status === 'completed').length;
}

// 4. Sectional Action Queues
function renderActionQueues() {
  const container = $('#actionQueues');
  if (!container || !state.brief) return;

  const cs = state.brief.commitments;

  // Split into 4 logical executive buckets
  const myActions = cs.filter(c => c.action_type === 'my_action' && c.status !== 'completed');
  const waitingOnOthers = cs.filter(c => c.action_type === 'waiting_on_other' && c.status !== 'completed');
  const unclearOwnership = cs.filter(c => c.action_type === 'unclear_ownership');
  const completed = cs.filter(c => c.status === 'completed');

  let html = '';

  if (state.activeFilter === 'all' || state.activeFilter === 'my_action') {
    html += renderQueueSection('⚡ MY ACTIONS &amp; COMMITMENTS I OWE', myActions, 'my_action', 'Direct actions required from Arjun Malhotra');
  }

  if (state.activeFilter === 'all' || state.activeFilter === 'waiting_on_other') {
    html += renderQueueSection('⏳ WAITING ON OTHERS (DEPENDENCIES)', waitingOnOthers, 'waiting_on_other', 'Deliverables owed to Arjun by colleagues');
  }

  if (state.activeFilter === 'all' || state.activeFilter === 'unclear_ownership') {
    html += renderQueueSection('⚠️ OWNERSHIP AMBIGUITIES &amp; UNRESOLVED', unclearOwnership, 'unclear_ownership', 'Action items where ownership is contested or unassigned — system strictly refuses to invent an owner');
  }

  if (state.activeFilter === 'all' || state.activeFilter === 'completed') {
    html += renderQueueSection('✅ RECENTLY COMPLETED COMMITMENTS', completed, 'completed', 'Verified finished deliverables during the exercise week');
  }

  if (!html.trim()) {
    html = `
      <div style="background: var(--bg-panel); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 36px; text-align: center; color: var(--text-muted);">
        No commitments match the active filter (<strong>${esc(state.activeFilter)}</strong>) as of ${formatDateDisplay(state.activeDate)}.
      </div>
    `;
  }

  container.innerHTML = html;

  // Bind drill-down buttons
  container.querySelectorAll('.btn-inspect').forEach(btn => {
    btn.addEventListener('click', () => {
      openDrilldownModal(btn.dataset.id);
    });
  });
}

function renderQueueSection(title, items, typeKey, subtext) {
  if (state.activeFilter === 'all' && items.length === 0 && typeKey !== 'unclear_ownership') {
    return '';
  }

  return `
    <section class="queue-section">
      <div class="queue-section-header">
        <div>
          <div class="queue-section-title">
            <span>${title}</span>
            <span class="queue-count-pill">${items.length}</span>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">${subtext}</div>
        </div>
      </div>
      <div class="action-cards">
        ${items.length === 0 
          ? `<div style="background: var(--bg-panel); border: 1px dashed var(--border-subtle); border-radius: var(--radius-sm); padding: 18px; text-align: center; color: var(--text-muted); font-size: 12px;">No active items in this category as of today.</div>`
          : items.map(c => renderCommitmentCard(c)).join('')
        }
      </div>
    </section>
  `;
}

function renderCommitmentCard(c) {
  const cardClassModifier = c.status === 'overdue' 
    ? 'card-overdue' 
    : (c.status === 'due_today' 
        ? 'card-due-today' 
        : (c.action_type === 'unclear_ownership' ? 'card-ambiguous' : ''));

  const statusBadge = `<span class="badge badge-${c.status}">${formatStatus(c.status)}</span>`;
  const actionTypeBadge = `<span class="badge badge-${c.action_type}">${formatActionType(c.action_type)}</span>`;
  
  let ownershipBadge = '';
  if (c.action_type === 'unclear_ownership') {
    ownershipBadge = `<span class="badge badge-unassigned">OWNERSHIP UNRESOLVED &bull; REFUSED TO GUESS</span>`;
  }

  const ownerDisplay = c.owner_display 
    ? `<strong>${esc(c.owner_display)}</strong>` 
    : `<span style="color:#fde047; font-weight:700;">UNASSIGNED (FLAGGED)</span>`;

  const counterpartyDisplay = c.counterparty 
    ? `<strong>${esc(c.counterparty)}</strong>` 
    : '<span>None / Team</span>';

  const deadlineDisplay = c.deadline_label 
    ? `<strong>${esc(c.deadline_label)}</strong>` 
    : '<span style="color:var(--text-muted);">None specified</span>';

  // Source badges
  const sourceTypes = (c.reconciliation && c.reconciliation.source_types_involved) || 
    [...new Set(c.evidence.map(e => e.source_type))];
  const sourceTagsHtml = sourceTypes.map(st => `<span class="source-tag-item">${st.toUpperCase()}</span>`).join('');

  // Slippage notice
  let slippageHtml = '';
  if (c.deadline_history && c.deadline_history.length > 1) {
    const first = c.deadline_history[0];
    const latest = c.deadline_history[c.deadline_history.length - 1];
    slippageHtml = `
      <div class="slippage-notice">
        <span>&#9201;</span>
        <span><strong>Deadline Slippage Detected:</strong> ${esc(first.new_deadline)} &rarr; ${esc(latest.new_deadline)} (${esc(latest.reason || 'Per subsequent thread')})</span>
      </div>
    `;
  }

  const confPercent = Math.round(c.confidence * 100);

  return `
    <article class="action-card ${cardClassModifier}" data-id="${esc(c.id)}">
      <div class="card-header">
        <div class="card-subject">${esc(c.subject)}</div>
        <div class="card-badges">
          ${ownershipBadge}
          ${actionTypeBadge}
          ${statusBadge}
        </div>
      </div>

      <div class="card-action-text">${esc(c.action)}</div>

      ${slippageHtml}

      <div class="card-meta-line">
        <div class="meta-segment">Owner: ${ownerDisplay}</div>
        <div class="meta-segment">&bull;</div>
        <div class="meta-segment">Counterparty: ${counterpartyDisplay}</div>
        <div class="meta-segment">&bull;</div>
        <div class="meta-segment">Deadline: ${deadlineDisplay}</div>
        <div class="meta-segment">&bull;</div>
        <div class="meta-segment">
          <div class="source-icons-tag">${sourceTagsHtml}</div>
        </div>
      </div>

      <div class="card-footer">
        <div style="display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--text-secondary);">
          <span>Confidence: <strong>${confPercent}%</strong></span>
          <div style="width: 50px; height: 5px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
            <div style="width: ${confPercent}%; height: 100%; background: var(--accent-cyan);"></div>
          </div>
        </div>
        <button class="btn-inspect" data-id="${esc(c.id)}">
          <span>Inspect Evidence &amp; History</span>
          <span>&rarr;</span>
        </button>
      </div>
    </article>
  `;
}

// 5. Drill-down Modal (Defensible Evidence & Lineage)
function openDrilldownModal(commitmentId) {
  const modal = $('#drilldownModal');
  const subjectEl = $('#modalSubject');
  const bodyEl = $('#modalBody');
  if (!modal || !subjectEl || !bodyEl || !state.brief) return;

  const c = state.brief.commitments.find(item => item.id === commitmentId);
  if (!c) return;

  subjectEl.innerHTML = `<span>${esc(c.subject)}</span> <span style="font-size: 12px; color: var(--text-muted); font-weight: 500;">(ID: ${esc(c.id)})</span>`;

  // Evidence quotes
  const evidenceHtml = c.evidence.map(e => `
    <div class="evidence-block">
      <div class="evidence-source-title">${esc(e.source_type.toUpperCase())} &bull; ${esc(e.title)} (${esc(e.date)})</div>
      <div class="evidence-quote-text">&ldquo;${esc(e.excerpt)}&rdquo;</div>
    </div>
  `).join('');

  // Deadline revision history
  let historyHtml = '<div style="color: var(--text-muted); font-size: 12px;">No revisions recorded; single authoritative deadline.</div>';
  if (c.deadline_history && c.deadline_history.length > 0) {
    historyHtml = `
      <div style="display: flex; flex-direction: column; gap: 8px;">
        ${c.deadline_history.map((rev, idx) => `
          <div style="background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 4px; border-left: 2px solid ${idx === c.deadline_history.length - 1 ? 'var(--accent-cyan)' : 'var(--border-subtle)'};">
            <div style="font-size: 12px; font-weight: 700; color: #fff;">Revision ${idx + 1} (${esc(rev.revised_at)}): <strong>${esc(rev.new_deadline)}</strong></div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Source: <code>${esc(rev.source_id)}</code> &bull; Reason: ${esc(rev.reason || 'Stated deliverable requirement')}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  // Classification Rationale
  const rationaleHtml = `
    <ul style="padding-left: 18px; display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #cbd5e1;">
      ${c.rationale.map(r => `<li>${esc(r)}</li>`).join('')}
    </ul>
  `;

  // Pipeline Trace
  const traceHtml = (c.extraction_trace && c.extraction_trace.length > 0) ? `
    <div style="background: #040810; padding: 10px 12px; border-radius: 4px; font-family: var(--font-mono); font-size: 11px; color: #93c5fd; max-height: 140px; overflow-y: auto;">
      ${c.extraction_trace.map(t => `<div>&gt; ${esc(t)}</div>`).join('')}
    </div>
  ` : '<div style="color: var(--text-muted); font-size: 12px;">Standard deterministic extraction pipeline executed.</div>';

  bodyEl.innerHTML = `
    <!-- Summary Header -->
    <div style="background: var(--bg-panel-elevated); padding: 14px 16px; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);">
      <div style="font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 6px;">${esc(c.action)}</div>
      <div style="display: flex; flex-wrap: wrap; gap: 12px; font-size: 11px; color: var(--text-secondary);">
        <div>Status: <span class="badge badge-${c.status}">${formatStatus(c.status)}</span></div>
        <div>Type: <span class="badge badge-${c.action_type}">${formatActionType(c.action_type)}</span></div>
        <div>Owner: <strong>${c.owner_display || '<span style="color:#fde047;">UNASSIGNED (REFUSED TO GUESS)</span>'}</strong></div>
        <div>Counterparty: <strong>${esc(c.counterparty || '—')}</strong></div>
        <div>Current Deadline: <strong>${esc(c.deadline_label || 'None')}</strong></div>
        <div>Confidence: <strong>${Math.round(c.confidence * 100)}%</strong></div>
      </div>
    </div>

    <!-- Section 1: Multi-Source Evidence Quotes -->
    <div class="drilldown-section">
      <div class="drilldown-title">&#128196; MULTI-SOURCE CORROBORATING EVIDENCE (${c.evidence.length} CITATIONS)</div>
      ${evidenceHtml}
    </div>

    <!-- Section 2: Chronological Deadline History & Slippage -->
    <div class="drilldown-section">
      <div class="drilldown-title">&#9201; CHRONOLOGICAL DEADLINE TIMELINE &amp; SLIPPAGE HISTORY</div>
      ${historyHtml}
    </div>

    <!-- Section 3: Deterministic Classification Rationale -->
    <div class="drilldown-section">
      <div class="drilldown-title">&#9881; DETERMINISTIC CLASSIFICATION RATIONALE</div>
      ${rationaleHtml}
    </div>

    <!-- Section 4: Pipeline Extraction Trace -->
    <div class="drilldown-section">
      <div class="drilldown-title">&#128065; STAGE EXECUTION TRACE</div>
      ${traceHtml}
    </div>
  `;

  modal.style.display = 'flex';
}

function closeDrilldownModal() {
  const modal = $('#drilldownModal');
  if (modal) modal.style.display = 'none';
}

// 6. Today's Meetings & Schedule
function renderMeetings() {
  const meetings = state.brief.meetings || [];
  const countTag = $('#meetingCountTag');
  const container = $('#todayMeetingsList');

  if (countTag) {
    countTag.textContent = `${meetings.length} Scheduled`;
  }

  if (!container) return;

  if (meetings.length === 0) {
    container.innerHTML = `
      <div style="background: var(--bg-panel-elevated); padding: 14px; border-radius: var(--radius-sm); text-align: center; color: var(--text-muted); font-size: 12px;">
        No calendar meetings scheduled for ${formatDateDisplay(state.activeDate)}.
      </div>
    `;
    return;
  }

  container.innerHTML = meetings.map(m => `
    <div class="meeting-item ${m.title.toLowerCase().includes('hold') ? 'blocked' : ''}">
      <div class="meeting-time">${esc(m.start)} – ${esc(m.end)}</div>
      <div class="meeting-title">${esc(m.title)}</div>
    </div>
  `).join('');
}

// 7. Timeline & Deadlines Panel
function renderTimeline() {
  const container = $('#timelineContainer');
  if (!container || !state.brief) return;

  const weekDays = [
    { date: '2026-09-21', name: 'Monday, 21 Sep 2026' },
    { date: '2026-09-22', name: 'Tuesday, 22 Sep 2026' },
    { date: '2026-09-23', name: 'Wednesday, 23 Sep 2026' },
    { date: '2026-09-24', name: 'Thursday, 24 Sep 2026' },
    { date: '2026-09-25', name: 'Friday, 25 Sep 2026' },
  ];

  const cs = state.brief.commitments;

  container.innerHTML = weekDays.map(day => {
    const isToday = day.date === state.activeDate;
    const isPast = day.date < state.activeDate;

    // Filter commitments associated with this day
    const dayCommitments = cs.filter(c => {
      if (c.deadline && c.deadline.startsWith(day.date)) return true;
      if (day.date === '2026-09-25' && c.subject.toLowerCase().includes('lease')) return true; // lease is Friday EOD
      return false;
    });

    return `
      <div class="timeline-day-block" style="${isToday ? 'border-color: var(--accent-cyan); background: #0c182c;' : ''}">
        <div class="timeline-day-header" style="display: flex; justify-content: space-between; align-items: center;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span>${esc(day.name)}</span>
            ${isToday ? '<span class="badge" style="background: var(--accent-cyan); color: #06111f; font-weight: 800;">CURRENT AS-OF DATE</span>' : ''}
            ${isPast ? '<span class="badge" style="background: rgba(255,255,255,0.06); color: var(--text-muted);">HISTORICAL</span>' : ''}
          </div>
          <span style="font-size: 11px; color: var(--text-muted);">${dayCommitments.length} key commitment(s)</span>
        </div>

        <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px;">
          ${dayCommitments.length === 0 
            ? `<div style="font-size: 12px; color: var(--text-muted); padding: 6px 0;">No milestone commitments due on this date.</div>` 
            : dayCommitments.map(c => `
              <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.25); padding: 10px 14px; border-radius: var(--radius-sm); border-left: 3px solid ${c.status === 'overdue' ? 'var(--status-overdue)' : (c.status === 'completed' ? 'var(--status-completed)' : 'var(--accent-cyan)')};">
                <div>
                  <div style="font-weight: 700; color: #fff; font-size: 13px;">${esc(c.subject)}</div>
                  <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">${esc(c.action)}</div>
                  <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Owner: <strong>${c.owner_display || 'Unassigned'}</strong> &bull; Deadline: <strong>${esc(c.deadline_label || 'Unspecified')}</strong></div>
                </div>
                <div style="display: flex; gap: 6px;">
                  <span class="badge badge-${c.status}">${formatStatus(c.status)}</span>
                  <button class="btn-inspect" data-id="${esc(c.id)}">Details</button>
                </div>
              </div>
            `).join('')
          }
        </div>
      </div>
    `;
  }).join('');

  // Bind inspect buttons inside timeline
  container.querySelectorAll('.btn-inspect').forEach(btn => {
    btn.addEventListener('click', () => {
      openDrilldownModal(btn.dataset.id);
    });
  });
}

// 8. 8-Stage Pipeline Inspector
function renderPipelineTrace() {
  if (!state.trace) return;

  const statSig = $('#statSignals');
  const statCand = $('#statCandidates');
  const statGrp = $('#statGroups');
  const pre = $('#pipelineTracePre');

  if (statSig) statSig.textContent = `${state.trace.signal_count} Signals Normalized`;
  if (statCand) statCand.textContent = `${state.trace.candidate_count} Candidates Extracted`;
  if (statGrp) statGrp.textContent = `${state.trace.reconciled_count} Groups Reconciled`;

  if (pre) {
    pre.textContent = JSON.stringify(state.trace, null, 2);
  }
}

// 9. Source Evidence Matrix
function renderEvidenceMatrix() {
  if (!state.sources || !state.brief) return;

  const s = state.sources;
  const grid = $('#sourcesSummaryGrid');
  const list = $('#evidenceMatrixList');

  if (grid) {
    grid.innerHTML = `
      <div class="metric-tile">
        <div class="metric-value">${s.email_threads}</div>
        <div class="metric-label">EMAIL THREADS</div>
      </div>
      <div class="metric-tile">
        <div class="metric-value">${s.voice_notes}</div>
        <div class="metric-label">VOICE MEMOS</div>
      </div>
      <div class="metric-tile">
        <div class="metric-value">${s.calendar_people}</div>
        <div class="metric-label">CALENDARS INDEXED</div>
      </div>
      <div class="metric-tile">
        <div class="metric-value">${s.people.length}</div>
        <div class="metric-label">CANONICAL DIRECTORY</div>
      </div>
    `;
  }

  if (list) {
    list.innerHTML = state.brief.commitments.map(c => `
      <div class="matrix-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <h3 style="color: #fff; font-size: 15px; font-weight: 800;">${esc(c.subject)}</h3>
          <div style="display: flex; gap: 6px;">
            <span class="badge badge-${c.action_type}">${formatActionType(c.action_type)}</span>
            <span class="badge badge-${c.status}">${formatStatus(c.status)}</span>
          </div>
        </div>

        <div style="font-size: 13px; color: #e2e8f0; margin-bottom: 12px;"><strong>Canonical action:</strong> ${esc(c.action)}</div>

        <div style="display: flex; flex-direction: column; gap: 8px;">
          ${c.evidence.map(e => `
            <div class="evidence-block">
              <div class="evidence-source-title">${esc(e.source_type.toUpperCase())} &bull; ${esc(e.title)} (${esc(e.date)})</div>
              <div class="evidence-quote-text">&ldquo;${esc(e.excerpt)}&rdquo;</div>
            </div>
          `).join('')}
        </div>
      </div>
    `).join('');
  }
}

// 10. Audit Trail Panel
function renderAudit() {
  if (!state.audit) return;
  const list = $('#auditLogList');
  if (!list) return;

  const events = state.audit.events || [];
  if (events.length === 0) {
    list.innerHTML = `
      <div style="background: var(--bg-panel); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 28px; text-align: center; color: var(--text-muted); font-size: 13px;">
        No grounded queries logged yet. Use the "Ask the Agent" console to record an auditable interaction.
      </div>
    `;
    return;
  }

  list.innerHTML = events.map(ev => `
    <div class="audit-entry">
      <div style="display: flex; justify-content: space-between; color: var(--accent-cyan); font-weight: 700; margin-bottom: 4px;">
        <span>AUDIT ID: ${esc(ev.id)}</span>
        <span>AS-OF: ${esc(ev.as_of)}</span>
      </div>
      <div style="color: #fff; font-weight: 600; margin-bottom: 4px;">Question: &ldquo;${esc(ev.question)}&rdquo;</div>
      <div style="color: var(--text-secondary); font-size: 11px;">
        Intent Type: <code>${esc(ev.type)}</code> &bull; Matched Commitment IDs: [${esc((ev.matched_commitments || []).join(', ') || 'None')}]
      </div>
    </div>
  `).reverse().join('');
}

// 11. Grounded Q&A Assistant Execution
async function askQuestion(queryText) {
  const input = $('#qaInput');
  if (queryText) {
    input.value = queryText;
  }
  const q = input.value.trim();
  if (!q) return;

  const resultBox = $('#qaResponseBox');
  if (!resultBox) return;

  resultBox.style.display = 'block';
  resultBox.innerHTML = `<div style="color: var(--accent-cyan); font-weight: 600; font-size: 13px;">Consulting deterministic evidence graph as of ${state.activeDate}…</div>`;

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

    let evidenceHtml = '';
    if (data.evidence && data.evidence.length > 0) {
      evidenceHtml = `
        <details style="margin-top: 10px; cursor: pointer;">
          <summary style="font-size: 11px; font-weight: 700; color: var(--accent-cyan);">View Grounded Source Evidence (${data.evidence.length} Citations) &bull; Audit ID: ${esc(data.audit_id)}</summary>
          <div style="margin-top: 8px; display: flex; flex-direction: column; gap: 6px;">
            ${data.evidence.map(e => `
              <div class="evidence-block">
                <div class="evidence-source-title">${esc(e.title)} (${esc(e.date)})</div>
                <div class="evidence-quote-text">&ldquo;${esc(e.excerpt)}&rdquo;</div>
              </div>
            `).join('')}
          </div>
        </details>
      `;
    }

    resultBox.innerHTML = `
      <div class="qa-answer-text">${esc(data.answer)}</div>
      <div class="qa-scope-text">${esc(interpretationText)}</div>
      ${evidenceHtml}
    `;

    // Refresh audit trail
    const auditRes = await fetch('/api/audit');
    state.audit = await auditRes.json();
    renderAudit();
  } catch (err) {
    resultBox.innerHTML = `<div style="color: var(--status-overdue); font-size: 13px;">Error querying agent: ${esc(err.message)}</div>`;
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
      const targetPanel = $(`#${panelId}`);
      if (targetPanel) targetPanel.classList.add('active');
    });
  });

  // Date Navigator Pills
  $$('.date-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      state.activeDate = pill.dataset.date;
      loadAll();
    });
  });

  // Filter Tabs
  $$('.filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      $$('.filter-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.activeFilter = tab.dataset.filter;
      renderActionQueues();
    });
  });

  // Fast Query Chips
  $$('.chip-btn').forEach(chip => {
    chip.addEventListener('click', () => {
      askQuestion(chip.dataset.query);
    });
  });

  // Ask Button & Enter Key in QA input
  const submitBtn = $('#qaSubmitBtn');
  const qaInput = $('#qaInput');
  if (submitBtn) {
    submitBtn.addEventListener('click', () => askQuestion());
  }
  if (qaInput) {
    qaInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        askQuestion();
      }
    });
  }

  // Trace Refresh Button
  const refreshTraceBtn = $('#refreshTraceBtn');
  if (refreshTraceBtn) {
    refreshTraceBtn.addEventListener('click', async () => {
      const traceRes = await fetch(`/api/pipeline-trace?date=${state.activeDate}`);
      state.trace = await traceRes.json();
      renderPipelineTrace();
    });
  }

  // Modal Close Button & Backdrop Click
  const closeBtn = $('#modalCloseBtn');
  const modal = $('#drilldownModal');
  if (closeBtn) {
    closeBtn.addEventListener('click', closeDrilldownModal);
  }
  if (modal) {
    modal.addEventListener('click', e => {
      if (e.target === modal) {
        closeDrilldownModal();
      }
    });
  }

  // Escape key to close modal
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeDrilldownModal();
    }
  });
}

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
  setupEvents();
  loadAll();
});
