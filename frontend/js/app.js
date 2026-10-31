/* StayGenius AI - Frontend JavaScript */

const API = location.port === '5000' ? '' : 'http://localhost:5000';

const $ = s => document.querySelector(s);

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
}[c]));

const money = n => '₹' + Math.round(Number(n || 0)).toLocaleString('en-IN');

const fmtDate = d => new Date(d + 'T00:00').toLocaleDateString('en-IN', {
  day: 'numeric',
  month: 'short'
});

const today = () => new Date().toISOString().slice(0, 10);

const addDays = (d, n) => {
  const x = new Date(d + 'T00:00');
  x.setDate(x.getDate() + n);
  return x.toLocaleDateString('en-CA');
};

const tag = s => `<span class="tag ${esc(s)}">${esc(String(s).replace('_', ' '))}</span>`;

let token = sessionStorage.getItem('sg_token');
let user = JSON.parse(sessionStorage.getItem('sg_user') || 'null');

let state = {
  search: null,
  page: null,
  assistantHistory: []
};


/* ==========================================
   API CONNECTION
========================================== */

async function api(path, o = {}) {

  const r = await fetch(API + '/api' + path, {
    method: o.method || 'GET',

    headers: {
      'Content-Type': 'application/json',
      ...(token ? {
        Authorization: 'Bearer ' + token
      } : {})
    },

    body: o.body ? JSON.stringify(o.body) : undefined
  });

  const d = await r.json().catch(() => ({}));

  if (!r.ok) {

    if (r.status === 401 && token && path !== '/auth/login') {
      logout();
    }

    throw new Error(d.error || 'Something went wrong.');
  }

  return d;
}


function toast(m, bad) {

  const t = $('#toast');

  t.textContent = m;

  t.className = 'show' + (bad ? ' bad' : '');

  clearTimeout(t._t);

  t._t = setTimeout(() => {
    t.className = '';
  }, 3200);
}


function dialog(html) {

  const d = $('#dlg');

  d.innerHTML = html +
    '<p><button class="btn" data-act="close">Close</button></p>';

  d.showModal();
}


/* ==========================================
   SVG CHARTS
========================================== */

function bars(data, fmt = v => v, h = 180) {

  const max = Math.max(...data.map(d => d.value), 1);

  const w = 56 * data.length + 20;

  return `<svg viewBox="0 0 ${w} ${h + 40}" width="100%"
    style="max-width:${w * 1.6}px" role="img">` +

    data.map((d, i) => {

      const bh = d.value / max * h;

      return `
        <rect
          x="${i * 56 + 14}"
          y="${h - bh + 10}"
          width="36"
          height="${bh}"
          rx="4"
          fill="${d.color || '#0e5a4a'}"
        />

        <text
          x="${i * 56 + 32}"
          y="${h - bh + 4}"
          text-anchor="middle"
        >${fmt(d.value)}</text>

        <text
          x="${i * 56 + 32}"
          y="${h + 28}"
          text-anchor="middle"
        >${esc(d.label)}</text>
      `;

    }).join('') + '</svg>';
}


function line(data) {

  const w = 600;
  const h = 160;

  const max = Math.max(...data.map(d => d.value), 100);

  const pts = data.map((d, i) => [
    10 + i * (w - 20) / (data.length - 1),
    h - d.value / max * h + 10
  ]);

  return `
    <svg viewBox="0 0 ${w} ${h + 40}" width="100%" role="img">

      <polyline
        fill="none"
        stroke="#0e5a4a"
        stroke-width="2.5"
        points="${pts.map(p => p.join(',')).join(' ')}"
      />

      ${[0, 14, 29].map(i => `
        <text
          x="${pts[i][0]}"
          y="${h + 30}"
          text-anchor="middle"
        >${data[i].label}</text>
      `).join('')}

      <text x="4" y="12">${max}%</text>

    </svg>
  `;
}


/* ==========================================
   ROOM AMENITIES
========================================== */

const AMEN = {

  Standard: [
    'Free Wi-Fi',
    'Air conditioning',
    'Queen bed',
    'TV'
  ],

  Deluxe: [
    'Free Wi-Fi',
    'Hill view',
    'Work desk',
    'King bed'
  ],

  Executive: [
    'Free Wi-Fi',
    'Lounge corner',
    'Breakfast included',
    'Hill view'
  ],

  Suite: [
    'Free Wi-Fi',
    'Living room',
    'Breakfast included',
    'Temple-hill view'
  ]

};


/* ==========================================
   REAL HOTEL ROOM PHOTOGRAPHS
========================================== */

const ROOM_PHOTOS = {

  Standard:
    'https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=1000&q=85',

  Deluxe:
    'https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1000&q=85',

  Executive:
    'https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1000&q=85',

  Suite:
    'https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=1000&q=85'

};


/* ==========================================
   ROOM IMAGE FUNCTION
========================================== */

function roomPic(name, badges = '') {

  const photo = ROOM_PHOTOS[name] || ROOM_PHOTOS.Standard;

  return `
    <div class="roompic">

      <img
        src="${photo}"
        alt="${esc(name)} hotel room"
        loading="lazy"
        onerror="this.style.display='none';this.parentElement.classList.add('photo-error')"
      >

      ${badges}

    </div>
  `;
}


/* ==========================================
   OLD ROOM ILLUSTRATION
   Used in booking history thumbnails
========================================== */

