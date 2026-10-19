const $ = (s) => document.querySelector(s);
const log = $("#log"), form = $("#form"), q = $("#q"), send = $("#send");
const state = { sources: {} };

const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* tiny, safe markdown: escape first, then **bold**, `code`, bullets, and [source#chunk] citations */
function render(text) {
  const blocks = esc(text).split(/\n{2,}/).map((b) => {
    const lines = b.split("\n");
    if (lines.every((l) => /^\s*[-*] /.test(l))) return "<ul>" + lines.map((l) => `<li>${l.replace(/^\s*[-*] /, "")}</li>`).join("") + "</ul>";
    return "<p>" + lines.join("<br>") + "</p>";
  }).join("");
  return blocks
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\[\]]+?#\d+)\]/g, (m, id) => state.sources[id] !== undefined ? `<button type="button" class="cite" data-id="${id}">[${id}]</button>` : m);
}

function add(cls, html) {
  $("#empty")?.remove();
  const el = document.createElement("div");
  el.className = "turn " + cls;
  el.innerHTML = html;
  log.append(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

function openSource(id) {
  const s = state.sources[id];
  if (!s) return;
  $("#inspId").textContent = id + "  ·  score " + s.score;
  $("#inspText").textContent = s.text;
  $("#inspector").hidden = false;
}
$("#inspClose").onclick = () => ($("#inspector").hidden = true);
log.addEventListener("click", (e) => { const b = e.target.closest("[data-id]"); if (b) openSource(b.dataset.id); });

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = q.value.trim();
  if (!question) return;
  add("user", esc(question));
  q.value = ""; send.disabled = true;
  const wait = add("bot", '<span class="typing">Searching your documents…</span>');
  try {
    const r = await fetch("/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: +$("#topk").value }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Request failed");
    data.sources.forEach((s) => (state.sources[s.id] = s));
    wait.classList.toggle("nogt", !data.grounded);
    const list = data.sources.length
      ? `<details class="srcs"><summary>${data.sources.length} retrieved chunk${data.sources.length > 1 ? "s" : ""}</summary><ul>` +
        data.sources.map((s) => `<li><button type="button" class="cite" data-id="${esc(s.id)}">[${esc(s.id)}]</button><span class="score">${s.score}</span></li>`).join("") + "</ul></details>"
      : "";
    wait.innerHTML = `<div class="body">${render(data.answer)}</div>${list}`;
  } catch (err) {
    wait.innerHTML = `<div class="body" style="color:var(--err)">${esc(err.message)}</div>`;
  } finally { send.disabled = false; q.focus(); log.scrollTop = log.scrollHeight; }
});

/* documents */
function drawDocs(docs) {
  const ul = $("#docs");
  ul.innerHTML = docs.length ? "" : '<li class="none">No documents yet</li>';
  docs.forEach((d) => {
    const li = document.createElement("li");
    li.innerHTML = `<span><span class="name">${esc(d.name)}</span><br><span class="muted">${d.chunks} chunks</span></span><button class="btn small ghost" aria-label="Remove ${esc(d.name)}">Remove</button>`;
    li.querySelector("button").onclick = async () => {
      const r = await fetch("/api/documents/" + encodeURIComponent(d.name), { method: "DELETE" });
      drawDocs((await r.json()).documents);
    };
    ul.append(li);
  });
}
async function refresh() { drawDocs((await (await fetch("/api/documents")).json()).documents); }

async function upload(files) {
  if (!files.length) return;
  const msg = $("#uploadMsg"); msg.className = "msg"; msg.textContent = "Indexing…";
  const fd = new FormData(); [...files].forEach((f) => fd.append("files", f));
  try {
    const r = await fetch("/api/upload", { method: "POST", body: fd });
    const data = await r.json();
    const errs = data.results.filter((x) => x.error);
    msg.className = "msg " + (errs.length ? "err" : "ok");
    msg.textContent = errs.length ? errs.map((x) => `${x.name}: ${x.error}`).join(" ") : `Indexed ${data.results.length} file${data.results.length > 1 ? "s" : ""}.`;
    drawDocs(data.documents);
  } catch { msg.className = "msg err"; msg.textContent = "Upload failed. Check the server is running."; }
}
const file = $("#file"), drop = $("#drop");
file.onchange = () => { upload(file.files); file.value = ""; };
drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); file.click(); } });
["dragover", "dragenter"].forEach((n) => drop.addEventListener(n, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((n) => drop.addEventListener(n, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => upload(e.dataTransfer.files));

$("#topk").oninput = (e) => ($("#topkOut").textContent = e.target.value);
$("#toggleSide").onclick = (e) => { const o = $("#side").classList.toggle("open"); e.target.setAttribute("aria-expanded", o); };
refresh();
