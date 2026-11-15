// Renders docs/guide/*.md as a checklist. Ticks live in localStorage; checkpoints come from
// /api/status (local server of tools/check_progress.py) or from status.json on the group's
// tutorial-status branch (written by the GitHub Actions workflow).
const PARTS = [
  ["0-setup.md", "0 · Getting ready"],
  ["1-warm-up-on-main.md", "1 · Warm-up on main"],
  ["2-branches-and-pull-requests.md", "2 · Branches + pull requests"],
  ["3-notebooks.md", "3 · Notebooks"],
  ["4-when-things-go-wrong.md", "4 · When things go wrong"],
];
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const store = {
  get(k, d = "") { try { return localStorage.getItem("epss-git:" + k) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem("epss-git:" + k, v); } catch { /* private mode */ } },
  clearTicks() { try { Object.keys(localStorage).filter((k) => k.startsWith("epss-git:tick:")).forEach((k) => localStorage.removeItem(k)); } catch { /* ignore */ } },
};
const PRINT = params.has("print");
let steps = [];
let role = params.get("role") || store.get("role", "A");
let localMode = false;

function parseRepo(text) {
  const m = (text || "").trim().match(/(?:github\.com[/:])?([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/);
  return m ? `${m[1]}/${m[2]}` : "";
}

async function loadGuide() {
  const texts = await Promise.all(PARTS.map(([file]) => fetch("guide/" + file).then((r) => r.text())));
  const guide = $("guide");
  guide.textContent = "";
  texts.forEach((md, i) => {
    md = md
      .replace(/<!--\s*checkpoint:\s*([\w-]+)\s*-->/g, '<div class="cp" data-cp="$1"></div>\n')
      .replace(/^[ \t]*<!--\s*snippet:.*?-->[ \t]*\n/gm, "")
      .replace(/\]\(\.\.\/img\//g, "](img/")
      .replace(/\]\((\d)-[\w-]+\.md\)/g, "](#part-$1)");
    const section = document.createElement("section");
    section.className = "part";
    section.id = "part-" + i;
    section.innerHTML = marked.parse(md);
    guide.append(section);
    enhance(section, i);
  });
  $("nav").innerHTML = PARTS.map(([, title], i) => `<a href="#part-${i}">${title}</a>`).join("");
  const seen = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting) document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("here", a.hash === "#" + e.target.id));
  }), { rootMargin: "-20% 0px -70% 0px" });
  document.querySelectorAll(".part").forEach((p) => seen.observe(p));
  if (PRINT) document.querySelectorAll("details").forEach((d) => (d.open = true));
  if (location.hash) document.querySelector(location.hash)?.scrollIntoView();
}

function enhance(section, part) {
  // task-list items become steps: checkbox + role badges + body
  section.querySelectorAll("li > input[type=checkbox], li > p > input[type=checkbox]").forEach((box, n) => {
    const li = box.closest("li");
    const strong = box.nextElementSibling?.tagName === "STRONG" ? box.nextElementSibling : null;
    const label = strong ? strong.textContent.trim() : "All";
    const roles = label === "All" ? ["A", "B", "C"] : label.match(/[ABC]/g) || ["A", "B", "C"];
    const who = document.createElement("span");
    who.className = "who";
    who.innerHTML = (label === "All" ? ["All"] : roles).map((r) => `<span class="${r}">${r}</span>`).join("");
    strong?.replaceWith(who);

    const body = document.createElement("div");
    body.className = "body";
    box.remove();
    body.append(...li.childNodes);
    li.append(box, body);
    li.classList.add("step");
    li.parentElement.classList.add("steps");
    const id = `tick:${part}-${n}`;
    box.disabled = false;
    box.checked = store.get(id) === "1";
    box.setAttribute("aria-label", "Done");
    box.addEventListener("change", () => { store.set(id, box.checked ? "1" : "0"); paint(); });
    steps.push({ li, box, roles });
  });
  // copy buttons on code to paste
  section.querySelectorAll("pre > code.language-python").forEach((code) => {
    const b = document.createElement("button");
    b.type = "button"; b.className = "copy"; b.textContent = "Copy";
    b.addEventListener("click", async () => {
      await navigator.clipboard.writeText(code.textContent);
      b.textContent = "Copied"; setTimeout(() => (b.textContent = "Copy"), 1500);
    });
    code.parentElement.append(b);
  });
  // checkpoint markers attach to the note that follows them
  section.querySelectorAll(".cp").forEach((cp) => {
    const note = cp.nextElementSibling;
    if (note?.tagName === "BLOCKQUOTE") {
      note.classList.add("checkpoint");
      note.dataset.cp = cp.dataset.cp;
      const line = document.createElement("p");
      line.innerHTML = '<span class="chip"></span><span class="chip-detail"></span>';
      note.append(line);
    }
    cp.remove();
  });
}