function roomArt(name) {

  const lvl = {
    Standard: 1,
    Deluxe: 2,
    Executive: 3,
    Suite: 4
  }[name] || 1;

  const pal = [
    ['#ffe3b8', '#ffb347', '#5a60e0'],
    ['#cfe8ff', '#ffd27a', '#3a3fd1'],
    ['#e5d6ff', '#ff9f6b', '#2a2eaa'],
    ['#ffd1dc', '#ffb347', '#1b2166']
  ][lvl - 1];

  return `
  <svg viewBox="0 0 400 240"
    preserveAspectRatio="xMidYMid slice"
    role="img"
    aria-label="${esc(name)} room illustration">

    <defs>
      <linearGradient id="sky${lvl}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="${pal[0]}"/>
        <stop offset="1" stop-color="${pal[1]}"/>
      </linearGradient>
    </defs>

    <rect width="400" height="240" fill="#f3f0fb"/>
    <rect y="172" width="400" height="68" fill="#d8d2ee"/>
    <rect y="168" width="400" height="6" fill="#c3bce3"/>

    <rect x="246" y="26" width="132" height="108"
      rx="8" fill="url(#sky${lvl})" stroke="#fff" stroke-width="6"/>

    <circle cx="330" cy="62" r="16" fill="#fff6d6" opacity=".95"/>

    <polygon points="246,134 276,86 302,114 330,76 378,134"
      fill="${pal[2]}" opacity=".55"/>

    <polygon points="246,134 290,106 330,134"
      fill="${pal[2]}" opacity=".85"/>

    <line x1="312" y1="26" x2="312" y2="134"
      stroke="#fff" stroke-width="4"/>

    <line x1="246" y1="80" x2="378" y2="80"
      stroke="#fff" stroke-width="4"/>

    <rect x="236" y="20" width="152" height="8"
      rx="4" fill="${pal[2]}"/>

    <rect x="236" y="28" width="22" height="118"
      rx="6" fill="${pal[2]}" opacity=".25"/>

    <rect x="366" y="28" width="22" height="118"
      rx="6" fill="${pal[2]}" opacity=".25"/>

    <rect x="34" y="66" width="190" height="66"
      rx="10" fill="${pal[2]}"/>

    <rect x="24" y="118" width="210" height="54"
      rx="12" fill="#fff"/>

    <rect x="24" y="140" width="210" height="34"
      rx="10" fill="${pal[2]}" opacity=".85"/>

    <rect x="24" y="140" width="210" height="8"
      fill="#fff" opacity=".4"/>

    <ellipse cx="78" cy="122" rx="30" ry="12" fill="#f0eefc"/>
    <ellipse cx="140" cy="122" rx="30" ry="12" fill="#f0eefc"/>

    <rect x="24" y="172" width="8" height="18" fill="#6b5d4a"/>
    <rect x="226" y="172" width="8" height="18" fill="#6b5d4a"/>

    <rect x="236" y="146" width="26" height="26"
      rx="4" fill="#8a6f52"/>

    <rect x="243" y="116" width="12" height="30" fill="#8a6f52"/>

    <path d="M233 118 L265 118 L258 94 L240 94 Z"
      fill="#ffd27a"/>

    <circle cx="249" cy="118" r="24"
      fill="#ffd27a" opacity=".18"/>

    <ellipse cx="150" cy="212" rx="110" ry="14"
      fill="${pal[2]}" opacity=".18"/>

    ${lvl >= 2 ? `
      <rect x="292" y="152" width="96" height="9"
        rx="3" fill="#8a6f52"/>

      <rect x="300" y="161" width="6" height="30" fill="#8a6f52"/>
      <rect x="374" y="161" width="6" height="30" fill="#8a6f52"/>

      <rect x="318" y="134" width="40" height="18"
        rx="3" fill="#2b2f5e"/>

      <rect x="322" y="138" width="32" height="10" fill="#7f86ff"/>
    ` : ''}

    ${lvl >= 3 ? `
      <rect x="268" y="176" width="40" height="30"
        rx="12" fill="#ff9f1c"/>

      <rect x="262" y="164" width="14" height="44"
        rx="7" fill="#e78600"/>

      <rect x="300" y="164" width="14" height="44"
        rx="7" fill="#e78600"/>
    ` : ''}

    ${lvl >= 4 ? `
      <rect x="326" y="170" width="70" height="38"
        rx="10" fill="#5a60e0"/>

      <rect x="326" y="158" width="70" height="20"
        rx="10" fill="#7f86ff"/>

      <rect x="40" y="26" width="64" height="40"
        rx="4" fill="#fff" stroke="${pal[2]}" stroke-width="3"/>

      <polygon points="44,62 66,38 80,54 92,44 100,62"
        fill="${pal[1]}"/>
    ` : ''}

  </svg>
  `;
}


/* ==========================================
   NAVIGATION BY USER ROLE
========================================== */

const NAV = {

  guest: [
    ['book', 'Book a room'],
    ['stays', 'My stays'],
    ['assistant', 'Concierge'],
    ['offers', 'Offers for you'],
    ['profile', 'My preferences']
  ],

  staff: [
    ['board', 'Room board'],
    ['frontdesk', 'Arrivals and stays'],
    ['requests', 'Guest requests'],
    ['housekeeping', 'Housekeeping'],
    ['reviews', 'Reviews']
  ],

  manager: [
    ['pricing', 'Pricing'],
    ['forecast', 'Forecast'],
    ['reviews', 'Reviews'],
    ['dashboard', 'Dashboard'],
    ['board', 'Room board']
  ],

  admin: [
    ['dashboard', 'Dashboard'],
    ['roomtypes', 'Rooms and types'],
    ['catalog', 'Services'],
    ['users', 'Users'],
    ['board', 'Room board']
  ]

};


/* ==========================================
   LANDING PAGE NAVIGATION
========================================== */

function showLanding() {

  $('#landing').hidden = false;
  $('#login').hidden = true;
  $('#app').hidden = true;

  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });

}


function showAuth() {

  $('#landing').hidden = true;
  $('#login').hidden = false;
  $('#app').hidden = true;

  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });

}


/* ==========================================
   USER LOGIN SUCCESS
========================================== */

function enter() {

  $('#landing').hidden = true;
  $('#login').hidden = true;
  $('#app').hidden = false;

  $('#me-name').textContent = user.name;

  $('#me-role').textContent = {
    staff: 'Front office',
    guest: 'Guest',
    manager: 'Hotel manager',
    admin: 'Admin'
  }[user.role];

  $('#nav').innerHTML = NAV[user.role]
    .map(([k, l]) =>
      `<button data-act="go" data-p="${k}">${l}</button>`
    )
    .join('');

  go(NAV[user.role][0][0]);

}


/* ==========================================
   LOGOUT
========================================== */

function logout() {

  sessionStorage.clear();

  token = user = null;

  $('#app').hidden = true;

  showLanding();

}


/* ==========================================
   PAGE NAVIGATION
========================================== */

