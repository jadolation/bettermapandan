(function (global) {
  "use strict";
  const api = global.NationalBudget = global.NationalBudget || {};
  const DATASETS = ["dpwh", "fmr", "hfep", "nia"];
  const STAGES = ["hgab2", "hgab3"];
  const GROUPS = ["house_only", "nep_only", "unchanged", "increased", "decreased", "scope_review"];
  const TRACE_GROUPS = { amount_same: "unchanged", candidate_increase: "increased", candidate_decrease: "decreased",
    house_only_candidate: "house_only", nep_only_candidate: "nep_only", segment_scope_review: "scope_review" };
  const object = value => value !== null && typeof value === "object" && !Array.isArray(value);
  const text = value => typeof value === "string" ? value : "";
  function validTimestamp(value) {
    if (!/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(text(value)) ||
        !Number.isFinite(Date.parse(value))) return false;
    return new Date(value.slice(0, 10) + "T00:00:00Z").toISOString().slice(0, 10) === value.slice(0, 10);
  }
  function money(value) {
    if (value == null) return null;
    if (typeof value !== "number" || !Number.isSafeInteger(value)) throw new Error("invalid_amount");
    return value;
  }
  function safeUrl(value) {
    if (typeof value !== "string" || /[\u0000-\u0020\u007f]/.test(value)) return null;
    try {
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password && !url.port &&
        ["budget.bettergov.ph", "budget-assets.bettergov.ph"].includes(url.hostname) ? url.href : null;
    } catch (_) { return null; }
  }
  function validateEnvelope(envelope, options) {
    const { dataset, detail = false } = options || {};
    if (!object(envelope) || !object(envelope.meta) || !object(envelope.data)) throw new Error("invalid_envelope");
    const m = envelope.meta;
    if (m.dataset !== "hgab" || m.dataset_key !== dataset || !DATASETS.includes(dataset) ||
        m.fiscal_year !== 2027 || m.currency !== "PHP" || m.scale !== "pesos" ||
        !text(m.house_stage).trim() || !text(m.source_commit).trim() || !validTimestamp(m.built_at) ||
        !/^https:\/\/github\.com\/[a-z\d](?:[a-z\d-]*[a-z\d])?\/(?!\.{1,2}\/?$)[a-z\d_.-]+\/?$/i.test(text(m.source_repo)) ||
        !text(m.notice).trim() || !Array.isArray(envelope.disclaimers) ||
        envelope.disclaimers.some(d => !object(d) || typeof d.body !== "string")) throw new Error("invalid_metadata");
    if (!detail && (!Array.isArray(envelope.data.rows) || !Number.isSafeInteger(envelope.data.total) ||
        envelope.data.total < 0 || !object(envelope.data.sums) ||
        !(envelope.data.next_offset === null || (Number.isSafeInteger(envelope.data.next_offset) && envelope.data.next_offset >= 0)))) {
      throw new Error("invalid_pagination_envelope");
    }
    return envelope;
  }
  function normalize(row, meta) {
    if (!object(row) || !text(row.id) || !text(row.title) || !object(meta) ||
        !DATASETS.includes(meta.dataset_key) || row.dataset !== meta.dataset_key ||
        (row.held != null && typeof row.held !== "boolean") ||
        (row.flags != null && (!Array.isArray(row.flags) || row.flags.some(f => typeof f !== "string")))) throw new Error("invalid_row");
    const stage = meta.house_stage;
    const amounts = {};
    for (const version of ["nep", "hgab2", "hgab3", "api"]) amounts[version] = money(row[version + "_php"]);
    const knownStage = STAGES.includes(stage);
    amounts.house = knownStage ? amounts[stage] : null;
    if (Object.prototype.hasOwnProperty.call(row, "house_php") && money(row.house_php) !== amounts.house && knownStage) throw new Error("house_alias_mismatch");
    money(row.delta_php);
    const delta = amounts.house === null || amounts.nep === null ? null : amounts.house - amounts.nep;
    amounts.delta = Number.isSafeInteger(delta) ? delta : null;
    if (row.delta_php != null && amounts.delta !== null && row.delta_php !== amounts.delta) throw new Error("delta_mismatch");
    const pdf = {}, pages = {}, documents = {};
    for (const version of ["nep", "hgab2", "hgab3"]) {
      pdf[version] = safeUrl(object(row.pdf_url) ? row.pdf_url[version] : null);
      pages[version] = Number.isSafeInteger(row[version + "_page"]) && row[version + "_page"] > 0 ? row[version + "_page"] : null;
      documents[version] = text(row[version + "_doc"]) || null;
    }
    pdf.house = knownStage ? pdf[stage] : null;
    const titleMatch = /\bmapandan\b/i.test(row.title);
    const region = text(row.region).trim(), regionKey = text(row.region_key).trim();
    const missingRegion = !regionKey && !region;
    const regionMatches = (!regionKey || regionKey.toUpperCase() === "I") &&
      (!region || /^(?:region\s+)?I(?:\s*[-(].*)?$/i.test(region));
    const reviewReasons = [];
    if (missingRegion) reviewReasons.push("missing_region");
    if (!titleMatch) reviewReasons.push("non_title_match");
    const geography = !missingRegion && !regionMatches ? "excluded" : reviewReasons.length ? "review" : "included";
    const knownStatus = TRACE_GROUPS[text(row.trace).replace(/^outside_api_then_/, "")] === row.bridge_group;
    const aggregatable = knownStage && GROUPS.includes(row.bridge_group) && knownStatus;
    const consistentChange = row.bridge_group === "unchanged" ? amounts.delta === 0 :
      row.bridge_group === "increased" ? amounts.delta > 0 : row.bridge_group === "decreased" && amounts.delta < 0;
    const comparable = aggregatable && row.held === false &&
      ["unchanged", "increased", "decreased"].includes(row.bridge_group) && amounts.delta !== null && consistentChange;
    const result = { key: meta.dataset_key + ":" + row.id, id: row.id, dataset: meta.dataset_key,
      fiscalYear: meta.fiscal_year, stage, title: row.title, amounts, pdf, pages, documents,
      titleMatch, geography, reviewReasons, aggregatable, comparable, flags: (row.flags || []).slice(),
      held: row.held == null ? null : row.held, confidence: row.confidence == null ? null : row.confidence,
      url: safeUrl(row.url), meta, raw: row };
    for (const key of ["program", "pap", "office", "office_kind", "region", "region_key", "bridge_group", "status_label", "trace", "house_match"]) result[key] = text(row[key]);
    return result;
  }
  function subtotal(values) {
    let value = 0, known = 0, overflow = false;
    for (const amount of values) if (amount !== null) {
      known++;
      if (!Number.isSafeInteger(value + amount)) overflow = true;
      else value += amount;
    }
    return { value: known && !overflow ? value : null, known, unknown: values.length - known, overflow };
  }
  function summarize(rows) {
    const groups = new Map();
    for (const row of rows) {
      const key = row.fiscalYear + ":" + row.stage;
      if (!groups.has(key)) groups.set(key, { stage: row.stage, fiscalYear: row.fiscalYear, rows: [] });
      groups.get(key).rows.push(row);
    }
    return Array.from(groups.values(), group => {
      const list = group.rows;
      return { stage: group.stage, fiscalYear: group.fiscalYear, count: list.length, partial: list.some(r => r.partial),
        nep: subtotal(list.map(r => r.aggregatable ? r.amounts.nep : null)),
        house: subtotal(list.map(r => r.aggregatable ? r.amounts.house : null)),
        delta: subtotal(list.map(r => r.comparable ? r.amounts.delta : null)),
        pairedCount: list.filter(r => r.comparable).length,
        qualifiedCount: list.filter(r => !r.comparable).length };
    }).sort((a, b) => a.fiscalYear - b.fiscalYear || a.stage.localeCompare(b.stage));
  }
  function csv(rows) {
    const header = ["external_key", "fiscal_year", "dataset", "title", "program", "office", "nep_php", "house_php", "house_stage", "delta_php", "bridge_group", "held", "flags", "project_url", "nep_pdf_url", "house_pdf_url", "source_snapshot_date"];
    function cell(value) {
      if (value == null) return "";
      let output = String(value);
      if (typeof value !== "number" && /^[\s\u0000-\u001f\u007f]*[=+\-@]/.test(output)) output = "'" + output;
      return /[",\r\n]/.test(output) ? '"' + output.replace(/"/g, '""') + '"' : output;
    }
    const lines = [header, ...rows.map(r => [r.key, r.fiscalYear, r.dataset, r.title, r.program, r.office,
      r.amounts.nep, r.amounts.house, r.stage, r.comparable ? r.amounts.delta : null, r.bridge_group, r.held,
      r.flags.slice().sort().join(";"), r.url, r.pdf.nep, r.pdf.house, r.meta.built_at || null])];
    return "\ufeff" + lines.map(line => line.map(cell).join(",")).join("\r\n") + "\r\n";
  }
  Object.assign(api, { DATASETS, STAGES, normalize, validateEnvelope, summarize, safeUrl, csv, subtotal });
})(window);
