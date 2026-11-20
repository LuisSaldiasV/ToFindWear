// Pestana Outfits: combinaciones de Sanzo Wada + colorimetria personal por estaciones.
// Usa DATA, $, clp, esc y render() de la pagina principal, y window.WADA de wada.js.
(() => {
'use strict';
const W = window.WADA;
if (!W) return;

// ================= Color: hex -> Lab, diferencia CIEDE2000 =================
const _lab = new Map();
function LAB(hex) {
  if (_lab.has(hex)) return _lab.get(hex);
  const ok = /^#[0-9a-f]{6}$/i.test(hex || '');
  const n = parseInt(ok ? hex.slice(1) : '888888', 16);
  const [r, g, b] = [n >> 16 & 255, n >> 8 & 255, n & 255].map(v => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
  const f = t => t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116;
  const x = f((r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047), y = f(r * 0.2126 + g * 0.7152 + b * 0.0722),
    z = f((r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883);
  const lab = [116 * y - 16, 500 * (x - y), 200 * (y - z)];
  _lab.set(hex, lab);
  return lab;
}
function de2000([L1, a1, b1], [L2, a2, b2]) {
  const rad = Math.PI / 180, deg = 180 / Math.PI, p7 = c => c ** 7 / (c ** 7 + 25 ** 7);
  const Cm = (Math.hypot(a1, b1) + Math.hypot(a2, b2)) / 2, G = 0.5 * (1 - Math.sqrt(p7(Cm)));
  const a1p = a1 * (1 + G), a2p = a2 * (1 + G), C1p = Math.hypot(a1p, b1), C2p = Math.hypot(a2p, b2);
  const hue = (b, a) => { if (!a && !b) return 0; const h = Math.atan2(b, a) * deg; return h < 0 ? h + 360 : h; };
  const h1p = hue(b1, a1p), h2p = hue(b2, a2p);
  let dhp = 0;
  if (C1p * C2p) { dhp = h2p - h1p; if (dhp > 180) dhp -= 360; else if (dhp < -180) dhp += 360; }
  const dLp = L2 - L1, dCp = C2p - C1p, dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin(dhp * rad / 2);
  const Lm = (L1 + L2) / 2, Cmp = (C1p + C2p) / 2;
  let hm = h1p + h2p;
  if (C1p * C2p) { if (Math.abs(h1p - h2p) > 180) hm += hm < 360 ? 360 : -360; hm /= 2; }
  const T = 1 - 0.17 * Math.cos((hm - 30) * rad) + 0.24 * Math.cos(2 * hm * rad) + 0.32 * Math.cos((3 * hm + 6) * rad) - 0.2 * Math.cos((4 * hm - 63) * rad);
  const SL = 1 + 0.015 * (Lm - 50) ** 2 / Math.sqrt(20 + (Lm - 50) ** 2), SC = 1 + 0.045 * Cmp, SH = 1 + 0.015 * Cmp * T;
  const RT = -Math.sin(2 * 30 * Math.exp(-(((hm - 275) / 25) ** 2)) * rad) * 2 * Math.sqrt(p7(Cmp));
  return Math.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH));
}
const _de = new Map();
function dE(h1, h2) {
  const k = h1 < h2 ? h1 + h2 : h2 + h1;
  if (!_de.has(k)) _de.set(k, de2000(LAB(h1), LAB(h2)));
  return _de.get(k);
}

// ================= Estaciones =================
// t: temperatura ideal (-1 fria .. +1 calida). L: luminosidad comoda. C: intensidad comoda.
// N: luminosidad aceptable para neutros sin color (negro/gris/blanco).
const SUB = {
  'primavera-clara':     {est: 'primavera', nombre: 'Primavera clara', t: 0.4, L: [65, 93], C: [12, 45], N: [70, 97],
    dif: 'La más luminosa de primavera. Le van los tonos claros y suaves con base cálida: durazno, marfil, celeste agua. A diferencia de la cálida, aguanta colores menos dorados; evita los oscuros.'},
  'primavera-calida':    {est: 'primavera', nombre: 'Primavera cálida', t: 0.9, L: [50, 85], C: [28, 65], N: [75, 95],
    dif: 'La más dorada de primavera: todo con base amarilla, como coral, camel y verde manzana. Evita los grises fríos y el negro.'},
  'primavera-brillante': {est: 'primavera', nombre: 'Primavera brillante', t: 0.3, L: [45, 85], C: [45, 85], N: [60, 97],
    dif: 'La más intensa de primavera: colores vivos y limpios como turquesa o rojo amapola. Tolera algo de frío. Evita lo apagado o polvoriento.'},
  'verano-claro':        {est: 'verano', nombre: 'Verano claro', t: -0.3, L: [65, 90], C: [6, 30], N: [65, 92],
    dif: 'El más claro del verano: lavanda, celeste y rosa palo. Evita los oscuros y los colores muy saturados.'},
  'verano-frio':         {est: 'verano', nombre: 'Verano frío', t: -0.9, L: [45, 80], C: [12, 40], N: [45, 88],
    dif: 'El más frío del verano, con base azul: azul grisáceo, frambuesa suave, gris azulado. Evita los naranjos y los dorados.'},
  'verano-suave':        {est: 'verano', nombre: 'Verano suave', t: -0.2, L: [40, 72], C: [4, 25], N: [35, 80],
    dif: 'El más apagado del verano: tonos polvorientos casi neutros, como salvia, malva y gris topo. Evita lo vivo y los contrastes fuertes.'},
  'otono-suave':         {est: 'otono', nombre: 'Otoño suave', t: 0.2, L: [40, 70], C: [6, 30], N: [35, 85],
    dif: 'El más apagado del otoño: cálido pero suave, como oliva claro, camel y salvia. Evita el negro puro y los colores eléctricos.'},
  'otono-calido':        {est: 'otono', nombre: 'Otoño cálido', t: 0.9, L: [30, 65], C: [25, 60], N: [25, 85],
    dif: 'El más cálido del otoño: tierras ricas como terracota, mostaza, óxido y oliva. Evita los rosas fríos y el gris azulado.'},
  'otono-profundo':      {est: 'otono', nombre: 'Otoño profundo', t: 0.4, L: [15, 50], C: [15, 50], N: [8, 80],
    dif: 'El más oscuro del otoño: chocolate, verde bosque, burdeo y petróleo. A diferencia de los otros otoños, tolera el negro. Evita los pasteles.'},
  'invierno-profundo':   {est: 'invierno', nombre: 'Invierno profundo', t: -0.3, L: [8, 45], C: [15, 60], N: [0, 100],
    dif: 'El más oscuro del invierno: negro, azul marino, burdeo frío, verde esmeralda. Admite algo de calidez. Evita los tonos tierra apagados.'},
  'invierno-frio':       {est: 'invierno', nombre: 'Invierno frío', t: -0.9, L: [10, 95], C: [28, 75], N: [0, 100],
    dif: 'El más frío del invierno: blanco puro, negro, azul rey, fucsia. Evita el beige, el naranjo y los dorados.'},
  'invierno-brillante':  {est: 'invierno', nombre: 'Invierno brillante', t: -0.3, L: [10, 95], C: [45, 90], N: [0, 100],
    dif: 'El de mayor contraste: colores saturados como rojo puro o azul eléctrico, junto con negro y blanco. Evita lo apagado.'},
};
const EST = {
  primavera: {nombre: 'Primavera', txt: 'Cálida, clara y luminosa. Colores frescos con base dorada.'},
  verano:    {nombre: 'Verano', txt: 'Fría, clara y suave. Colores empolvados con base azul.'},
  otono:     {nombre: 'Otoño', txt: 'Cálida, profunda y apagada. Tonos tierra y especias.'},
  invierno:  {nombre: 'Invierno', txt: 'Fría, profunda y de alto contraste. Colores nítidos, negro y blanco puro.'},
};
const fuera = (v, [a, b]) => v < a ? a - v : v > b ? v - b : 0;
const _ps = new Map();
// 0..100: que tan bien le queda un color a una estacion (o subestacion)
function puntaje(hex, clave) {
  if (!clave) return 100;
  const k = hex + clave;
  if (_ps.has(k)) return _ps.get(k);
  let v;
  if (EST[clave]) {
    v = Math.max(...Object.keys(SUB).filter(s => SUB[s].est === clave).map(s => puntaje(hex, s)));
  } else {
    const s = SUB[clave], [L, a, b] = LAB(hex), C = Math.hypot(a, b);
    const temp = Math.max(-1, Math.min(1, b / 25)) * Math.min(1, C / 15);   // amarillo = calido, azul = frio
    let pen = Math.abs(temp - s.t) * 28;
    if (C < 6) pen = pen * 0.3 + fuera(L, s.N) * 1.3;                     // neutros sin color
    else pen += fuera(L, s.L) * 1.2 + fuera(C, s.C) * 1.0;
    v = Math.max(0, Math.min(100, Math.round(100 - pen)));
  }
  _ps.set(k, v);
  return v;
}
const nombreEst = c => c ? (SUB[c] || EST[c]).nombre : '';

// ================= Estado (preferencias en el navegador) =================
const guardado = (() => { try { return JSON.parse(localStorage.getItem('outfits') || '{}'); } catch (e) { return {}; } })();
const S = Object.assign({est: '', soloEst: false, estricto: false, genero: '', max: 0, misColores: false}, guardado);
function guardar() {
  try { localStorage.setItem('outfits', JSON.stringify({est: S.est, soloEst: S.soloEst, estricto: S.estricto, genero: S.genero, max: S.max, misColores: S.misColores})); } catch (e) {}
}

// ================= Piezas: cada color de cada prenda vigente =================
const SLOTS = ['arriba', 'abajo', 'zapatillas'];
const ROTULO = {arriba: 'Parte superior', abajo: 'Pantalón', zapatillas: 'Zapatillas'};
const PIEZAS = [];
DATA.forEach((p, i) => {
  if (!p.activo || !SLOTS.includes(p.grupo)) return;
  (p.color || []).forEach(c => {
    const v = c.k != null && p.colores ? p.colores[c.k] : null;
    PIEZAS.push({i, p, slot: p.grupo, hex: c.hex, n: c.n, neutro: c.neutro, origen: c.origen,
      img: (v && v.img) || p.img, url: (v && v.url) || p.url});
  });
});
const pasa = z => (!S.genero || z.p.genero === S.genero || z.p.genero === 'unisex') && (!S.max || z.p.precio <= S.max);

// Costo de usar una pieza para un color objetivo: diferencia de color + cuanto le queda a tu estacion.
// La estacion pesa fuerte cerca de la cara (parte superior) y poco en pantalon y zapatillas.
const PESO_EST = {arriba: 1, abajo: 0.3, zapatillas: 0.1};
const COMODIN = {abajo: 14, zapatillas: 10};      // neutros (negro, blanco, denim...) sirven casi siempre abajo
function costo(z, objetivo) {
  let d = dE(z.hex, objetivo);
  if (!S.estricto && z.neutro && COMODIN[z.slot] != null) d = Math.min(d, COMODIN[z.slot]);
  if (S.est) d += PESO_EST[z.slot] * (100 - puntaje(z.hex, S.est)) / 5;
  return d;
}
let _cand = new Map();
function candidatos(slot, objetivo) {
  const k = slot + objetivo;
  if (!_cand.has(k)) {
    const vistos = new Set(), L = [];
    PIEZAS.filter(z => z.slot === slot && pasa(z)).map(z => ({z, c: costo(z, objetivo)}))
      .sort((a, b) => a.c - b.c)
      .forEach(x => { if (!vistos.has(x.z.i)) { vistos.add(x.z.i); L.push(x); } });
    _cand.set(k, L);
  }
  return _cand.get(k);
}
const reiniciarCache = () => { _cand = new Map(); _evals = null; };

// ================= Combinaciones =================
const COMBOS = W.k.map((idx, n) => ({id: n + 1, cols: idx.map(i => W.c[i][1]), nombres: idx.map(i => W.c[i][0])}));
// Asigna los colores de la combinacion a superior / pantalon / zapatillas buscando el menor costo total.
function asignar(cb, fijas) {
  const n = cb.cols.length;
  let mejor = null;
  const r = [...Array(n).keys()];
  for (const a of r) for (const b of r) for (const z of r) {
    if (a === b || (n >= 3 && (a === z || b === z))) continue;
    const as = {arriba: a, abajo: b, zapatillas: z};
    let tot = 0;
    for (const s of SLOTS) {
      const obj = cb.cols[as[s]];
      if (fijas[s]) tot += dE(fijas[s].hex, obj);
      else { const c = candidatos(s, obj)[0]; tot += c ? c.c : 60; }
    }
    if (!mejor || tot < mejor.tot) mejor = {as, tot};
  }
  const est = S.est ? Math.round(puntaje(cb.cols[mejor.as.arriba], S.est) * 0.7
    + cb.cols.filter((_, i) => i !== mejor.as.arriba).reduce((s, h) => s + puntaje(h, S.est), 0) / (n - 1) * 0.3) : null;
  return {as: mejor.as, costo: mejor.tot / 3, est};
}
let _evals = null;
function evaluar() {
  if (!_evals) _evals = COMBOS.map(cb => Object.assign({cb}, asignar(cb, {})));
  return _evals;
}
const calidad = c => c < 8 ? ['Excelente', 'var(--ok)'] : c < 14 ? ['Buena', '#9bd36a'] : c < 22 ? ['Aproximada', 'var(--warn)'] : ['Difícil', 'var(--acc)'];

// ================= Interfaz =================
const sec = document.getElementById('outfits');
let vista = 'catalogo', sel = null, idxSlot = {}, fijas = {}, desde = null, limiteCombos = 48;

const chip = document.createElement('button');
chip.className = 'chip'; chip.textContent = '🎨 Outfits';
document.getElementById('grupos').appendChild(chip);
chip.onclick = () => cambiarVista(vista === 'outfits' ? 'catalogo' : 'outfits');
document.querySelectorAll('#grupos .chip[data-g]').forEach(b => b.addEventListener('click', () => cambiarVista('catalogo')));

function cambiarVista(v) {
  vista = v;
  chip.classList.toggle('on', v === 'outfits');
  if (v === 'outfits') document.querySelectorAll('#grupos .chip[data-g]').forEach(b => b.classList.remove('on'));
  document.getElementById('grid').hidden = v === 'outfits';
  document.getElementById('mas').hidden = v === 'outfits';
  document.getElementById('ctrlCat').hidden = v === 'outfits';
  sec.hidden = v !== 'outfits';
  if (v === 'outfits') pintar();
  window.scrollTo(0, 0);
}

// Chip "Mis colores" en el catalogo: parte superior solo en colores de tu estacion
const chipMis = document.createElement('label');
chipMis.className = 'sw2';
document.getElementById('ctrlCat').appendChild(chipMis);
function pintarChipMis() {
  chipMis.hidden = !S.est;
  chipMis.innerHTML = `<input type="checkbox" ${S.misColores ? 'checked' : ''}> Mis colores (${esc(nombreEst(S.est))})`;
  chipMis.querySelector('input').onchange = e => { S.misColores = e.target.checked; guardar(); render(); };
}
window.filtroExtra = p => !S.est || !S.misColores || p.grupo !== 'arriba' || (p.color || []).some(c => puntaje(c.hex, S.est) >= 60);

// Boton "armar outfit" en cada tarjeta del catalogo
document.addEventListener('click', e => {
  const b = e.target.closest('.armar');
  if (!b) return;
  e.preventDefault(); e.stopPropagation();
  const i = +b.closest('.card').dataset.i, z = PIEZAS.find(x => x.i === i);
  if (!z) return;
  fijas = {[z.slot]: z}; desde = z; sel = null; idxSlot = {};
  cambiarVista('outfits');
}, true);

function swatches(cols, alto = 26) {
  return `<div class="franja" style="height:${alto}px">${cols.map(h => `<i style="background:${h}"></i>`).join('')}</div>`;
}

function pintar() {
  pintarChipMis();
  const evs = evaluar();
  let L = evs;
  if (desde) L = L.filter(e => e.cb.cols.some(h => dE(h, desde.hex) < (desde.neutro ? 9 : 13)));
  if (S.est && S.soloEst) L = L.filter(e => e.est >= 60);
  L = [...L].sort((a, b) => (a.costo + (S.est ? (100 - a.est) / 4 : 0)) - (b.costo + (S.est ? (100 - b.est) / 4 : 0)));
  if (!sel && L.length) elegir(L[0].cb, false);

  sec.innerHTML = `
    <div class="obar">
      <button class="chip ${S.est ? 'on' : ''}" id="btnEst">${S.est ? '🌸 ' + esc(nombreEst(S.est)) : '🌸 Elegir mi estación'}</button>
      ${S.est ? `<label class="sw2"><input type="checkbox" id="soloEst" ${S.soloEst ? 'checked' : ''}> Solo combinaciones para mi estación</label>` : ''}
      <select id="oGen"><option value="">Hombre y mujer</option><option value="hombre">Hombre</option><option value="mujer">Mujer</option></select>
      <input type="number" id="oMax" min="0" step="5000" placeholder="Precio máx. por prenda" value="${S.max || ''}">
      <label class="sw2" title="Si está desactivado, el negro, blanco, gris o denim pueden ocupar el pantalón o las zapatillas aunque no estén en la combinación"><input type="checkbox" id="oEstr" ${S.estricto ? 'checked' : ''}> Wada estricto</label>
    </div>
    ${desde ? `<div class="desde">Combinaciones con <i style="background:${desde.hex}"></i> <b>${esc(desde.n)}</b> de “${esc(desde.p.titulo)}” (${L.length}) <button class="chip" id="quitarDesde">Ver todas</button></div>` : ''}
    <div class="olay">
      <div id="outfit">${sel ? outfitHTML() : '<div class="empty">No hay combinaciones con esos filtros.</div>'}</div>
      <div>
        <div class="ohint">Combinaciones de Sanzo Wada, ordenadas por cuántas prendas reales calzan${S.est ? ' y por tu estación' : ''}.</div>
        <div class="combos">${L.slice(0, limiteCombos).map(e => {
          const [q, col] = calidad(e.costo);
          return `<button class="combo ${sel && sel.cb.id === e.cb.id ? 'on' : ''}" data-id="${e.cb.id}" title="${esc(e.cb.nombres.join(' · '))}">
            ${swatches(e.cb.cols)}<span><b style="color:${col}">●</b> #${e.cb.id} · ${q}${S.est && e.est >= 70 ? ' · ⭐' : ''}</span></button>`;
        }).join('')}</div>
        ${L.length > limiteCombos ? '<button class="chip" id="masCombos">Ver más combinaciones</button>' : ''}
      </div>
    </div>`;

  sec.querySelector('#oGen').value = S.genero;
  sec.querySelector('#btnEst').onclick = abrirEstacion;
  const so = sec.querySelector('#soloEst'); if (so) so.onchange = e => { S.soloEst = e.target.checked; guardar(); sel = null; pintar(); };
  sec.querySelector('#oGen').onchange = e => { S.genero = e.target.value; guardar(); reiniciarCache(); sel = null; pintar(); };
  sec.querySelector('#oMax').onchange = e => { S.max = +e.target.value || 0; guardar(); reiniciarCache(); sel = null; pintar(); };
  sec.querySelector('#oEstr').onchange = e => { S.estricto = e.target.checked; guardar(); reiniciarCache(); sel = null; pintar(); };
  const qd = sec.querySelector('#quitarDesde'); if (qd) qd.onclick = () => { desde = null; fijas = {}; sel = null; pintar(); };
  const mc = sec.querySelector('#masCombos'); if (mc) mc.onclick = () => { limiteCombos += 48; pintar(); };
  sec.querySelectorAll('.combo').forEach(b => b.onclick = () => { elegir(COMBOS[+b.dataset.id - 1]); });
  sec.querySelectorAll('[data-otra]').forEach(b => b.onclick = () => { const s = b.dataset.otra; idxSlot[s] = (idxSlot[s] || 0) + 1; pintarOutfit(); });
  sec.querySelectorAll('[data-fijar]').forEach(b => b.onclick = () => {
    const s = b.dataset.fijar;
    if (fijas[s]) delete fijas[s]; else fijas[s] = piezaDe(s);
    pintarOutfit();
  });
}

function elegir(cb, repintar = true) {
  sel = Object.assign({cb}, asignar(cb, fijas));
  idxSlot = {};
  if (repintar) pintar();
}
function piezaDe(s) {
  if (fijas[s]) return fijas[s];
  const L = candidatos(s, sel.cb.cols[sel.as[s]]);
  return L.length ? L[(idxSlot[s] || 0) % L.length].z : null;
}
function pintarOutfit() {
  const o = sec.querySelector('#outfit');
  o.innerHTML = outfitHTML();
  pintar();   // re-enlaza botones (barato)
}
function outfitHTML() {
  const cb = sel.cb;
  let total = 0, completas = 0;
  const casillas = SLOTS.map(s => {
    const obj = cb.cols[sel.as[s]], z = piezaDe(s);
    if (!z) return `<div class="slot"><div class="srot">${ROTULO[s]}</div><div class="empty">Sin prendas para este color.</div></div>`;
    total += z.p.precio; completas++;
    const d = dE(z.hex, obj), cerca = d < 8 ? 'muy cerca' : d < 15 ? 'cerca' : z.neutro ? 'neutro comodín' : 'aproximado';
    const pe = S.est ? puntaje(z.hex, S.est) : null;
    return `<div class="slot ${fijas[s] ? 'fija' : ''}">
      <div class="srot">${ROTULO[s]} <span class="obj"><i style="background:${obj}"></i>objetivo · <i style="background:${z.hex}"></i>${esc(z.n)} (${cerca})</span></div>
      <a href="${esc(z.url)}" target="_blank" class="simg">${z.img ? `<img src="${esc(z.img)}" loading="lazy" alt="">` : '<span class="nofoto">Sin foto</span>'}</a>
      <div class="marca">${esc(z.p.marca || '—')} · ${esc(z.p.fuente)}</div>
      <div class="tit">${esc(z.p.titulo)}</div>
      <div class="precio">${clp(z.p.precio)}${z.p.precio_antes ? `<s>${clp(z.p.precio_antes)}</s>` : ''}</div>
      ${pe != null && s === 'arriba' ? `<div class="meta"><span>Para tu estación</span><span style="color:${pe >= 70 ? 'var(--ok)' : pe >= 45 ? 'var(--warn)' : 'var(--acc)'}">${pe}/100</span></div>` : ''}
      <div class="sbtn"><button class="chip" data-otra="${s}" ${fijas[s] ? 'disabled' : ''}>↻ Otra</button>
        <button class="chip ${fijas[s] ? 'on' : ''}" data-fijar="${s}">${fijas[s] ? '🔒 Fija' : '🔓 Fijar'}</button>
        <a class="chip" href="${esc(z.url)}" target="_blank">Ver en tienda</a></div>
    </div>`;
  }).join('');
  const [q, col] = calidad(sel.costo);
  return `<div class="ohead">${swatches(cb.cols, 34)}
      <div><b>Combinación #${cb.id}</b> · <span style="color:${col}">${q}</span>${sel.est != null ? ` · estación ${sel.est}/100` : ''}<br>
      <span class="sub">${esc(cb.nombres.join(' · '))}</span></div>
      <div class="total">${completas === 3 ? 'Total' : 'Parcial'}<b>${clp(total)}</b></div></div>
    <div class="slots">${casillas}</div>`;
}

// ================= Panel de estacion y test =================
const modal = document.createElement('div');
modal.className = 'modal'; modal.hidden = true;
document.body.appendChild(modal);
modal.addEventListener('click', e => { if (e.target === modal) cerrar(); });
function cerrar() { modal.hidden = true; }
function aplicarEst(c) {
  S.est = c; guardar(); _ps.clear(); reiniciarCache(); sel = null; cerrar();
  if (vista === 'outfits') pintar(); else { pintarChipMis(); render(); }
}
// Paleta de muestra: los colores de Wada que mejor le quedan a cada estacion
const muestra = c => W.c.map(x => x[1]).sort((a, b) => puntaje(b, c) - puntaje(a, c)).slice(0, 10);

function abrirEstacion(subAbierta) {
  modal.hidden = false;
  modal.innerHTML = `<div class="mbox">
    <div class="mhead"><b>Tu estación de color</b><button class="chip" id="mCerrar">✕</button></div>
    <p class="sub">La colorimetría personal agrupa los colores que favorecen tu tono de piel, pelo y ojos. Lo principal son las 4 estaciones; si quieres afinar, cada una tiene 3 subestaciones.</p>
    <button class="chip on" id="hacerTest">📝 Hacer el test (8 preguntas)</button>
    ${S.est ? '<button class="chip" id="quitarEst">Quitar mi estación</button>' : ''}
    <div class="ests">${Object.keys(EST).map(e => `
      <div class="est ${S.est === e || (SUB[S.est] && SUB[S.est].est === e) ? 'on' : ''}">
        ${swatches(muestra(e), 22)}
        <b>${EST[e].nombre}</b><div class="sub">${EST[e].txt}</div>
        <button class="chip" data-usar="${e}">Usar ${EST[e].nombre}</button>
        <div class="subs">Afinar: ${Object.keys(SUB).filter(s => SUB[s].est === e).map(s =>
          `<button class="chip mini ${typeof subAbierta === 'string' && subAbierta === s ? 'on' : ''}" data-ver="${s}">${SUB[s].nombre.split(' ')[1]}</button>`).join('')}</div>
        ${typeof subAbierta === 'string' && SUB[subAbierta] && SUB[subAbierta].est === e ? `<div class="subdet">${swatches(muestra(subAbierta), 18)}
          <p>${SUB[subAbierta].dif}</p><button class="chip on" data-usar="${subAbierta}">Usar ${SUB[subAbierta].nombre}</button></div>` : ''}
      </div>`).join('')}</div></div>`;
  modal.querySelector('#mCerrar').onclick = cerrar;
  modal.querySelector('#hacerTest').onclick = () => test(0, {});
  const qe = modal.querySelector('#quitarEst'); if (qe) qe.onclick = () => aplicarEst('');
  modal.querySelectorAll('[data-usar]').forEach(b => b.onclick = () => aplicarEst(b.dataset.usar));
  modal.querySelectorAll('[data-ver]').forEach(b => b.onclick = () => abrirEstacion(b.dataset.ver));
}

// T: temperatura (+calida), D: profundidad (+oscura), K: intensidad/contraste (+viva)
const PREGUNTAS = [
  ['Mira las venas de tu muñeca con luz natural. ¿De qué color se ven?', [['Verdosas', {T: 2}], ['Azules o moradas', {T: -2}], ['No sé / una mezcla', {}]]],
  ['¿Qué te favorece más junto a la cara?', [['Dorado', {T: 1.5}], ['Plateado', {T: -1.5}], ['Los dos por igual', {}]]],
  ['Cuando tomas sol…', [['Me bronceo fácil, quedo dorado/a', {T: 1}], ['Me quemo y quedo rosado/a', {T: -1}], ['Ni lo uno ni lo otro', {}]]],
  ['Tu color de pelo natural (sin teñir):', [['Negro o castaño muy oscuro', {D: 2}], ['Castaño medio', {D: 0.5}], ['Castaño claro o rubio', {D: -2}], ['Pelirrojo o cobrizo', {T: 2}]]],
  ['Tus ojos son…', [['Muy oscuros e intensos', {D: 1, K: 0.5}], ['Medios: café claro, avellana, verde oliva', {K: -1}], ['Claros y brillantes: azul o verde intenso', {D: -1, K: 1.5}], ['Claros y grisáceos o apagados', {D: -1, K: -1}]]],
  ['Contraste entre tu pelo y tu piel:', [['Alto (ej. pelo oscuro y piel clara)', {K: 2}], ['Medio', {}], ['Bajo (pelo y piel de tono parecido)', {K: -2}]]],
  ['¿Qué blanco te ilumina más la cara?', [['Blanco puro, brillante', {K: 1, T: -1}], ['Crudo o marfil', {K: -0.5, T: 1}], ['No noto diferencia', {}]]],
  ['Los colores apagados (gris topo, salvia, malva)…', [['Me favorecen, me veo armónico/a', {K: -1.5}], ['Me apagan, me veo cansado/a', {K: 1.5}], ['No sé', {}]]],
];
function test(n, r) {
  if (n >= PREGUNTAS.length) return resultado(r);
  const [q, ops] = PREGUNTAS[n];
  modal.innerHTML = `<div class="mbox">
    <div class="mhead"><b>Test de estación · ${n + 1}/${PREGUNTAS.length}</b><button class="chip" id="mCerrar">✕</button></div>
    <div class="prog"><i style="width:${n / PREGUNTAS.length * 100}%"></i></div>
    <p class="preg">${q}</p>
    <div class="ops">${ops.map((o, k) => `<button class="chip" data-k="${k}">${o[0]}</button>`).join('')}</div>
    ${n ? '<button class="chip mini" id="atras">← Atrás</button>' : ''}</div>`;
  modal.querySelector('#mCerrar').onclick = cerrar;
  const at = modal.querySelector('#atras'); if (at) at.onclick = () => { const r2 = Object.assign({}, r); delete r2[n - 1]; test(n - 1, r2); };
  modal.querySelectorAll('[data-k]').forEach(b => b.onclick = () => test(n + 1, Object.assign({}, r, {[n]: ops[+b.dataset.k][1]})));
}
function resultado(r) {
  const t = {T: 0, D: 0, K: 0};
  Object.values(r).forEach(o => Object.entries(o).forEach(([k, v]) => t[k] += v));
  const calida = t.T > 0 || (t.T === 0 && t.D > 0 && t.K < 0);
  const est = calida ? (t.K - t.D >= 0 ? 'primavera' : 'otono') : (t.K + t.D >= 0 ? 'invierno' : 'verano');
  // rasgo dominante (normalizado por su rango maximo) -> subestacion
  const n = {T: Math.abs(t.T) / 6.5, D: Math.abs(t.D) / 4, K: Math.abs(t.K) / 6};
  const dom = Object.keys(n).sort((a, b) => n[b] - n[a])[0];
  const mapa = {
    primavera: {T: 'primavera-calida', D: 'primavera-clara', K: 'primavera-brillante'},
    otono: {T: 'otono-calido', D: 'otono-profundo', K: 'otono-suave'},
    verano: {T: 'verano-frio', D: 'verano-claro', K: 'verano-suave'},
    invierno: {T: 'invierno-frio', D: 'invierno-profundo', K: 'invierno-brillante'},
  };
  const sub = mapa[est][dom];
  const dudosa = Math.abs(t.T) < 1.5;
  modal.innerHTML = `<div class="mbox">
    <div class="mhead"><b>Tu resultado</b><button class="chip" id="mCerrar">✕</button></div>
    ${swatches(muestra(est), 28)}
    <h2>${EST[est].nombre}</h2><p>${EST[est].txt}</p>
    <div class="subdet">${swatches(muestra(sub), 18)}<p><b>Subestación sugerida: ${SUB[sub].nombre}.</b> ${SUB[sub].dif}</p></div>
    ${dudosa ? '<p class="sub">⚠️ Tus respuestas sobre temperatura (cálido/frío) fueron mixtas, así que el resultado es menos seguro. Prueba poniéndote una prenda de cada estación frente a un espejo con luz natural.</p>' : ''}
    <p class="sub">Es una aproximación, no un análisis profesional. Puedes cambiarla cuando quieras.</p>
    <button class="chip on" data-usar="${est}">Usar ${EST[est].nombre}</button>
    <button class="chip" data-usar="${sub}">Usar ${SUB[sub].nombre}</button>
    <button class="chip" id="rehacer">Repetir test</button></div>`;
  modal.querySelector('#mCerrar').onclick = cerrar;
  modal.querySelector('#rehacer').onclick = () => test(0, {});
  modal.querySelectorAll('[data-usar]').forEach(b => b.onclick = () => aplicarEst(b.dataset.usar));
}

// API minima para pruebas
window.OUTFITS = {LAB, dE, puntaje, asignar, evaluar, PIEZAS, COMBOS, SUB, resultado: r => resultado(r)};
pintarChipMis();
if (S.misColores && S.est) render();
})();
