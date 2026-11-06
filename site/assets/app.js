(() => {
  const fmtPct = p => Number.isFinite(p) ? `${Math.round(p * 100)}%` : '—';
  const fmtGap = p => Number.isFinite(p) ? `${Math.round(p * 100)} pts` : '—';
  const escapeHtml = s => String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const safeUrl = u => /^https:\/\//.test(String(u || '')) ? u : '#';

  let snapshot = null;

  function ageLabel(iso) {
    if (!iso) return '—';
    const sec = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (sec < 90) return 'now';
    if (sec < 3600) return `${Math.round(sec / 60)}m`;
    if (sec < 86400) return `${Math.round(sec / 3600)}h`;
    return `${Math.round(sec / 86400)}d`;
  }

  function renderMetrics(data) {
    const pairs = data.pairs || [];
    const maxGap = pairs.length ? Math.max(...pairs.map(p => p.gap || 0)) : 0;
    document.querySelector('#metric-pairs').textContent = pairs.length.toLocaleString();
    document.querySelector('#metric-max-gap').textContent = fmtGap(maxGap);
    document.querySelector('#metric-markets').textContent = ((data.stats?.kalshi_open || 0) + (data.stats?.polymarket_open || 0)).toLocaleString();
    document.querySelector('#metric-updated').textContent = ageLabel(data.generated_at);
    const sources = data.sources || {};
    const sourceState = [sources.kalshi?.ok ? 'Kalshi ✓' : 'Kalshi !', sources.polymarket?.ok ? 'Polymarket ✓' : 'Polymarket !'].join(' · ');
    document.querySelector('#snapshot-status').textContent = `Snapshot ${ageLabel(data.generated_at)} old · ${sourceState}`;
  }

  function renderPairs() {
    const body = document.querySelector('#pairs-body');
    if (!snapshot) return;
    const minGap = Number(document.querySelector('#min-gap').value || 0);
    const rows = (snapshot.pairs || []).filter(p => (p.gap || 0) >= minGap).sort((a,b) => (b.gap || 0) - (a.gap || 0));
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="5" class="empty-cell">No candidate pairs currently exceed this gap. That is a valid result, not a reason to lower the matching threshold.</td></tr>`;
      return;
    }
    body.innerHTML = rows.slice(0, 50).map(p => `
      <tr>
        <td class="question">
          <strong>${escapeHtml(p.display_question || p.kalshi?.title || p.polymarket?.question)}</strong>
          <small>${escapeHtml(p.note || 'Candidate lexical match; settlement semantics not certified.')}</small>
        </td>
        <td>
          <span class="price">${fmtPct(p.kalshi?.probability)}</span>
          <a class="venue-link" href="${safeUrl(p.kalshi?.url)}" target="_blank" rel="noreferrer">open Kalshi ↗</a>
        </td>
        <td>
          <span class="price">${fmtPct(p.polymarket?.probability)}</span>
          <a class="venue-link" href="${safeUrl(p.polymarket?.url)}" target="_blank" rel="noreferrer">open Polymarket ↗</a>
        </td>
        <td class="gap">${fmtGap(p.gap)}</td>
        <td class="score">${Math.round((p.match_score || 0) * 100)}%</td>
      </tr>`).join('');
  }

  async function boot() {
    try {
      const res = await fetch(`data/latest.json?v=${Date.now()}`, {cache: 'no-store'});
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      snapshot = await res.json();
      renderMetrics(snapshot);
      renderPairs();
    } catch (err) {
      document.querySelector('#snapshot-status').textContent = 'Snapshot unavailable · deployment may still be warming up';
      document.querySelector('#pairs-body').innerHTML = `<tr><td colspan="5" class="empty-cell">No generated snapshot is available yet. The scheduled build will populate this table after GitHub Pages is enabled.</td></tr>`;
      console.error(err);
    }
  }

  document.querySelector('#min-gap').addEventListener('change', renderPairs);
  boot();
})();