async function go(p) {

  state.page = p;

  document.querySelectorAll('#nav button').forEach(b => {
    b.classList.toggle('on', b.dataset.p === p);
  });

  $('#view').innerHTML = '<p>Loading…</p>';

  try {

    await pages[p]();

  } catch (e) {

    $('#view').innerHTML = `
      <div class="panel">
        <h3>Could not load this page</h3>
        <p>${esc(e.message)}</p>
      </div>
    `;

  }

}


const view = html => $('#view').innerHTML = html;

const head = (t, sub = '', extra = '') =>
  `<div class="head"><div><h2>${t}</h2><p>${sub}</p></div>${extra}</div>`;

const empty = m =>
  `<p style="color:var(--muted)">${m}</p>`;


/* ==========================================
   APPLICATION PAGES
========================================== */

const pages = {

  /* GUEST */

  async book() {

    const s = state.search || {
      check_in: addDays(today(), 1),
      check_out: addDays(today(), 2),
      guests: 2
    };

    view(`
      <div class="hero-banner">
        <h2>Stay close to Tirumala</h2>
        <p>
          Comfortable rooms minutes from the temple.
          Prices follow demand, so quiet weekdays cost less
          than festival dates.
        </p>
      </div>
    ` + `

      <form class="panel row" data-form="search">

        <label>
          Check-in
          <input type="date" name="check_in"
            min="${today()}" value="${s.check_in}" required>
        </label>

        <label>
          Check-out
          <input type="date" name="check_out"
            min="${today()}" value="${s.check_out}" required>
        </label>

        <label>
          Guests
          <input type="number" name="guests"
            min="1" max="5" value="${s.guests}" required>
        </label>

        <button class="btn primary">Show rooms</button>

      </form>

      <div id="results"></div>
    `);

    if (state.search) {
      searchRooms();
    }

  },


  async stays() {

    const [b, r, rv] = await Promise.all([
      api('/bookings'),
      api('/service-requests'),
      api('/reviews')
    ]);

    view(
      head('My stays') +

      (b.length ? b.map(x => `

        <div class="panel">

          <div class="row">

            <div class="thumb">
              ${roomArt(x.room_type)}
            </div>

            <div style="flex:2">

              <h3>
                ${esc(x.room_type)} · Room ${esc(x.room_number)}
              </h3>

              <p>
                ${fmtDate(x.check_in)} to ${fmtDate(x.check_out)}
                · ${x.guests} guest(s)
                · ${money(x.total)}
                ${tag(x.status)}
              </p>

            </div>

            <div>

              ${x.status === 'confirmed' ? `
                <button class="btn small danger"
                  data-act="cancel" data-id="${x.id}">
                  Cancel
                </button>
              ` : ''}

              ${x.status === 'checked_in' ? `
                <button class="btn small primary"
                  data-act="reqform">
                  Request a service
                </button>
              ` : ''}

              ${['checked_in', 'checked_out'].includes(x.status) ? `

                <button class="btn small"
                  data-act="invoice" data-id="${x.id}">
                  Invoice
                </button>

                <button class="btn small"
                  data-act="reviewform" data-id="${x.id}">
                  Leave feedback
                </button>

              ` : ''}

            </div>

          </div>

        </div>

      `).join('') : empty('No bookings yet. Book your first room.')) +

      `
        <h3>My requests</h3>

        <div class="panel">

          ${r.length
            ? table(
                ['Request', 'Type', 'Status'],
                r.map(x => [
                  esc(x.description),
                  x.category,
                  tag(x.status)
                ])
              )
            : empty('Requests open after check-in.')
          }

        </div>

        <h3>My feedback</h3>

        ${rv.map(x => `

          <div class="panel">

            <b>${'★'.repeat(x.rating)}</b>
            ${tag(x.sentiment)}

            <p>${esc(x.comment)}</p>

            ${x.reply ? `
              <p><b>Hotel reply:</b> ${esc(x.reply)}</p>
            ` : ''}

          </div>

        `).join('') || empty('No feedback yet.')}

      `
    );

  },


  async assistant() {

    const history = state.assistantHistory.map(message => `
      <div class="msg ${message.role === 'user' ? 'me' : ''}">${esc(message.content)}</div>
    `).join('');

    const greeting = `
      <div class="msg">
        Hello ${esc(user.name.split(' ')[0])}! I can help with hotel services, food, local temples, or a request for our team.
      </div>
    `;

    view(
      head(
        'Concierge',
        'Ask in your own language. Requests such as towels, food or repairs go straight to our staff.'
      ) +

      `

      <div class="panel">

        <div class="chat" id="chat">

          ${history || greeting}

        </div>

        <form class="row" data-form="chat" style="margin-top:.8rem">

          <label style="flex:0 0 150px">
            Language

            <select name="language">
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="te">తెలుగు</option>
              <option value="ta">தமிழ்</option>
              <option value="kn">ಕನ್ನಡ</option>
              <option value="ml">മലയാളം</option>
            </select>

          </label>

          <label style="flex:3">
            Message

            <input
              name="message"
              required
              maxlength="500"
              placeholder="Please send two extra towels to my room"
            >
          </label>

          <button class="btn primary">Send</button>

        </form>

      </div>
    `);

  },


  async offers() {

    const o = await api('/upsell');

    view(
      head('Offers for you', 'Picked from your preferences and stay history.') +

      `<div class="grid">

        ${o.map(x => `

          <div class="panel card">

            <h3>${esc(x.title)}</h3>

            <p>${esc(x.description)}</p>

            <p class="price">
              ${x.price ? money(x.price) : 'Free'}
            </p>

            <p>${esc(x.reason)}</p>

          </div>

        `).join('')}

      </div>`
    );

  },


  async profile() {

    const me = await api('/me');

    const pr = (me.preferences || '').split(',');

    view(
      head('My preferences', 'These shape the offers and service we give you.') +

      `

      <form class="panel" data-form="profile" style="max-width:520px">

        <label>
          Phone
          <input name="phone" value="${esc(me.phone)}" maxlength="20">
        </label>

        <label>
          Preferred language

          <select name="language">

            ${[
              ['en', 'English'],
              ['hi', 'Hindi'],
              ['te', 'Telugu'],
              ['ta', 'Tamil']
            ].map(([k, v]) => `
              <option value="${k}" ${me.language === k ? 'selected' : ''}>
                ${v}
              </option>
            `).join('')}

          </select>
        </label>

        ${[
          'vegetarian',
          'family',
          'spa',
          'quiet room',
          'high floor',
          'early check-in'
        ].map(t => `

          <label style="font-weight:400">

            <input
              type="checkbox"
              name="pref"
              value="${t}"
              style="width:auto"
              ${pr.includes(t) ? 'checked' : ''}
            >

            ${t}

          </label>

        `).join('')}

        <button class="btn primary">Save preferences</button>

      </form>
    `);

  },


  /* FRONT OFFICE */

  async board() {

    const r = await api('/rooms');

    const c = {};

    r.forEach(x => {
      c[x.status] = (c[x.status] || 0) + 1;
    });

    view(
      head('Room board', `${r.length} rooms. Select a room to change its status.`) +
      `
      <div class="legend">
        ${['vacant', 'occupied', 'cleaning', 'maintenance'].map(s => `

          <span>
            <i style="background:var(--${s})"></i>
            ${s} (${c[s] || 0})
          </span>

        `).join('')}

      </div>

      <div class="board">

        ${r.map(x => `

          <button
            class="room ${x.status}"
            data-act="roomdlg"
            data-id="${x.id}"
            data-n="${x.number}"
            data-s="${x.status}"
            title="${esc(x.room_type)}"
          >

            ${x.number}

            <small>
              ${esc(x.guest_name ? x.guest_name.split(' ')[0] : x.room_type)}
            </small>

          </button>

        `).join('')}

      </div>
    `);

  },


  async frontdesk() {

    const v = state.fdView || 'upcoming';

    const b = await api('/bookings?view=' + v);

    view(
      head(
        'Arrivals and stays',
        'Check guests in and out. Check-out creates the invoice and a cleaning task.',
        `
          <select id="fdview" style="width:auto">

            <option value="upcoming" ${v === 'upcoming' ? 'selected' : ''}>
              Arrivals (next 7 days)
            </option>

            <option value="inhouse" ${v === 'inhouse' ? 'selected' : ''}>
              In house
            </option>

            <option value="history" ${v === 'history' ? 'selected' : ''}>
              Past stays
            </option>

          </select>
        `
      ) +

      `

      <div class="panel table-wrap">

        ${b.length ? table(
          ['Guest', 'Room', 'Dates', 'Status', ''],

          b.map(x => [

            esc(x.guest_name),

            `${x.room_number} · ${esc(x.room_type)}`,

            `${fmtDate(x.check_in)} to ${fmtDate(x.check_out)}`,

            tag(x.status),

            x.status === 'confirmed' ? `
              <button class="btn small primary"
                data-act="checkin" data-id="${x.id}">
                Check in
              </button>

              <button class="btn small danger"
                data-act="cancel" data-id="${x.id}">
                Cancel
              </button>
            ` :

            x.status === 'checked_in' ? `
              <button class="btn small primary"
                data-act="checkout" data-id="${x.id}">
                Check out
              </button>
            ` :

            `
              <button class="btn small"
                data-act="invoice" data-id="${x.id}">
                Invoice
              </button>
            `

          ])
        ) : empty('Nothing here.')}

      </div>
    `);

  },


  async requests() {

    const r = await api('/service-requests');

    view(
      head('Guest requests', 'Open requests, high priority first.') +

      `

      <div class="panel table-wrap">

        ${r.length ? table(
          ['Room', 'Guest', 'Request', 'Priority', 'Status', ''],

          r.map(x => [

            x.room_number,

            esc(x.guest_name),

            `${esc(x.description)}<br><small>${x.category}</small>`,

            tag(x.priority),

            tag(x.status),

            ['pending', 'in_progress']
              .filter(s => s !== x.status)
              .concat(['done'])
              .filter((v, i, a) => a.indexOf(v) === i)
              .map(s => `

                <button
                  class="btn small"
                  data-act="reqstatus"
                  data-id="${x.id}"
                  data-s="${s}"
                >
                  ${s.replace('_', ' ')}
                </button>

              `).join(' ')

          ])
        ) : empty('All clear. No open requests.')}

      </div>
    `);

  },


  async housekeeping() {

    const d = await api('/housekeeping/schedule');

    view(
      head(
        'Housekeeping',
        'Suggested order: rooms with guests arriving today are cleaned first.'
      ) +

      `

      <div class="panel">

        <h3>Room turnovers</h3>

        ${d.turnover.length ? table(
          ['Time', 'Room', 'Type', 'Why', ''],

          d.turnover.map(x => [

            x.slot,
            x.number,
            esc(x.room_type),
            x.reason,

            `<button
              class="btn small primary"
              data-act="roomstatus"
              data-id="${x.id}"
              data-s="vacant">
              Mark clean
            </button>`

          ])
        ) : empty('No rooms waiting.')}

      </div>

      <div class="panel">

        <h3>Guest cleaning requests</h3>

        ${d.requests.length ? table(
          ['Room', 'Request', 'Status'],

          d.requests.map(x => [
            x.room_number,
            esc(x.description),
            tag(x.status)
          ])
        ) : empty('None.')}

      </div>
    `);

  },


  async reviews() {

    const [r, ins] = await Promise.all([

      api('/reviews'),

      user.role === 'manager' || user.role === 'admin'
        ? api('/reviews/insights')
        : null

    ]);

    const mgr = user.role === 'manager' || user.role === 'admin';

    view(
      head(
        'Reviews',
        mgr
          ? 'AI reads every review so you can reply faster.'
          : 'Recent guest feedback.'
      ) +

      (ins ? `

        <div class="panel">

          <h3>What guests are saying</h3>

          <p style="white-space:pre-line">
            ${esc(ins.summary)}
          </p>

          <p>

            ${ins.top_praise?.map(([t, n]) => `
              <span class="tag positive">
                ${esc(t)} ${n}
              </span>
            `).join(' ')}

            ${ins.top_issues?.map(([t, n]) => `
              <span class="tag negative">
                ${esc(t)} ${n}
              </span>
            `).join(' ')}

          </p>

        </div>

      ` : '') +

      r.map(x => `

        <div class="panel">

          <b>
            ${'★'.repeat(x.rating)}
            ${'☆'.repeat(5 - x.rating)}
          </b>

          ${esc(x.guest_name)}
          ${tag(x.sentiment)}

          <small>${esc(x.themes)}</small>

          <p>${esc(x.comment)}</p>

          ${x.reply
            ? `<p><b>Reply:</b> ${esc(x.reply)}</p>`
            : mgr
              ? `
                <button class="btn small primary"
                  data-act="draft" data-id="${x.id}">
                  Draft reply with AI
                </button>

                <div id="rp${x.id}"></div>
              `
              : ''
          }

        </div>

      `).join('')

    );

  },


  /* MANAGER */

  async pricing() {

    const days = state.days || 14;

    const d = await api('/pricing/suggestions?days=' + days);

    state.sug = d;

    view(
      head(
        'Pricing',
        'Suggested nightly prices from forecast occupancy and the festival calendar. Review, then approve.',

        `

        <div>

          <select id="pdays" style="width:auto">

            ${[7, 14, 30].map(n => `
              <option ${n === days ? 'selected' : ''} value="${n}">
                Next ${n} days
              </option>
            `).join('')}

          </select>

          <button class="btn primary" data-act="applyall">
            Approve all suggestions
          </button>

        </div>
        `
      ) +

      `

      <div class="panel table-wrap">

        ${table(

          [
            'Date',
            'Demand',
            'Reason',
            ...d.room_types.map(t => esc(t.name))
          ],

          d.days.map(x => [

            `${fmtDate(x.date)}${x.festival
              ? '<br><small>' + esc(x.festival) + '</small>'
              : ''
            }`,

            Math.round(x.occupancy * 100) + '%',

            `<span class="${x.change_pct >= 0 ? 'up' : 'down'}">
              ${x.change_pct > 0 ? '+' : ''}${x.change_pct}%
            </span> ${esc(x.reason)}`,

            ...d.room_types.map(t => {

              const p = x.prices[t.id];

              return `
                ${money(p.current)}

                ${p.current !== p.suggested ? `

                  <br>

                  <b class="${p.suggested > p.current ? 'up' : 'down'}">
                    ${money(p.suggested)}
                  </b>

                ` : ''}

              `;

            })

          ])

        )}

      </div>

      <p style="color:var(--muted)">
        Black: price guests see now. Coloured: AI suggestion.
      </p>
    `);

  },


  async forecast() {

    const f = await api('/forecast?weeks=8');

    view(
      head(
        'Occupancy forecast',
        'Next 8 weeks. A gradient boosting model trained on this hotel\'s own booking history.'
      ) +

      `

      <div class="panel">

        ${bars(
          f.map(x => ({
            label:fmtDate(x.week_start),
            value:Math.round(x.occupancy * 100),
            color:x.festival ? '#e5a50f' : '#0e5a4a'
          })),
          v => v + '%'
        )}

        <p style="color:var(--muted)">
          Gold bars include a festival period.
        </p>

      </div>

      <div class="panel">

        ${table(
          ['Week of', 'Forecast', 'Already booked', 'Festival'],

          f.map(x => [
            fmtDate(x.week_start),
            Math.round(x.occupancy * 100) + '%',
            Math.round(x.on_the_books * 100) + '%',
            esc(x.festival || '')
          ])
        )}

      </div>
    `);

  },


  async dashboard() {

    const d = await api('/dashboard');

    view(
      head(
        'Dashboard',
        `${d.total_rooms} rooms. Last 30 days unless stated.`
      ) +

      `

      <div class="kpis">

        ${[
          ['Occupancy today', d.occupancy_today + '%'],
          ['Occupancy (30 days)', d.occupancy_30d + '%'],
          ['Average daily rate', money(d.adr)],
          ['Revenue per room (RevPAR)', money(d.revpar)],
          ['Room revenue', money(d.revenue_30d)],
          ['Average rating', d.avg_rating ?? '-']
        ].map(([l, v]) => `

          <div class="kpi">
            <b>${v}</b>
            <span>${l}</span>
          </div>

        `).join('')}

      </div>

      <div class="panel">

        <h3>Daily occupancy</h3>
        ${line(d.trend)}

      </div>

      <div class="panel">

        <h3>Monthly room revenue</h3>

        ${bars(
          d.monthly.map(m => ({
            label:m.label,
            value:m.revenue
          })),
          v => (v / 100000).toFixed(1) + 'L'
        )}

      </div>

      <div class="panel">

        <h3>Revenue by room type (30 days)</h3>

        ${bars(
          d.revenue_by_type.map(m => ({
            label:m.label,
            value:Number(m.revenue)
          })),
          v => (v / 100000).toFixed(1) + 'L'
        )}

      </div>

      <div class="panel">

        <h3>Operations</h3>

        <p>
          Rooms:
          ${Object.entries(d.room_status)
            .map(([k, v]) => `${k} ${v}`).join(' · ')}
        </p>

        <p>
          Requests:
          ${Object.entries(d.requests)
            .map(([k, v]) => `${k.replace('_', ' ')} ${v}`).join(' · ')}
        </p>

        <p>
          Reviews:
          ${d.reviews.map(r => `${r.sentiment} ${r.c}`).join(' · ')}
        </p>

      </div>
    `);

  },


  /* ADMIN */

  async roomtypes() {

    const t = await api('/room-types');

    view(
      head('Rooms and types') +

      `

      <div class="panel table-wrap">

        ${table(
          ['Type', 'Rooms', 'Base price', 'Capacity', ''],

          t.map(x => [

            esc(x.name),
            x.room_count,
            money(x.base_price),
            x.capacity,

            `<button
              class="btn small"
              data-act="edittype"
              data-id="${x.id}"
              data-n="${esc(x.name)}"
              data-p="${x.base_price}"
              data-c="${x.capacity}"
              data-d="${esc(x.description)}">
              Edit
            </button>`

          ])
        )}

      </div>

      <form class="panel row" data-form="newtype">

        <label>
          New type
          <input name="name" required>
        </label>

        <label>
          Base price (₹)
          <input name="base_price" type="number" min="500" required>
        </label>

        <label>
          Capacity
          <input name="capacity" type="number" min="1" max="10" value="2">
        </label>

        <button class="btn primary">Add room type</button>

      </form>

      <form class="panel row" data-form="newroom">

        <label>
          Room number
          <input name="number" required maxlength="10">
        </label>

        <label>
          Type
          <select name="room_type_id">

            ${t.map(x => `
              <option value="${x.id}">
                ${esc(x.name)}
              </option>
            `).join('')}

          </select>
        </label>

        <label>
          Floor
          <input name="floor" type="number" value="1" min="0">
        </label>

        <button class="btn primary">Add room</button>

      </form>
    `);

  },


  async catalog() {

    const s = await api('/services');

    view(
      head('Services', 'Guests pick from this catalogue when they ask for something.') +

      `

      <div class="panel table-wrap">

        ${table(
          ['Service', 'Type', 'Price'],

          s.map(x => [
            esc(x.name),
            x.category,
            x.price > 0 ? money(x.price) : 'Free'
          ])
        )}

      </div>

      <form class="panel row" data-form="newservice">

        <label>
          Name
          <input name="name" required>
        </label>

        <label>
          Type
          <select name="category">
            <option>housekeeping</option>
            <option>food</option>
            <option>maintenance</option>
          </select>
        </label>

        <label>
          Price (₹)
          <input type="number" name="price" min="0" value="0">
        </label>

        <button class="btn primary">Add service</button>

      </form>
    `);

  },


  async users() {

    const u = await api('/users');

    view(
      head('Users') +

      `

      <div class="panel table-wrap">

        ${table(
          ['Name', 'Email', 'Role', 'Status', ''],

          u.map(x => [

            esc(x.name),
            esc(x.email),
            x.role,
            x.active ? 'Active' : 'Disabled',

            x.id === user.id ? '' : `

              <button
                class="btn small"
                data-act="toggleuser"
                data-id="${x.id}"
                data-a="${x.active ? 0 : 1}"
              >
                ${x.active ? 'Disable' : 'Enable'}
              </button>

            `

          ])
        )}

      </div>

      <form class="panel row" data-form="newuser">

        <label>
          Name
          <input name="name" required>
        </label>

        <label>
          Email
          <input name="email" type="email" required>
        </label>

        <label>
          Password
          <input name="password" type="password" minlength="8" required>
        </label>

        <label>
          Role

          <select name="role">
            <option value="staff">Front office</option>
            <option value="manager">Manager</option>
            <option value="admin">Admin</option>
            <option value="guest">Guest</option>
          </select>

        </label>

        <button class="btn primary">Create user</button>

      </form>
    `);

  }

};


