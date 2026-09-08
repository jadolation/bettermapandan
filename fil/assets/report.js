document.addEventListener("DOMContentLoaded", function () {
  var currentMode = "report";
  var TO_EMAIL = "zaratejandale15@gmail.com";

  // --- Segmented control ---
  var buttons = document.querySelectorAll(".segmented-control button");
  var panels = {
    report: document.getElementById("panel-report"),
    contribute: document.getElementById("panel-contribute"),
    suggest: document.getElementById("panel-suggest")
  };

  function setMode(mode) {
    currentMode = mode;
    buttons.forEach(function (btn) {
      var isActive = btn.getAttribute("data-mode") === mode;
      btn.classList.toggle("active", isActive);
      btn.setAttribute("aria-selected", isActive ? "true" : "false");
    });
    Object.keys(panels).forEach(function (key) {
      panels[key].classList.toggle("active", key === mode);
    });
    updatePreview();
  }

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      setMode(this.getAttribute("data-mode"));
    });
  });

  // --- Live preview ---
  var previewMode = document.getElementById("preview-mode");
  var previewTitle = document.getElementById("preview-title");
  var previewDesc = document.getElementById("preview-desc");

  var modeLabels = { report: "Report Error", contribute: "Submit Missing Info", suggest: "Suggest Feature" };
  var modeClasses = { report: "mode-report", contribute: "mode-contribute", suggest: "mode-suggest" };

  function updatePreview() {
    previewMode.textContent = modeLabels[currentMode];
    previewMode.className = "civic-preview-mode " + modeClasses[currentMode];

    var title = "";
    var desc = "";

    if (currentMode === "report") {
      title = document.getElementById("field-report-page").value.trim();
      desc = document.getElementById("field-report-error").value.trim();
      if (!title) title = document.getElementById("field-report-correction").value.trim();
    } else if (currentMode === "contribute") {
      title = document.getElementById("field-contribute-title").value.trim();
      desc = document.getElementById("field-contribute-desc").value.trim();
      var cat = document.getElementById("field-contribute-category").value;
      if (cat) title = "[" + cat + "] " + title;
    } else {
      title = document.getElementById("field-suggest-name").value.trim();
      desc = document.getElementById("field-suggest-desc").value.trim();
    }

    previewTitle.textContent = title || "Enter a title above...";
    previewDesc.textContent = desc ? (desc.length > 140 ? desc.slice(0, 140) + "..." : desc) : "Your submission preview will appear here as you type.";
  }

  // Attach live update listeners to all form fields
  document.querySelectorAll(".civic-form-field input, .civic-form-field textarea, .civic-form-field select").forEach(function (el) {
    el.addEventListener("input", updatePreview);
    el.addEventListener("change", updatePreview);
  });

  // --- URL parameter handling ---
  var params = new URLSearchParams(location.search);
  var serviceParam = params.get("service");
  var barangayParam = params.get("barangay");
  var pageParam = params.get("page");
  var modeParam = params.get("mode");
  var sectionParam = params.get("section");
  var itemParam = params.get("item");

  if (modeParam === "contribute" || modeParam === "suggest") {
    setMode(modeParam);
  } else if (serviceParam || barangayParam || pageParam) {
    setMode("report");
    var pageField = document.getElementById("field-report-page");
    if (serviceParam) pageField.value = serviceParam;
    else if (barangayParam) pageField.value = barangayParam;
    else if (pageParam) pageField.value = pageParam;
  }

  if (currentMode === "contribute") {
    if (sectionParam) {
      var catSelect = document.getElementById("field-contribute-category");
      for (var i = 0; i < catSelect.options.length; i++) {
        if (catSelect.options[i].value === sectionParam) { catSelect.selectedIndex = i; break; }
      }
    }
    if (itemParam) document.getElementById("field-contribute-title").value = itemParam;
  }

  updatePreview();

  // --- Honeypot check ---
  function isHoneypotFilled() {
    var hp = document.querySelector(".honeypot");
    return hp && hp.value.length > 0;
  }

  // --- Build mailto URL ---
  function buildMailto(mode) {
    if (isHoneypotFilled()) return null;

    var subject = "";
    var body = "";

    if (mode === "report") {
      var page = document.getElementById("field-report-page").value.trim();
      var error = document.getElementById("field-report-error").value.trim();
      var correction = document.getElementById("field-report-correction").value.trim();
      var source = document.getElementById("field-report-source").value.trim();
      subject = "Data Correction: " + (page || "General");
      body = "Mode: Report Error\nPage/Item: " + page + "\nError: " + error + "\nCorrection: " + correction + "\nSource: " + source;
    } else if (mode === "contribute") {
      var cat = document.getElementById("field-contribute-category").value;
      var title = document.getElementById("field-contribute-title").value.trim();
      var desc = document.getElementById("field-contribute-desc").value.trim();
      var vSource = document.getElementById("field-contribute-source").value.trim();
      subject = "New Information: " + title;
      body = "Mode: Submit Missing Info\nCategory: " + cat + "\nTitle: " + title + "\nDescription: " + desc + "\nSource: " + vSource;
    } else {
      var name = document.getElementById("field-suggest-name").value.trim();
      var sDesc = document.getElementById("field-suggest-desc").value.trim();
      var usecase = document.getElementById("field-suggest-usecase").value.trim();
      subject = "Feature Suggestion: " + name;
      body = "Mode: Suggest Feature\nFeature: " + name + "\nDescription: " + sDesc + "\nUse Case: " + usecase;
    }

    return "mailto:" + TO_EMAIL + "?subject=" + encodeURIComponent(subject) + "&body=" + encodeURIComponent(body);
  }

  // --- Build plain text draft ---
  function buildDraftText(mode) {
    return buildMailto(mode)
      .replace(/^mailto:[^?]+/, "")
      .replace(/\?subject=/, "Subject: ")
      .replace(/&body=/, "\n\n");
  }

  // --- Toast ---
  var toastEl = document.getElementById("civic-toast");
  var toastTimer = null;

  function showToast(message) {
    toastEl.textContent = message;
    toastEl.classList.add("show");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("show"); }, 4000);
  }

  // --- Submit buttons (mailto) ---
  document.getElementById("submit-report").addEventListener("click", function (e) {
    e.preventDefault();
    var url = buildMailto("report");
    if (!url) return;
    window.location.href = url;
    showToast("\uD83D\uDFE2 Draft opened! Please press 'Send' in your email app to complete.");
  });

  document.getElementById("submit-contribute").addEventListener("click", function (e) {
    e.preventDefault();
    var url = buildMailto("contribute");
    if (!url) return;
    window.location.href = url;
    showToast("\uD83D\uDFE2 Draft opened! Please press 'Send' in your email app to complete.");
  });

  document.getElementById("submit-suggest").addEventListener("click", function (e) {
    e.preventDefault();
    var url = buildMailto("suggest");
    if (!url) return;
    window.location.href = url;
    showToast("\uD83D\uDFE2 Draft opened! Please press 'Send' in your email app to complete.");
  });

  // --- Copy buttons (clipboard) ---
  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    // Fallback
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    return Promise.resolve();
  }

  document.getElementById("copy-report").addEventListener("click", function () {
    if (isHoneypotFilled()) return;
    var url = buildMailto("report");
    if (!url) return;
    // Decode the mailto body for clipboard
    var parts = url.split("?subject=");
    var subject = decodeURIComponent(parts[1].split("&body=")[0]);
    var body = decodeURIComponent(parts[1].split("&body=")[1]);
    var draft = "To: " + TO_EMAIL + "\nSubject: " + subject + "\n\n" + body;
    copyToClipboard(draft).then(function () {
      showToast("\uD83D\uDCCB Copied to clipboard! Paste into your email app.");
    });
  });

  document.getElementById("copy-contribute").addEventListener("click", function () {
    if (isHoneypotFilled()) return;
    var url = buildMailto("contribute");
    if (!url) return;
    var parts = url.split("?subject=");
    var subject = decodeURIComponent(parts[1].split("&body=")[0]);
    var body = decodeURIComponent(parts[1].split("&body=")[1]);
    var draft = "To: " + TO_EMAIL + "\nSubject: " + subject + "\n\n" + body;
    copyToClipboard(draft).then(function () {
      showToast("\uD83D\uDCCB Copied to clipboard! Paste into your email app.");
    });
  });

  document.getElementById("copy-suggest").addEventListener("click", function () {
    if (isHoneypotFilled()) return;
    var url = buildMailto("suggest");
    if (!url) return;
    var parts = url.split("?subject=");
    var subject = decodeURIComponent(parts[1].split("&body=")[0]);
    var body = decodeURIComponent(parts[1].split("&body=")[1]);
    var draft = "To: " + TO_EMAIL + "\nSubject: " + subject + "\n\n" + body;
    copyToClipboard(draft).then(function () {
      showToast("\uD83D\uDCCB Copied to clipboard! Paste into your email app.");
    });
  });
});

