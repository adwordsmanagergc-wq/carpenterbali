(function () {
  "use strict";
  var doc = document.documentElement;
  var body = document.body;

  // Mobile navigation
  var toggle = document.querySelector(".nav-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = body.classList.toggle("nav-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  // Close language menu when clicking outside
  document.addEventListener("click", function (e) {
    document.querySelectorAll("details.lang[open]").forEach(function (d) {
      if (!d.contains(e.target)) d.removeAttribute("open");
    });
  });

  // Remember an explicit language choice
  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function read(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  document.querySelectorAll("a[data-lang]").forEach(function (a) {
    a.addEventListener("click", function () { store("cb-lang", a.getAttribute("data-lang")); });
  });

  // Suggest the visitor's language (no automatic redirect — better for SEO and users)
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
      var f = form.elements;
      var lines = [form.getAttribute("data-greeting") || ""];
      function add(label, el) { if (el && el.value) lines.push(label + ": " + el.value); }
      add(form.querySelector('label input[name="name"]').parentNode.firstChild.textContent.trim(), f.name);
      add(form.querySelector('select[name="service"]').parentNode.firstChild.textContent.trim(), f.service);
      add(form.querySelector('select[name="area"]').parentNode.firstChild.textContent.trim(), f.area);
      if (f.text.value) lines.push("", f.text.value);
      var url = "https://wa.me/" + form.getAttribute("data-wa") + "?text=" + encodeURIComponent(lines.join("\n").trim());
      window.open(url, "_blank", "noopener");
    });
  });

  doc.classList.add("js");
})();