/* ==========================================
   TABLE GENERATOR
========================================== */

function table(h, rows) {

  return `
    <table>

      <thead>
        <tr>
          ${h.map(x => `<th>${x}</th>`).join('')}
        </tr>
      </thead>

      <tbody>

        ${rows.map(r => `
          <tr>
            ${r.map(c => `<td>${c}</td>`).join('')}
          </tr>
        `).join('')}

      </tbody>

    </table>
  `;

}


/* ==========================================
   ROOM SEARCH AND AVAILABILITY
========================================== */

async function searchRooms() {

  const el = $('#results');

  const s = state.search;

  try {

    const r = await api(
      `/availability?check_in=${s.check_in}&check_out=${s.check_out}&guests=${s.guests}`
    );

    const nights = r[0]?.nights || 1;

    el.innerHTML = `

      <p class="result-note">
        ${fmtDate(s.check_in)} to ${fmtDate(s.check_out)}
        · ${nights} night(s)
        · ${s.guests} guest(s)
      </p>

      <div class="rooms-grid">

        ${r.map(x => {

          const badges = `

            <span class="badge cap">
              Up to ${x.capacity} guests
            </span>

          ` +

          (x.available && x.available <= 5 ? `

            <span class="badge hot">
              Only ${x.available} left
            </span>

          ` : '') +

          (x.festival_pricing ? `

            <span class="badge fest">
              Demand pricing
            </span>

          ` : '');

          return `

            <article class="room-card ${x.available ? '' : 'soldout'}">

              ${roomPic(x.name, badges)}

              <div class="rc-body">

                <h3>${esc(x.name)}</h3>

                <p>${esc(x.description)}</p>

                <div class="amen">

                  ${(AMEN[x.name] || [
                    'Free Wi-Fi',
                    'Air conditioning'
                  ]).map(a => `
                    <span>${a}</span>
                  `).join('')}

                </div>

                <div class="rc-foot">

                  <div>

                    <span class="price">
                      ${money(x.avg_price)}
                    </span>

                    <small>/ night</small>

                    <p>${money(x.total)} total</p>

                  </div>

                  <button
                    class="btn primary"
                    ${x.available ? '' : 'disabled'}
                    data-act="bookroom"
                    data-id="${x.id}"
                  >
                    ${x.available ? 'Book now' : 'Sold out'}
                  </button>

                </div>

              </div>

            </article>

          `;

        }).join('') || empty('No room fits that many guests.')}

      </div>
    `;

  } catch (e) {

    el.innerHTML = `<p class="error">${esc(e.message)}</p>`;

  }

}


