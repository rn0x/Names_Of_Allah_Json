"use strict";

const DATA_URL = "downloads/asma_allah_alhusna_saeed_alqahtani.json";
const grid = document.getElementById("names");
const input = document.getElementById("q");
const count = document.getElementById("count");
const errorBox = document.getElementById("error");

let records = [];

function normalize(s) {
  return (s || "")
    .replace(/[ً-ٰٖـ]/g, "")
    .replace(/[أإآٱ]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي");
}

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function evidenceList(items) {
  if (!items.length) return "<p>لا يوجد.</p>";
  return items.map(e =>
    `<blockquote>${esc(e.text)}${e.source ? `<cite>المصدر: ${esc(e.source)}</cite>` : ""}</blockquote>`
  ).join("");
}

function strList(items) {
  if (!items.length) return "<p>لا يوجد.</p>";
  return "<ul>" + items.map(s => `<li>${esc(s)}</li>`).join("") + "</ul>";
}

function card(r) {
  const related = r.related_names.length
    ? `<p><strong>أسماء مرتبطة:</strong> ${esc(r.related_names.join("، "))}</p>` : "";
  return `
  <article class="card" data-id="${r.id}">
    <h3>${r.id}. ${esc(r.name)} <small>${esc(r.name_arabic || "")}</small></h3>
    <p class="meaning">${esc(r.meaning || "")}</p>
    <details>
      <summary>الشرح المختصر</summary>
      <p>${esc(r.explanation || "")}</p>
      <p class="ref"><a href="${esc(r.book_reference.url)}" target="_blank" rel="noopener">المرجع في الكتاب (صفحة ${esc(r.book_reference.page)})</a></p>
    </details>
    <details>
      <summary>الأدلة القرآنية (${r.quran_evidence.length})</summary>
      ${evidenceList(r.quran_evidence)}
    </details>
    <details>
      <summary>الأحاديث (${r.hadith_evidence.length})</summary>
      ${evidenceList(r.hadith_evidence)}
    </details>
    <details>
      <summary>أقوال العلماء والمصادر</summary>
      ${strList(r.scholarly_statements)}
      ${strList(r.sources)}
    </details>
    ${related}
  </article>`;
}

function render(list) {
  grid.innerHTML = list.map(card).join("");
  count.textContent = `عرض ${list.length} من أصل ${records.length} اسماً`;
}

function applyFilter() {
  const q = normalize(input.value.trim());
  if (!q) return render(records);
  render(records.filter(r =>
    normalize(r.name).includes(q) ||
    normalize(r.name_arabic).includes(q) ||
    normalize(r.meaning).includes(q)
  ));
}

fetch(DATA_URL)
  .then(res => { if (!res.ok) throw new Error(res.status); return res.json(); })
  .then(data => {
    records = data;
    const sum = k => data.reduce((a, r) => a + (r[k] || []).length, 0);
    document.querySelector('[data-stat="quran"]').textContent = sum("quran_evidence");
    document.querySelector('[data-stat="hadith"]').textContent = sum("hadith_evidence");
    document.querySelector('[data-stat="sources"]').textContent = sum("sources");
    render(records);
  })
  .catch(() => { errorBox.hidden = false; });

input.addEventListener("input", applyFilter);

// Live per-asset download counts from the GitHub release (graceful fallback).
fetch("https://api.github.com/repos/rn0x/Names_Of_Allah_Json/releases/latest")
  .then(res => (res.ok ? res.json() : null))
  .then(rel => {
    if (!rel || !Array.isArray(rel.assets)) return;
    const fmt = n => Number(n || 0).toLocaleString("ar-EG");
    rel.assets.forEach(a => {
      document.querySelectorAll(`[data-dl="${a.name}"]`).forEach(el => {
        el.textContent = fmt(a.download_count);
      });
    });
  })
  .catch(() => {});