function paint() {
  document.body.dataset.role = role;
  document.querySelectorAll(".roles button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.role === role)));
  let mine = 0, done = 0;
  for (const s of steps) {
    const isMine = s.roles.includes(role);
    s.li.classList.toggle("mine", isMine && !s.box.checked);
    s.li.classList.toggle("other", !isMine);
    s.li.classList.toggle("done", s.box.checked);
    if (isMine) { mine++; done += s.box.checked; }
  }
  $("fill").style.width = mine ? `${(100 * done) / mine}%` : "0";
  $("count").textContent = `${done} / ${mine} steps`;
}

// ---------------------------------------------------------------- checkpoints
const MARK = { true: ["ok", "✓", "verified"], false: ["no", "○", "not yet"], null: ["unknown", "?", "see GitHub"] };

function showStatus(st, note) {
  const repo = store.get("repo");
  $("check-now").hidden = localMode || !repo;
  $("repo-form").hidden = localMode;
  $("panel-hint").textContent = note || "";
  $("cps").innerHTML = "";
  $("problems").hidden = $("local").hidden = true;
  document.querySelectorAll("blockquote.checkpoint").forEach((b) => {
    b.classList.remove("ok");
    b.querySelector(".chip").className = "chip";
    b.querySelector(".chip").textContent = st ? "" : "not checked yet";
    b.querySelector(".chip-detail").textContent = "";
  });
  if (!st) { $("source").textContent = ""; return; }

  const when = new Date(st.updated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  $("source").textContent = `${st.done} of ${st.total} · ${st.repo} · ` +
    (localMode ? `this computer, ${when}` : `GitHub, ${when} (can lag a few minutes)`);
  const next = st.checkpoints.find((c) => c.ok === false);  // only the next one explains itself
  st.checkpoints.forEach((c) => {
    const [cls, sign, word] = MARK[String(c.ok)];
    const li = document.createElement("li");
    li.innerHTML = `<span class="mark ${cls}" aria-label="${word}">${sign}</span><span></span>`;
    li.lastChild.textContent = c.title;
    if (c.detail && (c === next || c.ok === null)) {
      const d = document.createElement("span");
      d.className = "detail"; d.textContent = c.detail;
      li.append(d);
    }
    $("cps").append(li);
    const note = document.querySelector(`blockquote.checkpoint[data-cp="${c.id}"]`);
    if (note) {
      note.classList.toggle("ok", c.ok === true);
      note.querySelector(".chip").className = "chip " + cls;
      note.querySelector(".chip").textContent = `${sign} ${word}`;
      note.querySelector(".chip-detail").textContent = c.ok === true ? "" : c.detail;
    }
  });
  if (st.problems?.length) {
    $("problems").hidden = false;
    $("problems").innerHTML = "";
    st.problems.forEach((p) => { const li = document.createElement("li"); li.textContent = p; $("problems").append(li); });
  }
  if (st.local) {
    $("local").hidden = false;
    $("local").innerHTML = "";
    Object.entries(st.local).forEach(([k, v]) => {
      const dt = document.createElement("dt"), dd = document.createElement("dd");
      dt.textContent = k; dd.textContent = v; $("local").append(dt, dd);
    });
  }
}

async function refresh(viaApi = false) {
  if (localMode) {
    try { showStatus(await (await fetch("api/status", { cache: "no-store" })).json()); }
    catch { showStatus(null, "The local progress check stopped. Run the task Tutorial: progress page again."); }
    return;
  }
  const repo = store.get("repo");
  if (!repo) return showStatus(null, "Paste your group's repository address below to see which checkpoints are verified.");
  const url = viaApi
    ? `https://api.github.com/repos/${repo}/contents/status.json?ref=tutorial-status`
    : `https://raw.githubusercontent.com/${repo}/tutorial-status/status.json?t=${Date.now()}`;
  try {
    const r = await fetch(url, { cache: "no-store", headers: viaApi ? { Accept: "application/vnd.github.raw+json" } : {} });
    if (r.status === 403 || r.status === 429) return showStatus(null, "GitHub asks to slow down. Wait a minute, or run Tutorial: check progress in VS Code.");
    if (!r.ok) return showStatus(null, `No status for ${repo} yet. It appears a minute after the first push to that repository; check the address if it stays empty.`);
    showStatus(await r.json());
  } catch {
    showStatus(null, "Could not reach GitHub. Your ticks still work.");
  }
}

async function init() {
  if (PRINT) document.body.classList.add("print");
  if (params.get("repo")) store.set("repo", parseRepo(params.get("repo")));
  $("repo").value = store.get("repo");
  document.querySelectorAll(".roles button").forEach((b) => b.addEventListener("click", () => {
    role = b.dataset.role; store.set("role", role); paint();
  }));
  $("repo-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const repo = parseRepo($("repo").value);
    store.set("repo", repo); $("repo").value = repo; refresh();
  });
  $("check-now").addEventListener("click", () => refresh(true));
  $("reset").addEventListener("click", () => {
    if (!confirm("Untick all your steps in this browser?")) return;
    store.clearTicks(); steps.forEach((s) => (s.box.checked = false)); paint();
  });

  await loadGuide();
  paint();
  try {
    const r = await fetch("api/status", { cache: "no-store" });
    localMode = r.ok && (r.headers.get("content-type") || "").includes("json");
  } catch { localMode = false; }
  refresh();
  setInterval(() => { if (!document.hidden) refresh(); }, localMode ? 8000 : 60000);
}

init();