// --- WebMCP Tool Registration ---
if (window.WebMCP && typeof WebMCP.registerTool === 'function') {
  WebMCP.registerTool({
    name: 'report-error',
    label: 'Report Error',
    inputSchema: {
      type: 'object',
      properties: {
        page: { type: 'string', label: 'Page / Item', description: 'The page or item where the error was found' },
        error: { type: 'string', label: 'What is incorrect?', description: 'Description of the error' },
        correction: { type: 'string', label: 'Correct information', description: 'The correct data if known' },
        source: { type: 'string', label: 'Source / Proof Link', description: 'Link to supporting document' }
      },
      required: ['error']
    }
  });

  WebMCP.registerTool({
    name: 'submit-information',
    label: 'Submit Missing Information',
    inputSchema: {
      type: 'object',
      properties: {
        category: { type: 'string', label: 'Category', description: 'Type of information being submitted', enum: ['Official', 'Service', 'Hotline', 'Ordinance', 'Historical Detail'] },
        title: { type: 'string', label: 'Information Title / Name', description: 'Title of the information' },
        description: { type: 'string', label: 'Description & Details', description: 'Detailed description' },
        source: { type: 'string', label: 'Verification Source / Proof Link', description: 'Link to verifiable source' }
      },
      required: ['category', 'title', 'description']
    }
  });

  WebMCP.registerTool({
    name: 'suggest-feature',
    label: 'Suggest New Feature',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', label: 'Feature Name', description: 'Name of the proposed feature' },
        description: { type: 'string', label: 'Description', description: 'Detailed description of the feature' },
        usecase: { type: 'string', label: 'Use Case / Why it matters', description: 'How this would help Mapandan residents' }
      },
      required: ['name', 'description']
    }
  });
}
