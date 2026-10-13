(function () {
  "use strict";
  var body = document.body;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");

  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function read(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  // Mobile navigation
  var toggle = document.querySelector(".nav-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && body.classList.contains("nav-open")) {
        body.classList.remove("nav-open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });
  }

  // Language menu: close on outside click or Escape, remember explicit choice
  document.addEventListener("click", function (e) {
    document.querySelectorAll("details.lang[open]").forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute("open"); });
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") document.querySelectorAll("details.lang[open]").forEach(function (d) { d.removeAttribute("open"); });
  });
  document.querySelectorAll("a[data-lang]").forEach(function (a) {
    a.addEventListener("click", function () { store("cb-lang", a.getAttribute("data-lang")); });
  });

  // Scroll reveals (once)
  var rv = document.querySelectorAll(".rv");
  if ("IntersectionObserver" in window && !reduce.matches) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    rv.forEach(function (el) { io.observe(el); });
  } else {
    rv.forEach(function (el) { el.classList.add("in"); });
  }

  // Material explorer tabs (progressive: all panels show without JS)
  document.querySelectorAll(".mx").forEach(function (mx) {
    var tabs = Array.prototype.slice.call(mx.querySelectorAll('[role="tab"]'));
    var panels = Array.prototype.slice.call(mx.querySelectorAll('[role="tabpanel"]'));
    function select(i, focus) {
      tabs.forEach(function (t, j) {
        var on = i === j;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
        panels[j].hidden = !on;
        panels[j].classList.remove("on");
      });
      // next frame so the bars animate from zero
      requestAnimationFrame(function () { requestAnimationFrame(function () { panels[i].classList.add("on"); }); });
      if (focus) tabs[i].focus();
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { select(i, false); });
      t.addEventListener("keydown", function (e) {
        var k = e.key, n = tabs.length;
        if (k === "ArrowRight" || k === "ArrowDown") { e.preventDefault(); select((i + 1) % n, true); }
        if (k === "ArrowLeft" || k === "ArrowUp") { e.preventDefault(); select((i - 1 + n) % n, true); }
        if (k === "Home") { e.preventDefault(); select(0, true); }
        if (k === "End") { e.preventDefault(); select(n - 1, true); }
      });
    });
    mx.classList.add("ready");
    select(0, false);
  });

  // Service index: photo preview follows the cursor (desktop, motion allowed)
  document.querySelectorAll(".ix").forEach(function (ix) {
    var pv = ix.querySelector(".ix-preview");
    if (!pv || !finePointer.matches || reduce.matches) return;
    var pimg = pv.querySelector("img");
    var x = 0, y = 0, tx = 0, ty = 0, raf = null, active = false;
    var w = function () { return pv.offsetWidth; }, h = function () { return pv.offsetHeight; };
    function loop() {
      x += (tx - x) * 0.16; y += (ty - y) * 0.16;
      pv.style.transform = "translate3d(" + x + "px," + y + "px,0)";
      if (active || Math.abs(tx - x) > 0.5 || Math.abs(ty - y) > 0.5) raf = requestAnimationFrame(loop); else raf = null;
    }
    function target(e) {
      tx = Math.min(e.clientX + 28, window.innerWidth - w() - 12);
      ty = Math.min(Math.max(e.clientY - h() / 2, 12), window.innerHeight - h() - 12);
    }
    ix.querySelectorAll("a[data-img]").forEach(function (a) {
      a.addEventListener("mouseenter", function (e) {
        var src = a.getAttribute("data-img");
        if (pimg.getAttribute("src") !== src) pimg.src = src;
        target(e);
        if (!active) { x = tx; y = ty; }
        active = true;
        pv.classList.add("show");
        if (!raf) raf = requestAnimationFrame(loop);
      });
      a.addEventListener("mousemove", target);
    });
    ix.addEventListener("mouseleave", function () { active = false; pv.classList.remove("show"); });
  });

  // Suggest the visitor's language (no automatic redirect)
  var current = body.getAttribute("data-lang");
  var i18n = {};
  try { i18n = JSON.parse(document.getElementById("i18n").textContent); } catch (e) {}
  if (!read("cb-lang") && !read("cb-lang-dismissed")) {
    var prefs = (navigator.languages || [navigator.language || ""]).map(function (l) { return String(l).slice(0, 2).toLowerCase(); });
    var want = null;
    for (var i = 0; i < prefs.length; i++) { if (i18n[prefs[i]]) { want = prefs[i]; break; } }
    if (want && want !== current) {
      var alt = document.querySelector('link[rel="alternate"][hreflang="' + want + '"]');
      if (alt) {
        var t = i18n[want];
        var bar = document.createElement("div");
        bar.className = "lang-banner";
        bar.setAttribute("lang", want);
        bar.innerHTML = '<span></span><a></a><button type="button">×</button>';
        bar.querySelector("span").textContent = t[0];
        var link = bar.querySelector("a");
        link.textContent = t[1];
        link.href = new URL(alt.href).pathname;
        link.addEventListener("click", function () { store("cb-lang", want); });
        var btn = bar.querySelector("button");
        btn.setAttribute("aria-label", t[2]);
        btn.addEventListener("click", function () { store("cb-lang-dismissed", "1"); bar.remove(); });
        body.appendChild(bar);
      }
    }
  }

  // Quote form → WhatsApp message
  document.querySelectorAll(".quote-form").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var lines = [form.getAttribute("data-greeting") || ""];
      ["name", "service", "area"].forEach(function (n) {
        var el = form.querySelector('[name="' + n + '"]');
        if (el && el.value) lines.push(el.closest("label").firstChild.textContent.trim() + ": " + el.value);
      });
      var msg = form.querySelector('[name="text"]');
      if (msg && msg.value) lines.push("", msg.value);
      window.open("https://wa.me/" + form.getAttribute("data-wa") + "?text=" + encodeURIComponent(lines.join("\n").trim()), "_blank", "noopener");
    });
  });
})();
