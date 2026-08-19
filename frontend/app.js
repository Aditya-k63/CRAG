/* CRAG Assistant — chat UI */
(function () {
  "use strict";

  var STORE = {
    sessions: "crag_sessions",
    current: "crag_current",
    apiKey: "crag_api_key",
    topK: "crag_topk"
  };

  var PIPELINE_STAGES = [
    "Retrieving relevant documents...",
    "Evaluating retrieved context...",
    "Generating answer..."
  ];

  function load(key, fallback) {
    try {
      var raw = localStorage.getItem(key);
      if (raw === null || raw === "") return fallback;
      return JSON.parse(raw);
    } catch (e) {
      return fallback;
    }
  }

  function save(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function uid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "s-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  function getApiKey() {
    return localStorage.getItem(STORE.apiKey) || "rag-secret-2026";
  }

  function getTopK() {
    var n = parseInt(localStorage.getItem(STORE.topK), 10);
    return n >= 1 && n <= 10 ? n : 3;
  }

  var sessions = load(STORE.sessions, {});
  var currentId = load(STORE.current, null);

  if (!currentId || !sessions[currentId]) {
    currentId = uid();
    sessions[currentId] = { id: currentId, title: "New Chat", pinned: false, messages: [] };
    save(STORE.sessions, sessions);
    save(STORE.current, currentId);
  }

  function persist() {
    save(STORE.sessions, sessions);
    save(STORE.current, currentId);
  }

  function currentSession() {
    return sessions[currentId];
  }

  // ---------- DOM helpers ----------
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function toast(message, isError) {
    var wrap = document.getElementById("toast-wrap");
    var t = el("div", "toast" + (isError ? " error" : ""), message);
    wrap.appendChild(t);
    setTimeout(function () { t.remove(); }, 3600);
  }

  function svgIcon(name) {
    var icons = {
      plus: '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z"/></svg>',
      send: '<svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path fill="currentColor" d="m3 20 18-8L3 4v6l12 2-12 2v6Z"/></svg>',
      chat: '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="currentColor" d="M12 3a9 9 0 0 1 9 9c0 2.6-1.1 4.9-2.9 6.5-.2 1.5-1.2 2.8-2.7 3.9L14 23.2V21H12a9 9 0 1 1 0-18Zm-3 9a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm3 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm3 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z"/></svg>',
      doc: '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="currentColor" d="M14 3H7a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V8l-4-5Zm-1 1.5L16.5 8H13V4.5ZM9 12h6v1.5H9V12Zm0 3.5h6V17H9v-1.5Z"/></svg>',
      pin: '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path fill="currentColor" d="M16 9V4h2V2H6v2h2v5c0 1.7-1.3 3-3 3v2h5.5v6l1.5 1 1.5-1v-6H19v-2c-1.7 0-3-1.3-3-3Z"/></svg>',
      del: '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path fill="currentColor" d="M9 3h6l1 2h4v2H4V5h4l1-2ZM6 9h12l-1 12H7L6 9Zm3 2v8h2v-8H9Zm4 0v8h2v-8h-2Z"/></svg>',
      web: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm7.9 9h-3.1a15.9 15.9 0 0 0-1.5-6.3A8 8 0 0 1 19.9 11ZM12 4a14 14 0 0 1 2.3 7H9.7A14 14 0 0 1 12 4Zm-7.9 7a8 8 0 0 1 4.6-6.3A15.9 15.9 0 0 0 7.2 11H4.1ZM4 13h3.1c.2 2.4.7 4.5 1.5 6.3A8 8 0 0 1 4 13Zm3.1-1H4.1a8 8 0 0 1 4.6-6.3A15.9 15.9 0 0 0 7.1 12Zm4.9 9a14 14 0 0 1-2.3-7h4.6a14 14 0 0 1-2.3 7Zm1.1-9H9.9a16 16 0 0 1 .4-7h3.4a16 16 0 0 1 .4 7Zm1 8.3a15.9 15.9 0 0 0 1.5-6.3h3.1a8 8 0 0 1-4.6 6.3ZM16.9 12A15.9 15.9 0 0 1 15.4 5.7 8 8 0 0 1 20 12h-3.1Z"/></svg>',
      db: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 3C7.6 3 4 4.3 4 6s3.6 3 8 3 8-1.3 8-3-3.6-3-8-3Zm8 5c0 1.7-3.6 3-8 3S4 9.7 4 8v3c0 1.7 3.6 3 8 3s8-1.3 8-3V8Zm0 6c0 1.7-3.6 3-8 3s-8-1.3-8-3v3c0 1.7 3.6 3 8 3s8-1.3 8-3v-3Z"/></svg>',
      check: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2Z"/></svg>',
      arrow: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M4 11h11.2l-4.6-4.6L12 5l7 7-7 7-1.4-1.4 4.6-4.6H4v-2Z"/></svg>'
    };
    return icons[name] || "";
  }

  // ---------- Status ----------
  function setStatus(online) {
    var dot = document.getElementById("status-dot");
    dot.className = "status-dot " + (online ? "online" : "offline");
    dot.title = online ? "API online" : "API offline";
  }

  async function checkStatus() {
    try {
      var res = await fetch("/health", { cache: "no-store" });
      setStatus(res.status === 200);
    } catch (e) {
      setStatus(false);
    }
  }

  // ---------- API ----------
  async function api(path, options) {
    options = options || {};
    var headers = options.headers || {};
    headers["X-API-Key"] = getApiKey();
    options.headers = headers;
    var res = await fetch(path, options);
    var data = null;
    try { data = await res.json(); } catch (e) { /* ignore */ }
    if (!res.ok) {
      var detail = (data && (data.detail || data.message)) || ("Request failed (" + res.status + ")");
      if (typeof detail === "object" && detail.msg) detail = detail.msg;
      throw new Error(detail);
    }
    return data;
  }

  async function sendQuery(question, topK) {
    return api("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, top_k: topK })
    });
  }

  async function evaluateQuery(question, topK) {
    return api("/evaluate-query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question, top_k: topK })
    });
  }

  async function uploadPdf(file) {
    var form = new FormData();
    form.append("file", file);
    return api("/upload", { method: "POST", body: form });
  }

  async function fetchDocuments() {
    return api("/documents");
  }

  async function clearCache() {
    return api("/cache/clear", { method: "POST" });
  }

  // ---------- Composer ----------
  function buildComposer(container) {
    container.innerHTML =
      '<div class="composer">' +
        '<button class="icon-btn attach-btn" title="Attach PDF" aria-label="Attach PDF">' + svgIcon("plus") + "</button>" +
        '<textarea rows="1" placeholder="Ask anything..." aria-label="Message"></textarea>' +
        '<button class="send-btn" disabled aria-label="Send">' + svgIcon("send") + "</button>" +
      "</div>";
    wireComposer(container);
  }

  function wireComposer(container) {
    var textarea = container.querySelector("textarea");
    var sendBtn = container.querySelector(".send-btn");

    textarea.addEventListener("input", function () {
      sendBtn.disabled = textarea.value.trim() === "";
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + "px";
    });

    textarea.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submitPrompt(container);
      }
    });

    sendBtn.addEventListener("click", function () { submitPrompt(container); });

    var attachBtn = container.querySelector(".attach-btn");
    attachBtn.addEventListener("click", function () {
      document.getElementById("file-input").click();
    });
  }

  // ---------- Message rendering ----------
  function renderMessages() {
    var wrap = document.querySelector("#messages .messages-inner");
    wrap.innerHTML = "";
    currentSession().messages.forEach(function (m) {
      if (m.role === "user") renderUserMessage(m.content, false);
      else {
        var web = m.web;
        var chunks = m.chunks;
        if (chunks === undefined) {
          web = (m.source || "").indexOf("Web search") >= 0;
          chunks = web ? 1 : 5;
        }
        renderAssistantMessage(m.content, chunks, web, m.pipeline, false);
      }
    });
    scrollMessages();
  }

  function scrollMessages() {
    var box = document.getElementById("messages");
    box.scrollTop = box.scrollHeight;
  }

  function renderUserMessage(content, scroll) {
    var row = el("div", "msg user");
    var body = el("div", "msg-body");
    body.appendChild(el("div", "msg-label", "You"));
    body.appendChild(el("div", "msg-bubble", content));
    row.appendChild(body);
    document.querySelector("#messages .messages-inner").appendChild(row);
    if (scroll !== false) scrollMessages();
  }

  function renderAssistantMessage(content, chunks, web, pipeline, scroll) {
    var row = el("div", "msg assistant");
    var avatar = el("div", "msg-avatar", "AI");
    var body = el("div", "msg-body");
    body.appendChild(el("div", "msg-content", content));
    body.appendChild(buildSources(chunks, web));
    if (pipeline) body.appendChild(buildPipeline(pipeline));
    row.appendChild(avatar);
    row.appendChild(body);
    document.querySelector("#messages .messages-inner").appendChild(row);
    if (scroll !== false) scrollMessages();
  }

  function buildSources(chunks, web) {
    var wrap = el("div", "msg-sources");
    var chip = el("span", "chip");
    if (web) {
      chip.innerHTML = svgIcon("web");
      chip.appendChild(document.createTextNode("Web Search"));
    } else {
      chip.innerHTML = svgIcon("db");
      chip.appendChild(document.createTextNode(chunks + " document blocks"));
    }
    wrap.appendChild(chip);
    return wrap;
  }

  function buildPipeline(p) {
    var det = el("details", "pipeline");
    det.appendChild(el("summary", null, "Retrieval details"));
    var body = el("div", "pipeline-body");

    function row(name, innerHTML, cls) {
      var r = el("div", "pipe-row");
      r.appendChild(el("span", "pipe-name", name));
      var v = el("span", "pipe-val" + (cls ? " " + cls : ""));
      v.innerHTML = innerHTML;
      r.appendChild(v);
      return r;
    }

    var qText = p.query || "";
    body.appendChild(row("Query", "<span class=\"pipe-arrow\">" + svgIcon("arrow") + "</span><span>" + escapeHtml(qText.length > 60 ? qText.slice(0, 60) + "..." : qText) + "</span>"));

    if (p.web) {
      body.appendChild(row("Retrieval", "<span class=\"pipe-ok\">" + svgIcon("check") + "</span><span>No relevant local chunks</span>"));
      body.appendChild(row("Context Evaluation", "<span class=\"pipe-arrow\">" + svgIcon("arrow") + "</span><span>Rejected local context, using web fallback</span>"));
    } else {
      body.appendChild(row("Retrieval", "<span class=\"pipe-ok\">" + svgIcon("check") + "</span><span>" + p.chunks + " chunks found</span>"));
      body.appendChild(row("Context Evaluation", "<span class=\"pipe-ok\">" + svgIcon("check") + "</span><span>Relevant context</span>"));
    }
    body.appendChild(row("Generation", "<span class=\"pipe-ok\">" + svgIcon("check") + "</span><span>Answer generated</span>"));

    det.appendChild(body);
    return det;
  }

  function escapeHtml(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  // ---------- Loading state ----------
  function typingIndicator() {
    var row = el("div", "msg assistant");
    var avatar = el("div", "msg-avatar", "AI");
    var body = el("div", "msg-body");
    var line = el("div", "typing-line");
    var dots = el("div", "typing-dots");
    dots.appendChild(el("span"));
    dots.appendChild(el("span"));
    dots.appendChild(el("span"));
    var text = el("span", "typing-text", PIPELINE_STAGES[0]);
    line.appendChild(dots);
    line.appendChild(text);
    body.appendChild(line);
    row.appendChild(avatar);
    row.appendChild(body);
    document.querySelector("#messages .messages-inner").appendChild(row);
    scrollMessages();

    var stage = 0;
    var timer = setInterval(function () {
      if (stage < PIPELINE_STAGES.length - 1) {
        stage += 1;
        text.textContent = PIPELINE_STAGES[stage];
      }
    }, 1300);

    return {
      row: row,
      done: function () {
        clearInterval(timer);
        row.remove();
      }
    };
  }

  // ---------- Error state ----------
  function renderError(question, message) {
    var row = el("div", "msg assistant");
    var avatar = el("div", "msg-avatar", "AI");
    var body = el("div", "msg-body");
    var err = el("div", "msg-error", "Something went wrong");
    var detail = el("div", "msg-error-detail", "I couldn't generate an answer. " + message + " Please try again.");
    var retry = el("button", "retry-btn", "Retry");
    retry.addEventListener("click", function () {
      row.remove();
      ask(question);
    });
    body.appendChild(err);
    body.appendChild(detail);
    body.appendChild(retry);
    row.appendChild(avatar);
    row.appendChild(body);
    document.querySelector("#messages .messages-inner").appendChild(row);
    scrollMessages();
  }

  // ---------- Ask flow ----------
  function ask(question) {
    var topK = getTopK();
    var typing = typingIndicator();

    sendQuery(question, topK)
      .then(function (data) {
        var chunks = parseInt(data.chunks_used, 10) || 0;
        var web = chunks <= 1;
        typing.done();
        var session = currentSession();
        var pipeline = {
          query: question,
          chunks: web ? 0 : chunks,
          web: web
        };
        session.messages.push({ role: "assistant", content: data.answer, chunks: chunks, web: web, pipeline: pipeline });
        persist();
        renderAssistantMessage(data.answer, chunks, web, pipeline);
      })
      .catch(function (err) {
        typing.done();
        renderError(question, err.message);
      });
  }

  // ---------- Prompt flow ----------
  function submitPrompt(container) {
    var textarea = container.querySelector("textarea");
    var question = textarea.value.trim();
    if (!question) return;

    var session = currentSession();
    session.messages.push({ role: "user", content: question });
    if (session.title === "New Chat") {
      session.title = question.slice(0, 40);
    }
    session.updatedAt = Date.now();
    persist();

    textarea.value = "";
    var sendBtn = container.querySelector(".send-btn");
    sendBtn.disabled = true;
    textarea.style.height = "auto";
    textarea.focus();

    refreshView();
    renderMessages();
    ask(question);
  }

  // ---------- Views ----------
  function refreshView() {
    var session = currentSession();
    var subtitle = document.getElementById("chat-subtitle");
    if (session.messages.length === 0) {
      subtitle.classList.add("hidden");
      subtitle.textContent = "";
    } else {
      subtitle.textContent = session.title;
      subtitle.classList.remove("hidden");
    }
  }

  // ---------- Sidebar ----------
  function renderSidebar() {
    var pinned = [], recent = [];
    Object.keys(sessions).forEach(function (id) {
      var s = sessions[id];
      if (s.pinned) pinned.push(s); else recent.push(s);
    });
    function byUpdated(a, b) { return (b.updatedAt || 0) - (a.updatedAt || 0); }
    pinned.sort(byUpdated);
    recent.sort(byUpdated);

    var pinnedList = document.getElementById("pinned-list");
    var recentList = document.getElementById("recent-list");
    pinnedList.innerHTML = "";
    recentList.innerHTML = "";

    var hasPinned = pinned.length > 0;
    var hasRecent = recent.length > 0;
    document.getElementById("pinned-section").classList.toggle("hidden", !hasPinned);
    document.getElementById("recent-section").classList.toggle("hidden", !hasRecent);

    function item(s) {
      var btn = el("button", "conv-item" + (s.id === currentId ? " active" : ""));
      var icon = el("span", "conv-icon");
      icon.innerHTML = svgIcon("chat");
      btn.appendChild(icon);
      btn.appendChild(el("span", "conv-text", s.title));
      var pin = el("span", "conv-pin");
      pin.innerHTML = svgIcon("pin");
      pin.title = s.pinned ? "Unpin conversation" : "Pin conversation";
      pin.addEventListener("click", function (e) {
        e.stopPropagation();
        s.pinned = !s.pinned;
        persist();
        renderSidebar();
      });
      var del = el("span", "conv-del");
      del.innerHTML = svgIcon("del");
      del.title = "Delete conversation";
      del.addEventListener("click", function (e) {
        e.stopPropagation();
        delete sessions[s.id];
        if (currentId === s.id) {
          currentId = uid();
          sessions[currentId] = { id: currentId, title: "New Chat", pinned: false, messages: [] };
        }
        persist();
        renderSidebar();
        refreshView();
        renderMessages();
      });
      btn.appendChild(pin);
      btn.appendChild(del);
      btn.addEventListener("click", function () {
        currentId = s.id;
        persist();
        renderSidebar();
        refreshView();
        renderMessages();
      });
      return btn;
    }

    pinned.forEach(function (s) { pinnedList.appendChild(item(s)); });
    recent.forEach(function (s) { recentList.appendChild(item(s)); });
  }

  async function renderDocuments() {
    var list = document.getElementById("documents-list");
    list.innerHTML = "";
    try {
      var data = await api("/documents");
      var docs = data.documents || [];
      if (!docs.length) {
        list.appendChild(el("div", "doc-empty", "No documents yet"));
        return;
      }
      docs.forEach(function (d) {
        var row = el("div", "doc-item");
        var icon = el("span", "doc-icon");
        icon.innerHTML = svgIcon("doc");
        row.appendChild(icon);
        row.appendChild(el("span", "doc-name", d.filename));
        row.appendChild(el("span", "doc-chunks", d.chunks + " chunks"));
        list.appendChild(row);
      });
    } catch (e) {
      list.appendChild(el("div", "doc-empty", "Could not load documents"));
    }
  }

  function newChat() {
    currentId = uid();
    sessions[currentId] = { id: currentId, title: "New Chat", pinned: false, messages: [] };
    persist();
    renderSidebar();
    refreshView();
    renderMessages();
    closeSidebar();
    document.querySelector(".composer textarea").focus();
  }

  function clearChat() {
    var session = currentSession();
    session.messages = [];
    session.title = "New Chat";
    persist();
    renderSidebar();
    refreshView();
    renderMessages();
  }

  // ---------- Sidebar toggle ----------
  function openSidebar() { document.body.classList.add("sidebar-open"); }
  function closeSidebar() { document.body.classList.remove("sidebar-open"); }

  // ---------- Menu ----------
  function openMenu() {
    document.getElementById("menu-popup").classList.remove("hidden");
  }

  function closeMenu() {
    document.getElementById("menu-popup").classList.add("hidden");
  }

  // ---------- Evaluation ----------
  function openEvaluation() {
    var session = currentSession();
    var lastUser = null;
    for (var i = session.messages.length - 1; i >= 0; i--) {
      if (session.messages[i].role === "user") { lastUser = session.messages[i].content; break; }
    }
    if (!lastUser) {
      toast("Ask a question first", true);
      return;
    }

    document.getElementById("eval-loading").classList.remove("hidden");
    document.getElementById("eval-question").classList.add("hidden");
    document.getElementById("eval-metrics").innerHTML = "";
    document.getElementById("eval-modal").classList.remove("hidden");

    evaluateQuery(lastUser, getTopK())
      .then(function (data) {
        document.getElementById("eval-loading").classList.add("hidden");
        var q = document.getElementById("eval-question");
        q.textContent = lastUser;
        q.classList.remove("hidden");

        var metrics = document.getElementById("eval-metrics");
        metrics.innerHTML = "";
        function row(label, value, overall) {
          var r = el("div", "eval-row" + (overall ? " overall" : ""));
          r.appendChild(el("span", null, label));
          r.appendChild(el("span", "eval-score", value.toFixed(3)));
          metrics.appendChild(r);
        }
        row("Faithfulness", data.faithfulness);
        row("Answer Relevance", data.answer_relevance);
        row("Context Precision", data.context_precision);
        row("Overall Score", data.overall_score, true);
      })
      .catch(function (err) {
        document.getElementById("eval-loading").classList.add("hidden");
        document.getElementById("eval-question").classList.add("hidden");
        var metrics = document.getElementById("eval-metrics");
        metrics.innerHTML = "";
        metrics.appendChild(el("div", "msg-error-detail", "Evaluation failed: " + err.message));
      });
  }

  function closeEvaluation() {
    document.getElementById("eval-modal").classList.add("hidden");
  }

  // ---------- Settings ----------
  function openSettings() {
    document.getElementById("setting-api-key").value = getApiKey();
    document.getElementById("setting-topk").value = getTopK();
    document.getElementById("settings-modal").classList.remove("hidden");
    updateSettingsStatus();
  }

  function closeSettings() {
    document.getElementById("settings-modal").classList.add("hidden");
  }

  async function updateSettingsStatus() {
    var row = document.getElementById("setting-status");
    try {
      var res = await fetch("/health", { cache: "no-store" });
      var data = await res.json();
      row.innerHTML = "";
      var dot = el("span", "status-dot " + (res.ok ? "online" : "offline"));
      row.appendChild(dot);
      row.appendChild(document.createTextNode(
        res.ok ? "API online - cache: " + (data.cache_size || 0) + " entries" : "API offline"
      ));
    } catch (e) {
      row.innerHTML = "";
      var d = el("span", "status-dot offline");
      row.appendChild(d);
      row.appendChild(document.createTextNode("API offline"));
    }
  }

  // ---------- Upload ----------
  function handleFile(file) {
    if (!file) return;
    if (!/\.pdf$/i.test(file.name)) { toast("Only PDF files are allowed", true); return; }
    toast("Uploading " + file.name + "...");
    uploadPdf(file).then(function (data) {
      toast("Added " + data.chunks_inserted + " chunks to the knowledge base");
      renderDocuments();
    }).catch(function (err) {
      toast(err.message, true);
    });
  }

  // ---------- Init ----------
  function init() {
    buildComposer(document.getElementById("chat-composer"));

    document.getElementById("new-chat-btn").addEventListener("click", newChat);
    document.getElementById("upload-btn").addEventListener("click", function () {
      document.getElementById("file-input").click();
    });

    document.getElementById("sidebar-open").addEventListener("click", openSidebar);
    document.getElementById("sidebar-close").addEventListener("click", closeSidebar);
    document.getElementById("sidebar-backdrop").addEventListener("click", closeSidebar);

    // Menu
    document.getElementById("menu-btn").addEventListener("click", function (e) {
      e.stopPropagation();
      var popup = document.getElementById("menu-popup");
      if (popup.classList.contains("hidden")) openMenu(); else closeMenu();
    });
    document.addEventListener("click", function (e) {
      if (!document.getElementById("menu-popup").classList.contains("hidden") &&
          !document.getElementById("menu-popup").contains(e.target) &&
          e.target.id !== "menu-btn") {
        closeMenu();
      }
    });
    document.querySelectorAll("#menu-popup button").forEach(function (b) {
      b.addEventListener("click", function () {
        closeMenu();
        var act = b.dataset.act;
        if (act === "settings") openSettings();
        else if (act === "clear") clearChat();
        else if (act === "evaluate") openEvaluation();
      });
    });

    // Settings
    document.querySelectorAll("#settings-modal .modal-close, #settings-modal [data-close='true']").forEach(function (b) {
      b.addEventListener("click", closeSettings);
    });
    document.getElementById("settings-modal").addEventListener("click", function (e) {
      if (e.target === this) closeSettings();
    });
    document.getElementById("save-settings").addEventListener("click", function () {
      localStorage.setItem(STORE.apiKey, document.getElementById("setting-api-key").value.trim());
      localStorage.setItem(STORE.topK, String(parseInt(document.getElementById("setting-topk").value, 10) || 3));
      toast("Settings saved");
      closeSettings();
    });
    document.getElementById("clear-cache").addEventListener("click", function () {
      clearCache().then(function (d) {
        toast(d.message || "Cache cleared");
        updateSettingsStatus();
      }).catch(function (err) { toast(err.message, true); });
    });

    // Evaluation modal
    document.querySelectorAll("#eval-modal .modal-close, #eval-modal [data-eval-close='true']").forEach(function (b) {
      b.addEventListener("click", closeEvaluation);
    });
    document.getElementById("eval-modal").addEventListener("click", function (e) {
      if (e.target === this) closeEvaluation();
    });

    // Upload
    document.getElementById("file-input").addEventListener("change", function (e) {
      var file = e.target.files[0];
      e.target.value = "";
      handleFile(file);
    });

    // Keyboard
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (!document.getElementById("settings-modal").classList.contains("hidden")) closeSettings();
        if (!document.getElementById("eval-modal").classList.contains("hidden")) closeEvaluation();
        closeMenu();
      }
    });

    renderSidebar();
    refreshView();
    renderMessages();
    renderDocuments();
    checkStatus();
    setInterval(checkStatus, 15000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();