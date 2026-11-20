// Vetted CFB Worker: serves the static site (./site) and three small server routes.
//   POST /api/contact  - contact form (validated, spam-checked, stored in Cloudflare D1)
//   POST /api/role     - anonymous "who are you?" choice (recruit / fan / coach), counts only
//   GET  /inbox        - private page to read messages and role counts (needs the INBOX_KEY secret)
// Setup needed in the Cloudflare dashboard: a D1 database bound as DB, and a secret named INBOX_KEY.
// Until both exist, the routes answer "not configured" and the site shows the X link instead.

const ROLES = new Set(['recruit', 'fan', 'coach', 'skip']);
const SOURCES = new Set(['popup', 'home', 'contact']);
const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', 'x-robots-tag': 'noindex, nofollow' } });
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

async function ipHash(req) {
  // Only a one-way hash of the visitor's IP is kept, for rate limiting. The IP itself is never stored.
  const ip = req.headers.get('cf-connecting-ip') || '';
  const d = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('vettedcfb:' + ip));
  return [...new Uint8Array(d)].slice(0, 8).map((b) => b.toString(16).padStart(2, '0')).join('');
}
async function ensureTables(db) {
  await db.batch([
    db.prepare('CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, name TEXT, email TEXT, role TEXT, msg TEXT NOT NULL, iph TEXT)'),
    db.prepare('CREATE TABLE IF NOT EXISTS roles (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, role TEXT NOT NULL, src TEXT, iph TEXT)'),
  ]);
}