/* ==========================================
   BUTTON ACTIONS
========================================== */

const acts = {

  close: () => $('#dlg').close(),

  go: d => go(d.p),


  async bookroom(d) {

    const s = state.search;

    const booking = {
      room_type_id: +d.id,
      ...s,
      guests: +s.guests
    };

    const order = await api('/payments/orders', {
      method: 'POST',
      body: booking
    });

    if (!order.required) {
      await api('/bookings', {
        method: 'POST',
        body: booking
      });

      toast('Booking confirmed.');
      go('stays');
      return;
    }

    if (!window.Razorpay) {
      throw new Error('Payment checkout could not load. Please refresh and try again.');
    }

    const checkout = new Razorpay({
      key: order.key_id,
      amount: order.amount,
      currency: order.currency,
      name: 'StayGenius',
      description: 'Room booking',
      order_id: order.order_id,
      prefill: {
        name: order.name,
        email: order.email
      },
      theme: { color: '#0e5a4a' },
      handler: async response => {
        try {
          await api('/payments/verify', {
            method: 'POST',
            body: response
          });

          toast('Payment successful. Booking confirmed.');
          go('stays');
        } catch (error) {
          toast(error.message, true);
        }
      },
      modal: {
        ondismiss: () => toast('Payment not completed. You can retry within 15 minutes.', true)
      }
    });

    checkout.on('payment.failed', response => {
      toast(response.error?.description || 'Payment failed. Please try again.', true);
    });

    checkout.open();

  },


  async cancel(d) {

    if (!confirm('Cancel this booking?')) return;

    await api(`/bookings/${d.id}/cancel`, {
      method: 'POST'
    });

    toast('Booking cancelled.');

    go(state.page);

  },


  async checkin(d) {

    await api(`/bookings/${d.id}/checkin`, {
      method: 'POST'
    });

    toast('Guest checked in.');

    go('frontdesk');

  },


  async checkout(d) {

    const i = await api(`/bookings/${d.id}/checkout`, {
      method: 'POST'
    });

    toast('Checked out. Room sent to housekeeping.');

    invoiceDialog(i);

    go('frontdesk');

  },


  async invoice(d) {

    invoiceDialog(
      await api(`/bookings/${d.id}/invoice`)
    );

  },


  reqform() {

    api('/services').then(s => dialog(`

      <h3>Request a service</h3>

      <form data-form="request">

        <label>
          Choose from the menu

          <select name="service_id">

            <option value="">Something else</option>

            ${s.map(x => `
              <option value="${x.id}">
                ${esc(x.name)}
                ${x.price > 0 ? ' - ' + money(x.price) : ''}
              </option>
            `).join('')}

          </select>

        </label>

        <label>
          Type

          <select name="category">
            <option>housekeeping</option>
            <option>food</option>
            <option>maintenance</option>
          </select>

        </label>

        <label>
          Details
          <input name="description" maxlength="300">
        </label>

        <button class="btn primary">Send request</button>

      </form>

    `));

  },


  reviewform(d) {

    dialog(`

      <h3>How was your stay?</h3>

      <form data-form="review">

        <input type="hidden" name="booking_id" value="${d.id}">

        <div class="stars" role="radiogroup" aria-label="Rating">

          ${[1, 2, 3, 4, 5].map(n => `
            <label>
              <input type="radio" name="rating" value="${n}" required>
              <span>★</span>
            </label>
          `).join('')}

        </div>

        <label>
          Your comments

          <textarea
            name="comment"
            rows="4"
            required
            maxlength="1500"
          ></textarea>

        </label>

        <button class="btn primary">Send feedback</button>

      </form>

    `);

  },


  roomdlg(d) {

    dialog(`

      <h3>Room ${esc(d.n)}</h3>

      <p>Now: ${tag(d.s)}</p>

      ${['vacant', 'cleaning', 'maintenance'].map(s => `

        <button
          class="btn"
          data-act="roomstatus"
          data-id="${d.id}"
          data-s="${s}"
        >
          ${s}
        </button>

      `).join(' ')}

    `);

  },


  async roomstatus(d) {

    await api(`/rooms/${d.id}/status`, {
      method: 'PATCH',
      body: {
        status: d.s
      }
    });

    if ($('#dlg').open) {
      $('#dlg').close();
    }

    toast('Room updated.');

    go(state.page);

  },


  async reqstatus(d) {

    await api(`/service-requests/${d.id}`, {
      method: 'PATCH',
      body: {
        status: d.s
      }
    });

    go('requests');

  },


  async draft(d) {

    const r = await api(`/reviews/${d.id}/draft-reply`, {
      method: 'POST'
    });

    $('#rp' + d.id).innerHTML = `

      <form data-form="reply" data-id="${d.id}">

        <label>

          ${r.ai
            ? 'AI draft (edit before posting)'
            : 'Draft (add a Gemini key for AI-written replies)'
          }

          <textarea name="reply" rows="6">${esc(r.draft)}</textarea>

        </label>

        <button class="btn primary">Post reply</button>

      </form>

    `;

  },


  async applyall() {

    const items = [];

    state.sug.days.forEach(x => {

      state.sug.room_types.forEach(t => {

        const p = x.prices[t.id];

        if (p.current !== p.suggested) {

          items.push({
            room_type_id: t.id,
            date: x.date,
            price: p.suggested
          });

        }

      });

    });

    if (!items.length) {
      return toast('Prices already match the suggestions.');
    }

    const r = await api('/pricing/apply', {
      method: 'POST',
      body: { items }
    });

    toast(r.applied + ' prices approved.');

    go('pricing');

  },


  edittype(d) {

    dialog(`

      <h3>Edit ${esc(d.n)}</h3>

      <form data-form="edittype" data-id="${d.id}">

        <label>
          Base price (₹)
          <input name="base_price" type="number" value="${d.p}" required>
        </label>

        <label>
          Capacity
          <input name="capacity" type="number" value="${d.c}" required>
        </label>

        <label>
          Description
          <input name="description" value="${esc(d.d)}">
        </label>

        <button class="btn primary">Save</button>

      </form>

    `);

  },


  async toggleuser(d) {

    await api('/users/' + d.id, {
      method: 'PATCH',
      body: {
        active: d.a === '1'
      }
    });

    go('users');

  }

};


