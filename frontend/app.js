/* CRAG Assistant — chat UI */
(function () {
  "use strict";

  var STORE = {
    sessions: "crag_sessions",
    current: "crag_current",
    apiKey: "crag_api_key",
    topK: "crag_topk"
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
    setTimeout(function () { t.remove(); }, 3200);
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

  // ---------- Composer ----------
  function svgIcon(name) {
    var icons = {
      plus: '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z"/></svg>',
      send: '<svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path fill="currentColor" d="m3 20 18-8L3 4v6l12 2-12 2v6Z"/></svg>'
    };
    return icons[name] || "";
  }

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

  // ---------- Message rendering ----------
  function renderMessages() {
    var wrap = document.getElementById("messages");
    wrap.innerHTML = "";
    var msgs = currentSession().messages;
    if (!msgs.length) return;
    msgs.forEach(function (m) { appendMessage(m, false); });
    wrap.scrollTop = wrap.scrollHeight;
  }

  function appendMessage(msg, scroll) {
    var wrap = document.getElementById("messages");
    var row = el("div", "msg");
    var avatar = el("div", "msg-avatar " + (msg.role === "user" ? "user" : "assistant"));
    avatar.textContent = msg.role === "user" ? "You" : "AI";
    var body = el("div", "msg-body");
    var content = el("div", "msg-content");
    content.textContent = msg.content;
    body.appendChild(content);
    if (msg.role === "assistant" && msg.source) {
      body.appendChild(el("div", "msg-source", msg.source));
    }
    row.appendChild(avatar);
    row.appendChild(body);
    wrap.appendChild(row);
    if (scroll !== false) wrap.scrollTop = wrap.scrollHeight;
  }

  function typingIndicator() {
    var row = el("div", "msg");
    var avatar = el("div", "msg-avatar assistant", "AI");
    var body = el("div", "msg-body");
    var typing = el("div", "typing");
    typing.appendChild(el("span"));
    typing.appendChild(el("span"));
    typing.appendChild(el("span"));
    body.appendChild(typing);
    row.appendChild(avatar);
    row.appendChild(body);
    document.getElementById("messages").appendChild(row);
    document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
    return row;
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

    var topK = getTopK();

    textarea.value = "";
    var sendBtn = container.querySelector(".send-btn");
    sendBtn.disabled = true;
    textarea.style.height = "auto";
    textarea.focus();

    document.getElementById("chat-title").textContent = session.title;
    renderSidebar();
    showChat();
    renderMessages();
    appendMessage({ role: "user", content: question });

    var typing = typingIndicator();

    sendQuery(question, topK)
      .then(function (data) {
        var source;
        var chunks = parseInt(data.chunks_used, 10) || 0;
        if (chunks <= 1) {
          source = "Web search fallback (DuckDuckGo)";
        } else {
          source = "Grounded in " + chunks + " document blocks";
        }
        session.messages.push({ role: "assistant", content: data.answer, source: source });
        persist();
        typing.remove();
        appendMessage({ role: "assistant", content: data.answer, source: source });
      })
      .catch(function (err) {
        typing.remove();
        toast(err.message, true);
      });
  }

  // ---------- Views ----------
  function showWelcome() {
    document.getElementById("welcome-view").classList.remove("hidden");
    document.getElementById("chat-view").classList.add("hidden");
  }

  function showChat() {
    document.getElementById("welcome-view").classList.add("hidden");
    document.getElementById("chat-view").classList.remove("hidden");
  }

  function refreshView() {
    var session = currentSession();
    document.getElementById("chat-title").textContent = session.title;
    if (session.messages.length === 0) {
      showWelcome();
    } else {
      showChat();
      renderMessages();
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
      btn.appendChild(el("span", "conv-text", s.title));
      var pin = el("span", "conv-pin", s.pinned ? "Unpin" : "Pin");
      pin.title = s.pinned ? "Unpin conversation" : "Pin conversation";
      pin.addEventListener("click", function (e) {
        e.stopPropagation();
        s.pinned = !s.pinned;
        persist();
        renderSidebar();
      });
      var del = el("span", "conv-del", "Delete");
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
      });
      btn.appendChild(pin);
      btn.appendChild(del);
      btn.addEventListener("click", function () {
        currentId = s.id;
        persist();
        renderSidebar();
        refreshView();
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
    closeSidebar();
    document.querySelector(".composer textarea").focus();
  }

  // ---------- Sidebar toggle ----------
  function openSidebar() { document.body.classList.add("sidebar-open"); }
  function closeSidebar() { document.body.classList.remove("sidebar-open"); }

  // ---------- Settings modal ----------
  function openSettings() {
    document.getElementById("setting-api-key").value = getApiKey();
    document.getElementById("setting-topk").value = getTopK();
    document.getElementById("settings-modal").classList.remove("hidden");
    loadDocuments();
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

  async function loadDocuments() {
    var list = document.getElementById("documents-list");
    list.innerHTML = "";
    try {
      var data = await api("/documents");
      var docs = data.documents || [];
      if (!docs.length) {
        list.appendChild(el("div", "doc-empty", "No documents in the knowledge base yet."));
        return;
      }
      docs.forEach(function (d) {
        var row = el("div", "doc-item");
        row.appendChild(el("span", "doc-name", d.filename));
        row.appendChild(el("span", "doc-chunks", d.chunks + " chunks"));
        list.appendChild(row);
      });
    } catch (e) {
      list.appendChild(el("div", "doc-empty", "Could not load documents."));
    }
  }

  // ---------- Init ----------
  function init() {
    buildComposer(document.getElementById("welcome-composer"));
    buildComposer(document.getElementById("chat-composer"));

    document.getElementById("new-chat-btn").addEventListener("click", newChat);

    document.getElementById("sidebar-open").addEventListener("click", openSidebar);
    document.getElementById("sidebar-close").addEventListener("click", closeSidebar);
    document.getElementById("sidebar-backdrop").addEventListener("click", closeSidebar);

    // Settings
    document.getElementById("settings-btn").addEventListener("click", openSettings);
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

    // Upload
    document.getElementById("file-input").addEventListener("change", function (e) {
      var file = e.target.files[0];
      e.target.value = "";
      if (!file) return;
      if (!/\.pdf$/i.test(file.name)) { toast("Only PDF files are allowed", true); return; }
      toast("Uploading " + file.name + "...");
      uploadPdf(file).then(function (data) {
        toast("Added " + data.chunks_inserted + " chunks to the knowledge base");
      }).catch(function (err) {
        toast(err.message, true);
      });
    });

    // Keyboard
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !document.getElementById("settings-modal").classList.contains("hidden")) {
        closeSettings();
      }
    });

    renderSidebar();
    refreshView();
    checkStatus();
    setInterval(checkStatus, 15000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();