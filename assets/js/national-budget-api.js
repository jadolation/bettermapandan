(function (global) {
  "use strict";
  const api = global.NationalBudget = global.NationalBudget || {};
  const ROOT = "https://budget.bettergov.ph/api/v1/hgab/2027/datasets/";
  const identity = m => JSON.stringify([m.fiscal_year, m.dataset_key, m.currency, m.scale, m.house_stage, m.source_repo, m.source_commit, m.built_at]);
  function createClient(options) {
    const opts = options || {};
    const fetcher = opts.fetch || global.fetch.bind(global);
    const now = opts.now || (() => Date.now());
    const timeoutMs = opts.timeoutMs == null ? 15000 : opts.timeoutMs;
    const maxPages = Math.min(opts.maxPages || 100, 100), maxRows = Math.min(opts.maxRows || 5000, 5000);
    const cache = new Map(), loads = new Map(), controllers = new Set();
    let stopped = false;
    function aborted() { const error = new Error("aborted"); error.name = "AbortError"; return error; }
    function sleep(ms, signal) {
      if (opts.sleep) return opts.sleep(ms, signal);
      return new Promise((resolve, reject) => {
        const timer = setTimeout(finish, ms);
        function finish() { signal.removeEventListener("abort", cancel); resolve(); }
        function cancel() { clearTimeout(timer); signal.removeEventListener("abort", cancel); reject(aborted()); }
        signal.addEventListener("abort", cancel, { once: true });
        if (signal.aborted) cancel();
      });
    }
    function request(url, dataset, detail, signal) {
      if (cache.has(url)) return cache.get(url);
      const promise = (async () => {
        let waitBudget = 30000;
        for (let attempt = 0; attempt < Math.min(opts.maxAttempts || 2, 2); attempt++) {
          if (stopped || (signal && signal.aborted)) throw aborted();
          const controller = new AbortController();
          controllers.add(controller);
          const cancel = () => controller.abort();
          if (signal) signal.addEventListener("abort", cancel, { once: true });
          let timedOut = false;
          const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
          let retry = false, delay = 0, failure;
          try {
            const response = await fetcher(url, { method: "GET", credentials: "omit", signal: controller.signal, headers: { Accept: "application/json" } });
            if (!response.ok) {
              failure = new Error("http_" + response.status);
              retry = response.status === 429 || response.status >= 500 && response.status < 600;
              const header = response.headers && response.headers.get("Retry-After");
              if (header != null) {
                const seconds = /^\d+(?:\.\d+)?$/.test(header.trim()) ? Number(header) * 1000 : Date.parse(header) - now();
                if (Number.isFinite(seconds)) delay = Math.max(0, seconds);
              }
              if (delay > waitBudget) { failure = new Error("retry_after_budget"); retry = false; }
            } else {
              let envelope;
              try { envelope = await response.json(); } catch (_) { throw new Error("invalid_json"); }
              api.validateEnvelope(envelope, { dataset, detail });
              return { envelope, endpoint: url, retrievedAt: new Date(now()).toISOString() };
            }
          } catch (error) {
            failure = error;
            if (stopped || (signal && signal.aborted)) throw aborted();
            retry = timedOut || error instanceof TypeError || error.name === "AbortError";
            if (timedOut) failure = new Error("timeout");
          } finally {
            clearTimeout(timer);
            controllers.delete(controller);
            if (signal) signal.removeEventListener("abort", cancel);
          }
          if (!retry || attempt + 1 >= Math.min(opts.maxAttempts || 2, 2)) throw failure;
          waitBudget -= delay;
          // Keep backoff abortable, including navigation during a readable Retry-After.
          const waiting = new AbortController();
          controllers.add(waiting);
          const cancelWait = () => waiting.abort();
          if (signal) signal.addEventListener("abort", cancelWait, { once: true });
          try { await sleep(delay, waiting.signal); } finally {
            controllers.delete(waiting);
            if (signal) signal.removeEventListener("abort", cancelWait);
          }
        }
        throw new Error("request_failed");
      })();
      cache.set(url, promise);
      promise.catch(() => { if (cache.get(url) === promise) cache.delete(url); });
      return promise;
    }
    function loadDataset(dataset, settings) {
      if (!api.DATASETS.includes(dataset)) return Promise.reject(new Error("invalid_dataset"));
      const config = settings || {};
      if (config.reload) {
        for (const url of cache.keys()) if (url.startsWith(ROOT + dataset + "/")) cache.delete(url);
        loads.delete(dataset);
      }
      if (loads.has(dataset)) return loads.get(dataset);
      const promise = (async () => {
        const result = { dataset, status: "error", records: [], meta: null, pages: [], disclaimers: [], warnings: [],
          invalidCount: 0, invalidRows: [], excludedCount: 0, reviewCount: 0, total: null, error: null };
        const seen = new Map(), signatures = new Set(), noticeSet = new Set();
        let offset = 0, received = 0, done = false;
        function warn(code) { if (!result.warnings.includes(code)) result.warnings.push(code); }
        try {
          while (!done && result.pages.length < maxPages && received < maxRows) {
            const page = await request(ROOT + dataset + "/projects?q=Mapandan&limit=50&offset=" + offset, dataset, false, config.signal);
            const { meta, data, disclaimers } = page.envelope;
            result.pages.push({ meta, disclaimers, sums: data.sums, endpoint: page.endpoint, retrievedAt: page.retrievedAt });
            for (const notice of disclaimers) {
              const key = JSON.stringify(notice);
              if (!noticeSet.has(key)) { noticeSet.add(key); result.disclaimers.push(notice); }
            }
            if (!result.meta) { result.meta = meta; result.total = data.total; }
            else {
              if (identity(result.meta) !== identity(meta)) warn("mixed_snapshot");
              if (result.total !== data.total) warn("inconsistent_total");
              if (JSON.stringify(result.pages[0].sums) !== JSON.stringify(data.sums)) warn("inconsistent_sums");
            }
            if (meta.offset !== undefined && meta.offset !== offset) warn("inconsistent_offset");
            if (meta.total !== undefined && meta.total !== data.total) warn("inconsistent_total");
            if (meta.returned !== undefined && meta.returned !== data.rows.length) warn("inconsistent_returned");
            const signature = JSON.stringify(data.rows);
            if (signatures.has(signature) && data.rows.length) { warn("repeated_page"); break; }
            signatures.add(signature);
            for (const raw of data.rows) {
              received++;
              if (received > maxRows) { warn("safety_cap"); break; }
              try {
                const record = api.normalize(raw, meta);
                if (seen.has(record.key)) {
                  warn("duplicate_rows");
                  const previous = seen.get(record.key);
                  // Flags are annotations: preserve their union even on conflicting duplicates.
                  previous.flags = Array.from(new Set([...previous.flags, ...record.flags])).sort();
                  if (JSON.stringify(previous.raw) !== JSON.stringify(raw)) warn("conflicting_duplicate");
                } else {
                  seen.set(record.key, record);
                  if (record.geography === "excluded") result.excludedCount++;
                  else { result.records.push(record); if (record.geography === "review") result.reviewCount++; }
                }
              } catch (error) {
                result.invalidCount++;
                result.invalidRows.push({ raw, page: result.pages.length, reason: error.message });
                warn("invalid_rows");
              }
            }
            if (data.next_offset === null) { done = true; break; }
            if (!data.rows.length || data.next_offset <= offset || data.next_offset !== offset + data.rows.length) {
              warn("invalid_next_offset"); break;
            }
            offset = data.next_offset;
          }
          if (!done) warn("incomplete_pagination");
          if (received !== result.total) warn("count_disagreement");
          if (result.pages.length >= maxPages && !done || received >= maxRows && !done) warn("safety_cap");
          if (!result.warnings.length) {
            const rawRows = Array.from(seen.values());
            for (const version of ["nep", "hgab2", "hgab3", "api"]) {
              const sum = api.subtotal(rawRows.map(r => r.amounts[version]));
              const upstream = result.pages[0].sums[version + "_php"];
              if (sum.overflow || upstream !== sum.value) warn("sum_disagreement");
            }
          }
          result.status = result.warnings.length ? "partial" : "complete";
        } catch (error) {
          result.error = error.message || "request_failed";
          result.status = result.pages.length ? "partial" : "error";
          warn(result.error);
        }
        result.records.forEach(row => { row.partial = result.status !== "complete"; });
        return result;
      })();
      loads.set(dataset, promise);
      promise.then(result => { if (result.status !== "complete" && loads.get(dataset) === promise) loads.delete(dataset); });
      return promise;
    }
    async function detail(row, settings) {
      if (!api.DATASETS.includes(row.dataset) || !row.id) throw new Error("invalid_detail_id");
      const url = ROOT + row.dataset + "/projects/" + encodeURIComponent(row.id);
      try {
        const response = await request(url, row.dataset, true, settings && settings.signal);
        if (response.envelope.data.id !== row.id) throw new Error("detail_id_mismatch");
        return { record: api.normalize(response.envelope.data, response.envelope.meta), raw: response.envelope.data,
          meta: response.envelope.meta, disclaimers: response.envelope.disclaimers, endpoint: response.endpoint,
          retrievedAt: response.retrievedAt, mixedSnapshot: identity(row.meta) !== identity(response.envelope.meta) };
      } catch (error) { cache.delete(url); throw error; }
    }
    function abort() { stopped = true; for (const controller of controllers) controller.abort(); cache.clear(); loads.clear(); }
    return { loadDataset, detail, abort };
  }
  api.createClient = createClient;
})(window);