/* ==========================================
   INVOICE
========================================== */

function invoiceDialog(i) {

  dialog(

    `<h3>Invoice · Room ${esc(i.room_number)}</h3>

    <p>
      ${esc(i.guest_name)}
      · ${fmtDate(i.check_in)}
      to ${fmtDate(i.check_out)}
      ${i.final === false ? ' (preview)' : ''}
    </p>` +

    table(

      ['Item', 'Amount'],

      [

        [
          `${i.nights} night(s) × ${money(i.rate)}`,
          money(i.room_charges)
        ],

        ...i.services.map(s => [
          esc(s.description),
          money(s.price)
        ]),

        [
          'GST (12% rooms, 5% services)',
          money(i.tax)
        ],

        [
          '<b>Total</b>',
          `<b>${money(i.total)}</b>`
        ]

      ]

    ) +

    '<p><button class="btn" onclick="window.print()">Print</button></p>'

  );

}


/* ==========================================
   FORM SUBMISSIONS
========================================== */

const forms = {


  async search(v) {

    state.search = {
      check_in: v.check_in,
      check_out: v.check_out,
      guests: v.guests
    };

    await searchRooms();

  },


  async chat(v, f) {

    const c = $('#chat');
    const history = state.assistantHistory.slice(-8);

    const userMessage = document.createElement('div');
    userMessage.className = 'msg me';
    userMessage.textContent = v.message;
    c.append(userMessage);

    f.message.value = '';

    const thinking = document.createElement('div');
    thinking.className = 'msg thinking';
    thinking.textContent = 'StayGenius is thinking...';
    c.append(thinking);
    c.scrollTop = c.scrollHeight;

    try {
      const r = await api('/assistant', {
        method: 'POST',
        body: { ...v, history }
      });

      const confirmation = r.request_id
        ? `\n\nRequest #${r.request_id} has been sent to the hotel team.`
        : '';
      const reply = document.createElement('div');
      reply.className = 'msg';
      reply.textContent = r.reply + confirmation;
      thinking.remove();
      c.append(reply);

      state.assistantHistory = [
        ...history,
        { role: 'user', content: v.message },
        { role: 'assistant', content: r.reply }
      ].slice(-12);
    } catch (error) {
      thinking.textContent = 'I could not reach the concierge. Please try again.';
      throw error;
    }

    c.scrollTop = c.scrollHeight;

  },


  async profile(v, f) {

    await api('/me/profile', {
      method: 'PUT',

      body: {
        phone: v.phone,
        language: v.language,

        preferences: [
          ...f.querySelectorAll('[name=pref]:checked')
        ].map(x => x.value)
      }
    });

    toast('Preferences saved.');

  },


  async request(v) {

    await api('/service-requests', {
      method: 'POST',

      body: {
        ...v,
        service_id: v.service_id || null
      }
    });

    $('#dlg').close();

    toast('Request sent.');

    go('stays');

  },


  async review(v) {

    const r = await api('/reviews', {
      method: 'POST',

      body: {
        ...v,
        rating: +v.rating,
        booking_id: +v.booking_id
      }
    });

    $('#dlg').close();

    toast('Thank you. Feedback detected as ' + r.sentiment + '.');

    go('stays');

  },


  async reply(v, f) {

    await api(`/reviews/${f.dataset.id}/reply`, {
      method: 'PUT',
      body: v
    });

    toast('Reply posted.');

    go('reviews');

  },


  async newtype(v) {

    await api('/room-types', {
      method: 'POST',

      body: {
        ...v,
        base_price: +v.base_price,
        capacity: +v.capacity
      }
    });

    toast('Room type added.');

    go('roomtypes');

  },


  async newroom(v) {

    await api('/rooms', {
      method: 'POST',

      body: {
        ...v,
        room_type_id: +v.room_type_id,
        floor: +v.floor
      }
    });

    toast('Room added.');

    go('roomtypes');

  },


  async edittype(v, f) {

    await api('/room-types/' + f.dataset.id, {
      method: 'PUT',

      body: {
        ...v,
        base_price: +v.base_price,
        capacity: +v.capacity
      }
    });

    $('#dlg').close();

    toast('Saved.');

    go('roomtypes');

  },


  async newservice(v) {

    await api('/services', {
      method: 'POST',

      body: {
        ...v,
        price: +v.price
      }
    });

    toast('Service added.');

    go('catalog');

  },


  async newuser(v) {

    await api('/users', {
      method: 'POST',
      body: v
    });

    toast('User created.');

    go('users');

  }

};


