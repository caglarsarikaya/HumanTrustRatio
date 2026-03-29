(() => {
  const root       = document.getElementById("result-root");
  const loading    = document.getElementById("loading");
  const report     = document.getElementById("report");
  const analysisId = root.dataset.id;

  /* ── helpers ────────────────────────────────────────────── */

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function scoreColor(score) {
    if (score >= 75) return "text-mint-600";
    if (score >= 50) return "text-amber-500";
    return "text-red-500";
  }

  function ringColor(score) {
    if (score >= 75) return "stroke-mint-500";
    if (score >= 50) return "stroke-amber-400";
    return "stroke-red-400";
  }

  function barBg(score) {
    if (score >= 75) return "bg-mint-500";
    if (score >= 50) return "bg-amber-400";
    return "bg-red-400";
  }

  function scoreBadgeClass(score) {
    if (score >= 7.5) return "text-mint-600 bg-mint-50";
    if (score >= 5) return "text-amber-500 bg-amber-50";
    return "text-red-500 bg-red-50";
  }

  /* ── accordion builder ─────────────────────────────────── */

  function accordion(title, badge, body) {
    return `
      <details class="group rounded-2xl bg-white border border-gray-200 shadow-sm overflow-hidden">
        <summary class="flex items-center justify-between gap-3 cursor-pointer px-6 py-5
                        select-none list-none hover:bg-gray-50 transition">
          <div class="flex items-center gap-3">
            <h2 class="text-lg font-bold text-gray-900">${title}</h2>
            ${badge ? `<span class="text-xs font-medium px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-600 border border-brand-200">${badge}</span>` : ""}
          </div>
          <svg class="h-5 w-5 text-gray-400 transition-transform group-open:rotate-180" fill="none"
               viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
          </svg>
        </summary>
        <div class="px-6 pb-6 border-t border-gray-100 pt-4">
          ${body}
        </div>
      </details>`;
  }

  /* ── section builders ──────────────────────────────────── */

  function buildScoreGauge(score) {
    const pct  = Math.max(0, Math.min(100, score));
    const dash = (pct / 100) * 471.2;
    return `
      <div class="flex flex-col items-center">
        <svg width="180" height="180" viewBox="0 0 180 180">
          <circle cx="90" cy="90" r="75" fill="none" stroke-width="12"
                  class="stroke-gray-200"/>
          <circle cx="90" cy="90" r="75" fill="none" stroke-width="12"
                  stroke-dasharray="${dash} 999" stroke-linecap="round"
                  transform="rotate(-90 90 90)"
                  class="${ringColor(pct)} transition-all duration-700"/>
          <text x="90" y="96" text-anchor="middle"
                class="fill-current ${scoreColor(pct)} font-bold"
                style="font-size:40px">${Math.round(pct)}</text>
        </svg>
        <p class="mt-3 text-sm text-gray-500 font-medium">Overall Trust Score</p>
      </div>`;
  }

  function buildResumeText(text) {
    if (!text) return "";
    const lines = esc(text).replace(/\n/g, "<br>");
    return accordion(
      "Parsed Resume Text",
      `${text.length.toLocaleString()} chars`,
      `<div class="text-sm text-gray-600 leading-relaxed max-h-96 overflow-y-auto font-mono bg-gray-50 rounded-xl p-4">${lines}</div>`
    );
  }

  function buildProfile(p) {
    if (!p || !p.full_name) return "";

    let rows = `
      <div class="grid sm:grid-cols-2 gap-3 text-sm">
        <div><span class="text-gray-400 font-medium">Name:</span> <span class="text-gray-800">${esc(p.full_name)}</span></div>
        <div><span class="text-gray-400 font-medium">Title:</span> <span class="text-gray-800">${esc(p.title || "\u2014")}</span></div>
        <div><span class="text-gray-400 font-medium">Email:</span> <span class="text-gray-800">${esc(p.email || "\u2014")}</span></div>
        <div><span class="text-gray-400 font-medium">Location:</span> <span class="text-gray-800">${esc(p.location || "\u2014")}</span></div>
        <div><span class="text-gray-400 font-medium">Phone:</span> <span class="text-gray-800">${esc(p.phone || "\u2014")}</span></div>
      </div>`;

    if (p.skills && p.skills.length) {
      rows += `
        <div class="mt-4">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Skills</p>
          <div class="flex flex-wrap gap-2">
            ${p.skills.map(s => `<span class="px-2.5 py-1 rounded-full bg-brand-50 text-brand-700 text-xs font-medium border border-brand-200">${esc(s)}</span>`).join("")}
          </div>
        </div>`;
    }

    if (p.experience && p.experience.length) {
      rows += `
        <div class="mt-4">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Experience</p>
          <div class="space-y-2">
            ${p.experience.map(e => `
              <div class="text-sm text-gray-700">
                <span class="font-semibold">${esc(e.title || "Role")}</span> at <span class="font-medium">${esc(e.company || "Company")}</span>
                ${e.duration ? `<span class="text-gray-400 ml-1">(${esc(e.duration)})</span>` : ""}
              </div>
            `).join("")}
          </div>
        </div>`;
    }

    if (p.education && p.education.length) {
      rows += `
        <div class="mt-4">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Education</p>
          <div class="space-y-2">
            ${p.education.map(e => `
              <div class="text-sm text-gray-700">
                <span class="font-semibold">${esc(e.degree || "Degree")}</span> in ${esc(e.field || "Field")} &mdash; <span class="font-medium">${esc(e.institution || "Institution")}</span>
                ${e.year ? `<span class="text-gray-400 ml-1">(${esc(e.year)})</span>` : ""}
              </div>
            `).join("")}
          </div>
        </div>`;
    }

    if (p.links && p.links.length) {
      rows += `
        <div class="mt-4">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Links</p>
          <div class="flex flex-wrap gap-2">
            ${p.links.map(l => `<a href="${l.startsWith("http") ? l : "https://" + l}" target="_blank" rel="noopener"
                class="text-xs text-brand-600 hover:underline bg-brand-50 px-2.5 py-1 rounded-full border border-brand-200">${esc(l)}</a>`).join("")}
          </div>
        </div>`;
    }

    const skillCount = (p.skills || []).length;
    const expCount = (p.experience || []).length;
    return accordion(
      "Extracted Profile",
      `${skillCount} skills, ${expCount} positions`,
      rows
    );
  }

  function buildSearchQueries(queries) {
    if (!queries || !queries.length) return "";
    const body = `
      <div class="space-y-2">
        ${queries.map((q, i) => `
          <div class="flex items-start gap-3 text-sm">
            <span class="shrink-0 w-6 h-6 rounded-full bg-brand-100 text-brand-600 text-xs font-bold flex items-center justify-center">${i + 1}</span>
            <code class="text-gray-700 bg-gray-50 px-3 py-1.5 rounded-lg block flex-1">${esc(q)}</code>
          </div>
        `).join("")}
      </div>`;
    return accordion("Search Queries Used", `${queries.length} queries`, body);
  }

  function buildSearchResults(results) {
    if (!results || !results.length) return "";
    const seen = new Set();
    const unique = results.filter(r => {
      if (seen.has(r.url)) return false;
      seen.add(r.url);
      return true;
    });

    const body = `
      <div class="space-y-3 max-h-96 overflow-y-auto">
        ${unique.map(r => `
          <div class="border border-gray-100 rounded-xl p-3 bg-gray-50/50">
            <a href="${r.url}" target="_blank" rel="noopener"
               class="text-sm font-semibold text-brand-600 hover:underline">${esc(r.title || r.url)}</a>
            <p class="text-xs text-gray-400 break-all mt-0.5">${esc(r.url)}</p>
            ${r.snippet ? `<p class="text-xs text-gray-500 mt-1">${esc(r.snippet)}</p>` : ""}
          </div>
        `).join("")}
      </div>`;
    return accordion("Web Search Results", `${unique.length} results`, body);
  }

  function buildCategories(cats) {
    if (!cats || !cats.length) return "";
    const body = `
      <div class="space-y-5">
        ${cats.map(c => `
          <div>
            <div class="flex justify-between text-sm mb-1.5">
              <span class="capitalize font-medium text-gray-700">${esc(c.name)}</span>
              <span class="${scoreColor(c.score)} font-bold">${Math.round(c.score)}</span>
            </div>
            <div class="h-2.5 rounded-full bg-gray-100 overflow-hidden">
              <div class="h-full rounded-full transition-all duration-700 ${barBg(c.score)}" style="width:${c.score}%"></div>
            </div>
            ${c.evidence ? `<p class="text-xs text-gray-400 mt-1.5">${esc(c.evidence)}</p>` : ""}
          </div>
        `).join("")}
      </div>`;
    return accordion("Category Breakdown", `${cats.length} categories`, body);
  }

  function buildFootprints(fps) {
    if (!fps || !fps.length) return "";
    const body = `
      <div class="space-y-3">
        ${fps.map(fp => `
          <div class="border border-gray-100 rounded-xl p-4 bg-gray-50/50 hover:bg-white transition">
            <div class="flex items-start justify-between gap-4">
              <div>
                <p class="text-sm font-semibold text-gray-700">${esc(fp.platform || "Web")}</p>
                <a href="${fp.source_url}" target="_blank" rel="noopener"
                   class="text-xs text-brand-600 hover:text-brand-700 hover:underline break-all">${esc(fp.source_url)}</a>
              </div>
              <div class="shrink-0 flex flex-col gap-1 text-right">
                <span class="px-2.5 py-1 rounded-full text-xs font-bold ${scoreBadgeClass(fp.strong_evidence_score ?? 0)}">
                  Evidence ${(fp.strong_evidence_score ?? 0).toFixed(1)}/10
                </span>
                <span class="px-2.5 py-1 rounded-full text-xs font-bold ${scoreBadgeClass(fp.identity_match_score ?? 0)}">
                  Identity ${(fp.identity_match_score ?? 0).toFixed(1)}/10
                </span>
              </div>
            </div>
            ${fp.summary ? `<p class="text-xs text-gray-500 mt-2 leading-relaxed">${esc(fp.summary)}</p>` : ""}
            ${fp.matched_claims && fp.matched_claims.length ? `
              <div class="mt-2 flex flex-wrap gap-1.5">
                ${fp.matched_claims.map(c => `<span class="text-xs bg-mint-50 text-mint-700 px-2 py-0.5 rounded-full border border-mint-200">${esc(c)}</span>`).join("")}
              </div>` : ""}
          </div>
        `).join("")}
      </div>`;
    return accordion("Digital Footprints", `${fps.length} found`, body);
  }

  function buildFlags(flags) {
    if (!flags || !flags.length) return "";
    return `
      <div class="rounded-2xl bg-red-50 border border-red-200 p-6">
        <h2 class="text-xl font-bold mb-3 text-red-600">Flags</h2>
        <ul class="list-disc list-inside space-y-1.5 text-sm text-red-600/80">
          ${flags.map(f => `<li>${esc(f)}</li>`).join("")}
        </ul>
      </div>`;
  }

  function buildReasoning(text) {
    if (!text) return "";
    return accordion(
      "AI Reasoning",
      null,
      `<p class="text-sm text-gray-600 whitespace-pre-line leading-relaxed">${esc(text)}</p>`
    );
  }

  /* ── load & render ─────────────────────────────────────── */

  async function load() {
    try {
      const res  = await fetch(`/api/analysis/${analysisId}`);
      if (!res.ok) throw new Error("Analysis not found");
      const data = await res.json();

      const t = data.trust_index || {};
      report.innerHTML =
        buildScoreGauge(t.overall_score ?? 0) +
        buildFlags(t.flags) +
        buildResumeText(data.resume_text) +
        buildProfile(data.profile) +
        buildSearchQueries(data.search_queries) +
        buildSearchResults(data.search_results) +
        buildFootprints(data.footprints) +
        buildCategories(t.categories) +
        buildReasoning(t.reasoning);

      loading.classList.add("hidden");
      report.classList.remove("hidden");
    } catch (err) {
      loading.innerHTML = `<p class="text-red-500">${err.message}</p>`;
    }
  }

  load();
})();
