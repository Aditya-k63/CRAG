/* CRAG Assistant — minimal chat UI */
(function () {
  "use strict";

  var STORE = {
    sessions: "crag_sessions",
    current: "crag_current",
    apiKey: "crag_api_key",
    topK: "crag_topk",
    lastEval: "crag_last_eval",
    bgEval: "crag_bg_eval"
  };

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

  function getBgEval() {
    return localStorage.getItem(STORE.bgEval) === "1";
  }

  var lastBgEvalAt = 0;

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
      pin: '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path fill="currentColor" d="M16 9V4h2V2H6v2h2v5c0 1.7-1.3 3-3 3v2h5.5v6l1.5 1 1.5-1v-6H19v-2c-1.7 0-3-1.3-3-3Z"/></svg>',
      del: '<svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path fill="currentColor" d="M9 3h6l1 2h4v2H4V5h4l1-2ZM6 9h12l-1 12H7L6 9Zm3 2v8h2v-8H9Zm4 0v8h2v-8h-2Z"/></svg>',
      pdf: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M14 3H7a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V8l-4-5Zm-1 1.5L16.5 8H13V4.5ZM9 12h6v1.5H9V12Zm0 3.5h6V17H9v-1.5Z"/></svg>',
      web: '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2Zm7.9 9h-3.1a15.9 15.9 0 0 0-1.5-6.3A8 8 0 0 1 19.9 11ZM12 4a14 14 0 0 1 2.3 7H9.7A14 14 0 0 1 12 4Zm-7.9 7a8 8 0 0 1 4.6-6.3A15.9 15.9 0 0 0 7.2 11H4.1ZM4 13h3.1c.2 2.4.7 4.5 1.5 6.3A8 8 0 0 1 4 13Zm3.1-1H4.1a8 8 0 0 1 4.6-6.3A15.9 15.9 0 0 0 7.1 12Zm4.9 9a14 14 0 0 1-2.3-7h4.6a14 14 0 0 1-2.3 7Zm1.1-9H9.9a16 16 0 0 1 .4-7h3.4a16 16 0 0 1 .4 7Zm1 8.3a15.9 15.9 0 0 0 1.5-6.3h3.1a8 8 0 0 1-4.6 6.3ZM16.9 12A15.9 15.9 0 0 1 15.4 5.7 8 8 0 0 1 20 12h-3.1Z"/></svg>'
    };
    return icons[name] || "";
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
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

  // ---------- Source modal ----------
  function openSourceModal(name, text) {
    document.getElementById("source-modal-title").textContent = name;
    document.getElementById("source-modal-text").textContent = text || "";
    document.getElementById("source-modal").classList.remove("hidden");
  }

  function closeSourceModal() {
    document.getElementById("source-modal").classList.add("hidden");
  }

  // ---------- Message rendering ----------
  function renderUserMessage(content, scroll) {
    var row = el("div", "msg user");
    var body = el("div", "msg-body");
    body.appendChild(el("div", "msg-label", "You"));
    body.appendChild(el("div", "msg-bubble", content));
    row.appendChild(body);
    document.querySelector("#messages .messages-inner").appendChild(row);
    if (scroll !== false) scrollMessages();
  }

  function renderAssistantMessage(content, sources, scroll) {
    var row = el("div", "msg assistant");
    var avatar = el("div", "msg-avatar", "AI");
    var body = el("div", "msg-body");
    body.appendChild(el("div", "msg-content", content));
    var srcs = buildSources(sources);
    if (srcs) body.appendChild(srcs);
    row.appendChild(avatar);
    row.appendChild(body);
    document.querySelector("#messages .messages-inner").appendChild(row);
    if (scroll !== false) scrollMessages();
  }

  function buildSources(sources) {
    if (!sources || !sources.length) return null;
    var wrap = el("div", "msg-sources");
    wrap.appendChild(el("div", "sources-title", "Source"));
    sources.forEach(function (s) {
      var item = el("span", "source-item");
      if (s.kind === "web") {
        item.innerHTML = svgIcon("web");
        var label = el("span", "source-label", s.title || s.url || "Web search");
        item.appendChild(label);
        item.addEventListener("click", function () {
          if (s.url) window.open(s.url, "_blank", "noopener");
        });
      } else {
        item.innerHTML = svgIcon("pdf");
        var plabel = el("span", "source-label", s.name || "Document");
        item.appendChild(plabel);
        item.addEventListener("click", function () {
          openSourceModal(s.name || "Document", s.text || "");
        });
      }
      wrap.appendChild(item);
    });
    return wrap;
  }

  function typingIndicator() {
    var row = el("div", "msg assistant");
    var avatar = el("div", "msg-avatar", "AI");
    var body = el("div", "msg-body");
    var line = el("div", "typing-line");
    var dots = el("span", "typing-dots");
    dots.appendChild(el("span"));
    dots.appendChild(el("span"));
    dots.appendChild(el("span"));
    line.appendChild(dots);
    line.appendChild(el("span", "typing-text", "Thinking..."));
    body.appendChild(line);
    row.appendChild(avatar);
    row.appendChild(body);
    document.querySelector("#messages .messages-inner").appendChild(row);
    scrollMessages();
    return {
      done: function () { row.remove(); }
    };
  }

  function renderError(question, message) {
    var row = el("div", "msg assistant");
    var avatar = el("div", "msg-avatar", "AI");
    var body = el("div", "msg-body");
    var err = el("div", "msg-error", "Something went wrong");
    var detail = el("div", "msg-error-detail", message);
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
        typing.done();
        if (/^Error generating final response/.test(data.answer)) {
          renderError(question, data.answer);
          return;
        }
        var sources = normalizeSources(data.sources, data.chunks_used);
        var session = currentSession();
        session.messages.push({
          role: "assistant",
          content: data.answer,
          sources: sources
        });
        persist();
        renderAssistantMessage(data.answer, sources);
        runBackgroundEvaluation(question, topK);
      })
      .catch(function (err) {
        typing.done();
        renderError(question, err.message);
      });
  }

  // Old messages may not have `sources`; derive a best-effort equivalent.
  function normalizeSources(sources, chunksUsed) {
    if (sources && sources.length) return sources;
    if (chunksUsed && chunksUsed > 1) {
      return [{ kind: "pdf", name: "Document source", text: "" }];
    }
    return [{ kind: "web", title: "Web search", url: "" }];
  }

  // Evaluation runs silently in the background — never shown in the UI.
  // Disabled by default because it re-runs the pipeline and doubles API token usage.
  function runBackgroundEvaluation(question, topK) {
    if (!getBgEval()) return;
    var now = Date.now();
    if (now - lastBgEvalAt < 60000) return; // at most once per minute
    lastBgEvalAt = now;
    evaluateQuery(question, topK)
      .then(function (data) {
        var scores = {
          faithfulness: data.faithfulness,
          answer_relevance: data.answer_relevance,
          context_precision: data.context_precision,
          overall_score: data.overall_score
        };
        save(STORE.lastEval, scores);
        console.log("[CRAG] background evaluation:", scores);
      })
      .catch(function (err) {
        console.log("[CRAG] background evaluation skipped:", err.message);
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
    var empty = document.getElementById("empty-state");
    if (session.messages.length === 0) {
      subtitle.classList.add("hidden");
      subtitle.textContent = "";
      empty.classList.remove("hidden");
    } else {
      subtitle.textContent = session.title;
      subtitle.classList.remove("hidden");
      empty.classList.add("hidden");
    }
  }

  function renderMessages() {
    var wrap = document.querySelector("#messages .messages-inner");
    var empty = document.getElementById("empty-state");
    wrap.innerHTML = "";
    if (empty) wrap.appendChild(empty);
    currentSession().messages.forEach(function (m) {
      if (m.role === "user") renderUserMessage(m.content, false);
      else {
        var sources = m.sources || normalizeSources(null, m.chunks_used);
        renderAssistantMessage(m.content, sources, false);
      }
    });
    scrollMessages();
  }

  function scrollMessages() {
    var messages = document.getElementById("messages");
    if (messages) messages.scrollTop = messages.scrollHeight;
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

    document.getElementById("pinned-section").classList.toggle("hidden", pinned.length === 0);
    document.getElementById("recent-section").classList.toggle("hidden", recent.length === 0);

    function item(s) {
      var btn = el("button", "conv-item" + (s.id === currentId ? " active" : ""));
      btn.appendChild(el("span", "conv-title", s.title));
      var pin = el("span");
      pin.innerHTML = svgIcon("pin");
      pin.title = s.pinned ? "Unpin conversation" : "Pin conversation";
      pin.addEventListener("click", function (e) {
        e.stopPropagation();
        s.pinned = !s.pinned;
        persist();
        renderSidebar();
      });
      var del = el("span");
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

  // ---------- Settings ----------
  function openSettings() {
    document.getElementById("setting-api-key").value = getApiKey();
    document.getElementById("setting-topk").value = String(getTopK());
    document.getElementById("setting-bg-eval").checked = getBgEval();
    document.getElementById("settings-modal").classList.remove("hidden");
  }

  function closeSettings() {
    document.getElementById("settings-modal").classList.add("hidden");
  }

  // ---------- Upload ----------
  async function handleFile(file) {
    if (!file) return;
    if (!/\.pdf$/i.test(file.name)) {
      toast("Only PDF files allowed", true);
      return;
    }
    toast("Uploading " + file.name + "...");
    try {
      var data = await uploadPdf(file);
      toast(data.message || "Upload complete");
    } catch (err) {
      toast(err.message, true);
    }
  }

  // ---------- Init ----------
  function init() {
    buildComposer(document.getElementById("chat-composer"));

    document.getElementById("new-chat-btn").addEventListener("click", newChat);

    // Menu
    document.getElementById("menu-btn").addEventListener("click", function (e) {
      var popup = document.getElementById("menu-popup");
      if (popup.classList.contains("hidden")) openMenu(); else closeMenu();
      e.stopPropagation();
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
      localStorage.setItem(STORE.bgEval, document.getElementById("setting-bg-eval").checked ? "1" : "0");
      toast("Settings saved");
      closeSettings();
    });
    document.getElementById("clear-cache").addEventListener("click", function () {
      clearCache().then(function (d) {
        toast(d.message || "Cache cleared");
      }).catch(function (err) { toast(err.message, true); });
    });

    // Source modal
    document.querySelectorAll("#source-modal .modal-close, #source-modal [data-source-close='true']").forEach(function (b) {
      b.addEventListener("click", closeSourceModal);
    });
    document.getElementById("source-modal").addEventListener("click", function (e) {
      if (e.target === this) closeSourceModal();
    });

    // Upload
    document.getElementById("file-input").addEventListener("change", function (e) {
      var file = e.target.files[0];
      e.target.value = "";
      handleFile(file);
    });

    // Sidebar toggle
    document.getElementById("sidebar-open").addEventListener("click", openSidebar);
    document.getElementById("sidebar-close").addEventListener("click", closeSidebar);
    document.getElementById("sidebar-backdrop").addEventListener("click", closeSidebar);

    // Keyboard
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        if (!document.getElementById("settings-modal").classList.contains("hidden")) closeSettings();
        if (!document.getElementById("source-modal").classList.contains("hidden")) closeSourceModal();
        closeMenu();
      }
    });

    renderSidebar();
    refreshView();
    renderMessages();
    checkStatus();
  }

  document.addEventListener("DOMContentLoaded", init);
})();