/* ==========================================
   LOGIN AND REGISTRATION
========================================== */

let registering = false;

$('#toggle-auth').onclick = () => {

  registering = !registering;

  $('#reg-name').hidden =
    $('#reg-name').parentElement.hidden = !registering;

  $('#reg-name').required = registering;

  $('#auth-title').textContent =
    $('#auth-submit').textContent =
      registering ? 'Create guest account' : 'Sign in';

  $('#toggle-auth').textContent =
    registering
      ? 'Already registered? Sign in'
      : 'New guest? Create an account';

};

$('#reg-name').parentElement.hidden = true;


/* DEMO ACCOUNT BUTTONS */

document.querySelectorAll('[data-demo]').forEach(b => {

  b.onclick = () => {

    const [e, p] = b.dataset.demo.split('|');

    const f = $('#login-form');

    f.email.value = e;
    f.password.value = p;

  };

});


/* LOGIN FORM SUBMISSION */

$('#login-form').addEventListener('submit', async e => {

  e.preventDefault();

  e.stopImmediatePropagation();

  $('#auth-error').textContent = '';

  const f = e.target;

  const body = {
    email: f.email.value,
    password: f.password.value,
    name: f.elements.name.value
  };

  try {

    const r = await api(
      registering ? '/auth/register' : '/auth/login',
      {
        method: 'POST',
        body
      }
    );

    token = r.token;
    user = r.user;

    sessionStorage.setItem('sg_token', token);

    sessionStorage.setItem(
      'sg_user',
      JSON.stringify(user)
    );

    f.password.value = '';

    enter();

  } catch (x) {

    $('#auth-error').textContent = x.message;

  }

}, true);