async function contact(req, env) {
  if (!env.DB) return json({ ok: false, reason: 'not_configured' }, 503);
  let b; try { b = await req.json(); } catch { return json({ ok: false, reason: 'bad_request' }, 400); }
  // Spam checks: a hidden field people never fill in, and a minimum time on the page before sending.
  if (b.website) return json({ ok: true });
  if (!(Number(b.t) >= 3000)) return json({ ok: false, reason: 'too_fast' }, 400);
  const msg = String(b.msg || '').trim(), email = String(b.email || '').trim(), name = String(b.name || '').trim();
  const role = ['fan', 'recruit', 'coach', 'media', 'other'].includes(b.role) ? b.role : 'other';
  if (msg.length < 2 || msg.length > 4000) return json({ ok: false, reason: 'message_length' }, 400);
  if (email && (email.length > 200 || !/^\S+@\S+\.\S+$/.test(email))) return json({ ok: false, reason: 'email' }, 400);
  if (name.length > 100) return json({ ok: false, reason: 'name_length' }, 400);
  if ((msg.match(/https?:\/\//g) || []).length > 3) return json({ ok: false, reason: 'links' }, 400);
  await ensureTables(env.DB);
  const iph = await ipHash(req);
  const recent = await env.DB.prepare("SELECT COUNT(*) AS n FROM messages WHERE iph = ? AND at > datetime('now','-1 hour')").bind(iph).first();
  if (recent && recent.n >= 5) return json({ ok: false, reason: 'rate_limited' }, 429);
  await env.DB.prepare("INSERT INTO messages (at, name, email, role, msg, iph) VALUES (datetime('now'), ?, ?, ?, ?, ?)").bind(name, email, role, msg, iph).run();
  return json({ ok: true });
}

async function role(req, env) {
  if (!env.DB) return json({ ok: false, reason: 'not_configured' }, 503);
  let b; try { b = await req.json(); } catch { return json({ ok: false }, 400); }
  if (!ROLES.has(b.role)) return json({ ok: false }, 400);
  const src = SOURCES.has(b.src) ? b.src : 'popup';
  await ensureTables(env.DB);
  const iph = await ipHash(req);
  const dup = await env.DB.prepare("SELECT COUNT(*) AS n FROM roles WHERE iph = ? AND role = ? AND at > datetime('now','-1 day')").bind(iph, b.role).first();
  if (!dup || dup.n === 0) await env.DB.prepare("INSERT INTO roles (at, role, src, iph) VALUES (datetime('now'), ?, ?, ?)").bind(b.role, src, iph).run();
  return json({ ok: true });
}

async function inbox(req, env) {
  const url = new URL(req.url), key = url.searchParams.get('key') || '';
  const page = (body, status = 200) => new Response(`<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex,nofollow"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Vetted CFB inbox</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#14213D;background:#F6F3EC}h1,h2{font-family:Oswald,system-ui}table{border-collapse:collapse;width:100%;background:#fff}td,th{border:1px solid #DDD7C8;padding:6px 8px;text-align:left;vertical-align:top}th{background:#14213D;color:#fff}.m{white-space:pre-wrap}</style>${body}`,
    { status, headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex, nofollow' } });
  if (!env.INBOX_KEY || !env.DB) return page('<h1>Inbox not set up yet</h1><p>Add the D1 database binding (DB) and the INBOX_KEY secret in Cloudflare.</p>', 503);
  if (key.length < 12 || key !== env.INBOX_KEY) return page('<h1>Not allowed</h1>', 401);
  await ensureTables(env.DB);
  const roles = (await env.DB.prepare('SELECT role, src, COUNT(*) AS n FROM roles GROUP BY role, src ORDER BY n DESC').all()).results;
  const days = (await env.DB.prepare("SELECT date(at) AS d, role, COUNT(*) AS n FROM roles WHERE at > datetime('now','-30 day') GROUP BY d, role ORDER BY d DESC").all()).results;
  const msgs = (await env.DB.prepare('SELECT at, name, email, role, msg FROM messages ORDER BY id DESC LIMIT 200').all()).results;
  const total = roles.reduce((a, r) => a + r.n, 0), byRole = {};
  roles.forEach((r) => { byRole[r.role] = (byRole[r.role] || 0) + r.n; });
  return page(`<h1>Vetted CFB inbox</h1>
  <h2>Who's visiting (from the "Who are you?" buttons)</h2><p>${total} answers in total. Each visitor counts once per role per day; no names or IP addresses are stored.</p>
  <table><tr><th>Role</th><th>Answers</th><th>Share</th></tr>${Object.entries(byRole).sort((a, b) => b[1] - a[1]).map(([k, n]) => `<tr><td>${esc(k)}</td><td>${n}</td><td>${total ? Math.round((100 * n) / total) : 0}%</td></tr>`).join('')}</table>
  <h3>By where they clicked</h3><table><tr><th>Role</th><th>Where</th><th>Answers</th></tr>${roles.map((r) => `<tr><td>${esc(r.role)}</td><td>${esc(r.src)}</td><td>${r.n}</td></tr>`).join('')}</table>
  <h3>Last 30 days</h3><table><tr><th>Day</th><th>Role</th><th>Answers</th></tr>${days.map((r) => `<tr><td>${esc(r.d)}</td><td>${esc(r.role)}</td><td>${r.n}</td></tr>`).join('')}</table>
  <h2>Messages (${msgs.length})</h2><table><tr><th>When (UTC)</th><th>From</th><th>Role</th><th>Message</th></tr>${msgs.map((m) => `<tr><td>${esc(m.at)}</td><td>${esc(m.name || '(no name)')}<br>${m.email ? `<a href="mailto:${esc(m.email)}">${esc(m.email)}</a>` : '(no email)'}</td><td>${esc(m.role)}</td><td class="m">${esc(m.msg)}</td></tr>`).join('')}</table>`);
}

export default {
  async fetch(req, env) {
    const { pathname } = new URL(req.url);
    try {
      if (pathname === '/api/contact') return req.method === 'POST' ? await contact(req, env) : json({ ok: false }, 405);
      if (pathname === '/api/role') return req.method === 'POST' ? await role(req, env) : json({ ok: false }, 405);
      if (pathname === '/inbox') return await inbox(req, env);
    } catch (e) {
      return json({ ok: false, reason: 'server_error' }, 500);   // never expose internals
    }
    return env.ASSETS.fetch(req);
  },
};
