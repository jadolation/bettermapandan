(function (root) {
  'use strict';
  const NB = root.NationalBudget = root.NationalBudget || {};
  const datasets = ['dpwh', 'fmr', 'hfep', 'nia'];
  const pageSize = 20;
  const normalizedText = value => String(value || '').normalize('NFKC').toLocaleLowerCase();

  function selectRows(rows, filters) {
    const f = filters || {};
    return rows.filter(row => row.geography !== 'excluded' &&
      (!f.category || row.dataset === f.category) &&
      (!f.office || row.office === f.office) &&
      (!f.status || (row.status_label || row.bridge_group || '') === f.status) &&
      (!f.search || normalizedText(row.title).includes(normalizedText(f.search).trim())) &&
      (!f.barangay || normalizedText(row.title).includes(normalizedText(f.barangay).trim()))
    ).sort((a, b) => {
      const sort = f.sort || 'title';
      if (sort !== 'title') {
        const [field, direction] = sort.split('-');
        const left = a.amounts[field], right = b.amounts[field];
        const leftKnown = Number.isSafeInteger(left), rightKnown = Number.isSafeInteger(right);
        if (leftKnown !== rightKnown) return leftKnown ? -1 : 1;
        if (leftKnown && left !== right) return (left < right ? -1 : 1) * (direction === 'desc' ? -1 : 1);
      } else {
        const titleOrder = String(a.title).localeCompare(String(b.title));
        if (titleOrder) return titleOrder;
      }
      return String(a.key).localeCompare(String(b.key));
    });
  }
  NB.selectRows = selectRows;

  if (!root.document) return;
  const doc = root.document;
  const page = doc.getElementById('national-budget-page');
  if (!page) return;
  const labels = root.NATIONAL_BUDGET_LABELS || {};
  const t = (key, values) => String(labels[key] || key).replace(/\{(\w+)\}/g, (match, name) =>
    values && Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : match);
  const el = id => doc.getElementById(id);
  const make = (tag, text, className) => {
    const node = doc.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  };
  const moneyFormat = new Intl.NumberFormat(doc.documentElement.lang || 'en', {
    style: 'currency', currency: 'PHP', minimumFractionDigits: 0, maximumFractionDigits: 0
  });
  const money = value => Number.isSafeInteger(value) ? moneyFormat.format(value) : t('unavailable');
  const literal = value => value === null || value === undefined || value === '' ? t('unavailable') :
    typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value);
  const stageName = stage => labels[stage] || t('unknown_stage') + (stage ? ' (' + stage + ')' : '');
  let client = NB.createClient();
  const outcomes = new Map();
  const cards = new Map();
  const seenNotices = new Set(), seenDisclaimers = new Set();
  const loading = new Set(datasets);
  let currentPage = 1, reviewPage = 1, selected = [];

  function filters() {
    return {
      category: el('nb-category').value, office: el('nb-office').value,
      status: el('nb-status-filter').value, search: el('nb-search').value,
      barangay: el('nb-barangay').value, sort: el('nb-sort').value,
      includeReview: el('nb-include-review').checked
    };
  }

  function allRows() {
    return Array.from(outcomes.values()).flatMap(outcome => outcome.records || []);
  }

  function addPair(list, label, value) {
    list.append(make('dt', label), make('dd', literal(value)));
  }

  function addLink(container, url, text) {
    const safe = NB.safeUrl(url);
    if (!safe) return;
    const link = make('a', text);
    link.href = safe;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    container.append(link);
  }

  function addSourceNotices(source) {
    const notice = source.meta && source.meta.notice;
    if (typeof notice === 'string' && notice && !seenNotices.has(notice)) {
      seenNotices.add(notice);
      el('nb-notice-content').append(make('p', notice));
    }
    (source.disclaimers || []).forEach(disclaimer => {
      const signature = JSON.stringify([disclaimer.title, disclaimer.body, disclaimer.url]);
      if (seenDisclaimers.has(signature)) return;
      seenDisclaimers.add(signature);
      const section = make('section', null, 'nb-source-notice');
      if (disclaimer.title) section.append(make('h3', disclaimer.title));
      if (typeof disclaimer.body === 'string') section.append(make('p', disclaimer.body));
      if (typeof disclaimer.url === 'string' && disclaimer.url) {
        try {
          addLink(section, new URL(disclaimer.url, 'https://budget.bettergov.ph').href, t('read_source_notice'));
        } catch (_) { /* Invalid source links remain unlinked; their notice text is retained. */ }
      }
      el('nb-notice-content').append(section);
    });
  }

  function comparisonLabel(row) {
    return t(row.aggregatable === false ? 'unclassified' : 'status_' + row.bridge_group);
  }

  function renderAvailability() {
    el('nb-availability').replaceChildren();
    el('nb-diagnostics').replaceChildren();
    datasets.forEach(dataset => {
      const outcome = outcomes.get(dataset);
      const block = make('div');
      block.dataset.dataset = dataset;
      block.dataset.state = loading.has(dataset) ? 'loading' : outcome.status;
      block.append(make('strong', dataset.toUpperCase()));
      block.append(make('p', t(loading.has(dataset) ? 'loading' : outcome.status === 'complete' && !outcome.records.length ? 'empty' : outcome.status)));
      if (outcome) {
        const stages = new Set([outcome.meta && outcome.meta.house_stage,
          ...(outcome.pages || []).map(page => page.meta && page.meta.house_stage),
          ...(outcome.records || []).map(row => row.stage)].filter(Boolean));
        if (stages.size) block.append(make('p', Array.from(stages, stageName).join(' · ')));
        const diagnostic = make('section');
        diagnostic.append(make('h3', dataset.toUpperCase()));
        const metadata = make('dl');
        if (outcome.meta) {
          addPair(metadata, t('built_at'), outcome.meta.built_at);
          addPair(metadata, t('source_commit'), outcome.meta.source_commit);
        }
        if (outcome.pages && outcome.pages[0]) addPair(metadata, t('retrieved'), outcome.pages[0].retrievedAt);
        if (outcome.warnings && outcome.warnings.length) addPair(metadata, t('warnings'), outcome.warnings);
        if (outcome.error) addPair(metadata, t('error'), outcome.error.message || outcome.error);
        diagnostic.append(metadata);
        el('nb-diagnostics').append(diagnostic);
        if (outcome.status !== 'complete' && !loading.has(dataset)) {
          const retry = make('button', t('retry'));
          retry.type = 'button';
          retry.dataset.retryDataset = dataset;
          retry.addEventListener('click', () => load(dataset, true));
          block.append(retry);
        }
        const sources = [{ meta: outcome.meta, disclaimers: outcome.disclaimers }].concat(outcome.pages || []);
        sources.forEach(addSourceNotices);
      }
      el('nb-availability').append(block);
    });
    const sourceDates = new Set();
    outcomes.forEach(outcome => {
      [outcome.meta, ...(outcome.pages || []).map(page => page.meta)].forEach(meta => {
        if (meta && meta.built_at) sourceDates.add(meta.built_at.slice(0, 10));
      });
    });
    const dateFormat = new Intl.DateTimeFormat(doc.documentElement.lang || 'en', { dateStyle: 'long', timeZone: 'UTC' });
    el('nb-source-date').hidden = !sourceDates.size;
    el('nb-source-date').textContent = t('source_snapshot_label') + ': ' +
      Array.from(sourceDates).sort().map(date => dateFormat.format(new Date(date + 'T00:00:00Z'))).join(' · ');
  }

  function renderSummary() {
    const groups = NB.summarize(selected);
    if (!groups.length) ['hgab2', 'hgab3'].forEach(stage => {
      if (!groups.some(group => group.stage === stage)) {
        groups.push({ stage, fiscalYear: 2027, count: 0, nep: { value: null, known: 0, unknown: 0 },
          house: { value: null, known: 0, unknown: 0 }, delta: { value: null }, pairedCount: 0 });
      }
    });
    groups.sort((a, b) => String(a.stage).localeCompare(String(b.stage)));
    el('nb-summary').replaceChildren();
    groups.forEach(group => {
      const section = make('section', null, 'nb-stage');
      section.dataset.stage = group.stage;
      section.append(make('h3', stageName(group.stage)));
      section.append(make('p', !group.count && loading.size ? t('loading') :
        !group.count && (page.dataset.state === 'error' || page.dataset.state === 'partial') ? t('unavailable') :
          t('selected_count', { count: group.count })));
      const matchingDatasets = datasets.filter(dataset => {
        const outcome = outcomes.get(dataset);
        return !outcome || !outcome.meta || outcome.meta.house_stage === group.stage ||
          (outcome.pages || []).some(page => page.meta && page.meta.house_stage === group.stage) ||
          (outcome.records || []).some(row => row.stage === group.stage);
      });
      section.append(make('p', matchingDatasets.map(dataset => dataset.toUpperCase()).join(' · '), 'nb-kicker'));
      if (group.partial || matchingDatasets.some(dataset => loading.has(dataset) || outcomes.get(dataset).status !== 'complete')) {
        section.append(make('p', t('partial'), 'nb-warning'));
        section.dataset.partial = 'true';
      }
      const list = make('dl');
      ['nep', 'house', 'delta'].forEach(metric => {
        const amount = group[metric];
        const term = make('dt', metric === 'house' ? stageName(group.stage) : t(metric === 'delta' ? 'change' : 'nep'));
        const value = make('dd', money(amount.overflow ? null : amount.value));
        value.dataset.metric = metric;
        value.dataset.value = amount.overflow || amount.value === null ? '' : String(amount.value);
        if (metric !== 'delta' && amount.unknown) value.append(make('small', t('known_unknown', amount)));
        if (metric === 'delta' && group.pairedCount < group.count) value.append(make('small', t('eligible', { count: group.pairedCount })));
        if (amount.overflow) value.append(make('p', t('overflow'), 'nb-warning'));
        const metricCell = make('div', null, 'nb-summary-metric');
        metricCell.append(term, value);
        list.append(metricCell);
      });
      section.append(list);
      el('nb-summary').append(section);
    });
  }

  function renderProject(row) {
    const card = make('article', null, 'nb-project');
    card.dataset.projectKey = row.key;
    card.append(make('p', [row.dataset.toUpperCase(), row.program].filter(Boolean).join(' · '), 'nb-kicker'));
    card.append(make('h3', row.title, 'nb-project-title'));
    const location = row.title.match(/\bBarangay\s+[^,;()]+/i);
    if (location && location[0].length <= 80) {
      card.append(make('p', t('title_location', { name: location[0].trim() }), 'nb-title-location'));
    }
    const amounts = make('dl', null, 'nb-project-amounts');
    [['nep', t('nep')], ['house', stageName(row.stage)]].forEach(([version, label]) => {
      const cell = make('div');
      cell.dataset.version = version;
      const amount = make('dd');
      amount.append(make('strong', money(row.amounts[version])));
      cell.append(make('dt', label), amount);
      amounts.append(cell);
    });
    card.append(amounts);
    card.append(make('p', comparisonLabel(row) + (row.comparable ? ' · ' + t('change') + ': ' + money(row.amounts.delta) : ''), 'nb-comparison'));
    if (row.flags && row.flags.includes('nep_evidence_review')) {
      card.append(make('p', t('source_review_pending'), 'nb-warning nb-source-review'));
    }
    if (row.held) card.append(make('p', t('held_short'), 'nb-warning'));
    if (row.geography === 'review') card.append(make('p', t('location_pending'), 'nb-warning nb-location-review'));
    const disclosure = make('details');
    disclosure.dataset.projectKey = row.key;
    disclosure.append(make('summary', t('details')));
    const record = make('div', null, 'nb-project-record');
    record.append(make('h4', row.title));
    const list = make('dl');
    addPair(list, t('office'), row.office);
    addPair(list, t('program'), [row.program, row.pap].filter(Boolean).join(' / '));
    addPair(list, t('region'), row.region);
    if (row.geography === 'review') addPair(list, t('review_reason'), row.reviewReasons.map(reason => labels[reason] || reason).join('; '));
    record.append(list);
    if (row.held) record.append(make('p', t('held'), 'nb-warning'));
    if (row.flags && row.flags.length) {
      record.append(make('h4', t('flags')));
      const flags = make('ul', null, 'nb-flags');
      row.flags.forEach(flag => flags.append(make('li', flag)));
      record.append(flags);
      if (row.flags.includes('nep_evidence_review')) record.append(make('p', t('nep_evidence_review')));
    }
    addLink(record, row.url, t('upstream'));
    ['nep', 'hgab2', 'hgab3'].forEach(version => {
      const pageNumber = row.pages && row.pages[version];
      addLink(record, row.pdf && row.pdf[version], t('pdf') + ' · ' + (version === 'nep' ? 'NEP' : stageName(version)) +
        (pageNumber === null || pageNumber === undefined ? '' : ' · ' + pageNumber));
    });
    record.append(make('p', t('pdf_positions'), 'nb-source-help'));
    disclosure.append(record);
    const body = make('div', null, 'nb-detail');
    body.dataset.state = 'idle';
    disclosure.append(body);
    const technical = make('details', null, 'nb-project-technical');
    technical.append(make('summary', t('technical_details')));
    const technicalList = make('dl');
    addPair(technicalList, t('reference_key'), row.key);
    addPair(technicalList, t('confidence'), row.confidence);
    addPair(technicalList, t('record_status'), [row.status_label, row.bridge_group, row.trace].filter(Boolean).join(' · '));
    technical.append(technicalList);
    const raw = make('pre', JSON.stringify(row.raw, null, 2));
    technical.append(raw);
    disclosure.append(technical);
    let detailLoaded = false, detailLoading = false;
    async function loadDetail() {
      if (detailLoaded || detailLoading) return;
      detailLoading = true;
      body.replaceChildren(make('p', t('detail_loading')));
      body.dataset.state = 'loading';
      try {
        const detail = await client.detail(row);
        body.replaceChildren();
        if (detail.mixedSnapshot) body.append(make('p', t('snapshot_warning'), 'nb-warning'));
        body.append(make('h4', t('evidence')));
        const detailLabels = detail.raw && detail.raw.labels;
        Object.values(detailLabels || {}).forEach(label => {
          (Array.isArray(label) ? label : [label]).forEach(item => {
            if (!item || typeof item !== 'object') return;
            if (typeof item.label === 'string') body.append(make('p', item.label));
            if (typeof item.help === 'string') body.append(make('p', item.help, 'nb-source-help'));
          });
        });
        const evidence = detail.raw && detail.raw.record;
        if (evidence && typeof evidence.reason === 'string') body.append(make('p', evidence.reason));
        if (evidence && typeof evidence.match_basis === 'string') body.append(make('p', evidence.match_basis));
        if (!body.querySelector('p')) body.append(make('p', t('source_record_available')));
        raw.textContent = JSON.stringify(detail.raw, null, 2);
        addSourceNotices(detail);
        detailLoaded = true;
        body.dataset.state = 'ready';
      } catch (error) {
        body.replaceChildren(make('p', t('detail_error')));
        const retry = make('button', t('retry'));
        retry.type = 'button';
        retry.dataset.retryDetail = row.key;
        retry.addEventListener('click', loadDetail);
        body.append(retry);
        body.dataset.state = 'error';
      } finally {
        detailLoading = false;
      }
    }
    disclosure.addEventListener('toggle', () => { if (disclosure.open) loadDetail(); });
    card.append(disclosure);
    return card;
  }

  function renderList(rows, prefix, requestedPage, emptyLabel) {
    const pages = Math.max(1, Math.ceil(rows.length / pageSize));
    const index = Math.min(requestedPage, pages);
    const container = el(prefix === 'nb' ? 'nb-results' : 'nb-review-results');
    const nodes = rows.slice((index - 1) * pageSize, index * pageSize).map(row => {
      let cached = cards.get(row.key);
      if (!cached || cached.row !== row) {
        cached = { row, node: renderProject(row) };
        cards.set(row.key, cached);
      }
      return cached.node;
    });
    if (!rows.length && !loading.size) nodes.push(make('p', t(emptyLabel)));
    const desired = new Set(nodes);
    Array.from(container.children).forEach(node => { if (!desired.has(node)) node.remove(); });
    // Leave already-positioned cards connected to preserve disclosure state and focus.
    let cursor = container.firstChild;
    nodes.forEach(node => {
      if (node === cursor) cursor = cursor.nextSibling;
      else container.insertBefore(node, cursor);
    });
    el(prefix + '-page').textContent = t('page', { page: index, pages, count: rows.length });
    el(prefix + '-prev').disabled = index <= 1;
    el(prefix + '-next').disabled = index >= pages;
    el(prefix + '-page').parentElement.hidden = pages <= 1;
    return index;
  }

  function render() {
    const rows = allRows();
    const currentRows = new Map(rows.map(row => [row.key, row]));
    cards.forEach((cached, key) => { if (currentRows.get(key) !== cached.row) cards.delete(key); });
    const f = filters();
    const matching = selectRows(rows, f);
    const included = matching.filter(row => row.geography === 'included');
    const review = matching.filter(row => row.geography === 'review');
    selected = matching.filter(row => row.geography === 'included' || f.includeReview);
    const values = Array.from(outcomes.values());
    const errors = values.filter(outcome => outcome.status === 'error').length;
    page.dataset.state = loading.size ? 'loading' : errors === datasets.length ? 'error' :
      values.some(outcome => outcome.status !== 'complete') ? 'partial' : rows.length ? 'ready' : 'empty';
    page.dataset.selectedCount = String(selected.length);
    el('nb-status').textContent = !selected.length && loading.size ? t('loading') :
      !selected.length && (page.dataset.state === 'error' || page.dataset.state === 'partial' && !rows.length) ? t('unavailable') :
        t('selected_count', { count: selected.length }) +
          (loading.size || page.dataset.state === 'partial' ? ' · ' + t('partial') : '');
    el('nb-technical-counts').textContent = t('counts', {
      loaded: rows.filter(row => row.geography !== 'excluded').length,
      review: rows.filter(row => row.geography === 'review').length,
      excluded: values.reduce((sum, outcome) => sum + (outcome.excludedCount || 0), 0),
      invalid: values.reduce((sum, outcome) => sum + (outcome.invalidCount || 0), 0), errors, selected: selected.length
    });
    el('nb-coverage-status').textContent = t('coverage_summary', {
      complete: values.filter(outcome => outcome.status === 'complete').length, total: datasets.length
    }) + (loading.size ? ' · ' + t('loading') : '') +
      (values.some(outcome => outcome.status !== 'complete') ? ' · ' + t('coverage_limited') : '');
    renderAvailability();
    renderSummary();
    const emptyLabel = page.dataset.state === 'error' ? 'error' :
      page.dataset.state === 'partial' && !rows.length ? 'partial' :
        page.dataset.state === 'empty' ? 'empty' : 'no_match';
    currentPage = renderList(included, 'nb', currentPage, emptyLabel);
    reviewPage = renderList(review, 'nb-review', reviewPage, 'no_review');
    el('nb-review-section').hidden = !review.length;
    el('nb-export').disabled = !selected.length;
    el('nb-export-metadata').disabled = !outcomes.size;
    el('nb-export-scope').textContent = t('export_notice') + ' ' + t('selected_count', { count: selected.length }) +
      (page.dataset.state === 'partial' || loading.size || errors ? ' ' + t('partial') : '');
  }

  function updateOptions() {
    const rows = allRows();
    [['nb-office', row => row.office], ['nb-status-filter', row => row.status_label || row.bridge_group]].forEach(([id, getValue]) => {
      const control = el(id), value = control.value;
      control.replaceChildren(new Option(t('all'), ''));
      const options = Array.from(new Set(rows.map(getValue).filter(Boolean))).sort();
      const optionLabels = options.map(item => id === 'nb-status-filter' ? comparisonLabel(rows.find(row => getValue(row) === item)) : item);
      options.forEach((item, index) => control.add(new Option(optionLabels[index], item)));
      if (Array.from(control.options).some(option => option.value === value)) control.value = value;
      control.closest('label').hidden = new Set(optionLabels).size <= 1 && !control.value;
    });
    el('nb-include-review').closest('label').hidden = !rows.some(row => row.geography === 'review') && !el('nb-include-review').checked;
  }

  async function load(dataset, reload) {
    loading.add(dataset);
    render();
    try {
      outcomes.set(dataset, await client.loadDataset(dataset, { reload: !!reload }));
    } catch (error) {
      outcomes.set(dataset, { dataset, status: 'error', records: [], error: { message: error.message }, warnings: [] });
    } finally {
      loading.delete(dataset);
      updateOptions();
      el('nb-filters').querySelector('fieldset').disabled = !outcomes.size;
      render();
    }
  }

  function download(content, type, filename) {
    const url = root.URL.createObjectURL(new Blob([content], { type }));
    const link = make('a');
    link.href = url;
    link.download = filename;
    doc.body.append(link);
    link.click();
    link.remove();
    root.setTimeout(() => root.URL.revokeObjectURL(url), 1000);
  }

  el('nb-filters').addEventListener('submit', event => event.preventDefault());
  el('nb-filters').addEventListener('input', () => { currentPage = 1; reviewPage = 1; render(); });
  [['nb-prev', -1, false], ['nb-next', 1, false], ['nb-review-prev', -1, true], ['nb-review-next', 1, true]].forEach(([id, step, review]) => {
    el(id).addEventListener('click', () => { if (review) reviewPage += step; else currentPage += step; render(); });
  });
  el('nb-export').addEventListener('click', () => {
    download(NB.csv(selected), 'text/csv;charset=utf-8', 'better-mapandan-national-budget-2027-mapandan.csv');
  });
  el('nb-export-metadata').addEventListener('click', () => {
    const metadata = {
      fiscal_year: 2027, query: { q: 'Mapandan', datasets }, filters: filters(),
      exported_at: new Date().toISOString(), selected_count: selected.length,
      selected_keys: selected.map(row => row.key), coverage: page.dataset.state,
      datasets: Array.from(outcomes.values()).map(outcome => ({
        dataset: outcome.dataset, status: outcome.status, total: outcome.total,
        meta: outcome.meta, pages: outcome.pages, disclaimers: outcome.disclaimers,
        warnings: outcome.warnings, error: outcome.error, invalid_count: outcome.invalidCount,
        excluded_count: outcome.excludedCount, review_count: outcome.reviewCount
      }))
    };
    download(JSON.stringify(metadata, null, 2), 'application/json;charset=utf-8', 'better-mapandan-national-budget-2027-mapandan-metadata.json');
  });
  root.addEventListener('pagehide', () => client.abort());
  root.addEventListener('pageshow', event => {
    if (event.persisted) client = NB.createClient();
  });
  render();
  datasets.forEach(dataset => load(dataset, false));
})(typeof window !== 'undefined' ? window : globalThis);