/* LOGOUT BUTTON */

$('#logout').onclick = logout;


/* ==========================================
   GLOBAL BUTTON EVENT HANDLING
========================================== */

document.addEventListener('click', async e => {

  const b = e.target.closest('[data-act]');

  if (!b || !acts[b.dataset.act]) return;

  try {

    b.disabled = true;

    await acts[b.dataset.act](b.dataset, b);

  } catch (x) {

    toast(x.message, true);

  } finally {

    b.disabled = false;

  }

});


/* ==========================================
   GLOBAL FORM EVENT HANDLING
========================================== */

document.addEventListener('submit', async e => {

  const f = e.target.closest('[data-form]');

  if (!f || !forms[f.dataset.form]) return;

  e.preventDefault();

  const btn = f.querySelector('button:not([type=button])');

  if (btn) {
    btn.disabled = true;
  }

  try {

    await forms[f.dataset.form](
      Object.fromEntries(new FormData(f)),
      f
    );

  } catch (x) {

    toast(x.message, true);

  } finally {

    if (btn) {
      btn.disabled = false;
    }

  }

});


/* ==========================================
   FILTER CHANGE EVENTS
========================================== */

document.addEventListener('change', e => {

  if (e.target.id === 'fdview') {

    state.fdView = e.target.value;

    go('frontdesk');

  }

  if (e.target.id === 'pdays') {

    state.days = +e.target.value;

    go('pricing');

  }

});


/* ==========================================
   APPLICATION INITIALIZATION
========================================== */

if (token && user) {

  enter();

} else {

  showLanding();

}