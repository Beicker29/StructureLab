from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

UI_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>ShearTors RC - UI</title>
<style>
:root{--bg:#eef3f9;--surface:#fff;--line:#c9d6e5;--text:#13243a;--muted:#5a6f8a;--brand:#112d49;--brand2:#0b2239;--accent:#0f5f79;--accent2:#0b4d62;--ok:#1f6b43;--warn:#8c5a00;--err:#a12821}
*{box-sizing:border-box}html,body{height:100%}
body{margin:0;background:linear-gradient(160deg,#e8eff8 0%,var(--bg) 56%,#f6f9fd 100%);color:var(--text);font-family:"IBM Plex Sans","Segoe UI",Tahoma,sans-serif}
.app{min-height:100vh;display:grid;grid-template-columns:250px minmax(0,1fr)}
.sidebar{background:linear-gradient(180deg,var(--brand),var(--brand2));color:#dbe6f2;padding:14px;border-right:1px solid #244564;position:sticky;top:0;height:100vh;display:flex;flex-direction:column;gap:12px}
.brand{border:1px solid rgba(136,167,196,.26);background:rgba(11,28,45,.35);border-radius:12px;padding:11px}
.brand-top{display:flex;align-items:center;gap:10px}
.brand-icon{width:36px;height:36px;display:block}
.brand-word{margin:0;font-size:1.05rem;font-weight:760;line-height:1;letter-spacing:.2px}
.brand-word .structure{color:#f3f8ff}.brand-word .lab{color:#3f98ff}
.brand-sub{margin:8px 0 0;color:#9fb3c9;font-size:.76rem}
.nav{display:grid;gap:7px}.nav button{appearance:none;border:1px solid transparent;background:transparent;color:#d0deec;text-align:left;border-radius:9px;padding:9px 10px;font-size:.88rem;font-weight:620;cursor:pointer}
.nav button:hover{background:rgba(120,152,183,.18);border-color:rgba(155,184,211,.24);color:#f4f8fc}.nav button.active{background:linear-gradient(180deg,#385474,#2a4768);border-color:#4f6884;color:#fff}
.side-foot{margin-top:auto;border-top:1px solid rgba(132,162,190,.2);padding-top:10px;font-size:.75rem;color:#9fb3c9}
.main{padding:14px}.top{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:13px 15px;display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
.top h1{margin:0;font-size:1.2rem}.top p{margin:5px 0 0;color:var(--muted);font-size:.84rem;max-width:820px}
.status{display:inline-flex;align-items:center;min-height:34px;border-radius:999px;border:1px solid #bfd0e4;background:#edf4fb;color:#2a3e56;font-size:.83rem;font-weight:640;padding:7px 12px}
.status.running{border-color:#dcc28f;background:#fff8e9;color:var(--warn)}.status.ok{border-color:#afd4c1;background:#ecf8f1;color:var(--ok)}.status.err{border-color:#e3b0ab;background:#fff1f0;color:var(--err)}
.view{display:none;margin-top:12px;gap:12px}.view.active{display:grid}.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:13px}
.card h2{margin:0 0 6px;font-size:1rem}.note{margin:0 0 10px;color:var(--muted);font-size:.8rem}
.grid{display:grid;gap:10px}.g2{grid-template-columns:repeat(2,minmax(0,1fr))}.g3{grid-template-columns:repeat(3,minmax(0,1fr))}
.field label{display:block;margin-bottom:4px;font-size:.82rem;font-weight:630}.field input,.field select{width:100%;border:1px solid #bfccde;border-radius:8px;padding:9px 10px;font-size:.9rem;background:#fff}
.field input:focus,.field select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(15,95,121,.14)}.field [aria-invalid="true"]{border-color:var(--err);background:#fff8f8}
.help{margin:5px 0 0;color:var(--muted);font-size:.75rem}.field-error{margin:5px 0 0;color:var(--err);font-size:.78rem}
.advanced{border:1px solid #d5e1ef;border-radius:10px;background:#f7fbff}.advanced>summary{list-style:none;cursor:pointer;padding:10px 11px;font-size:.86rem;font-weight:640;color:#1d3c5d}.advanced>summary::-webkit-details-marker{display:none}.advanced[open]>summary{border-bottom:1px solid #d5e1ef}
.adv-body{padding:10px}.adv-block{border:1px solid #d5e1ee;border-radius:10px;padding:10px;background:#fff}.adv-block+.adv-block{margin-top:10px}
.toggle{display:flex;align-items:center;gap:8px;margin-bottom:6px}.toggle input{width:16px;height:16px}.adv-disabled{opacity:.62;pointer-events:none}
.span-list{display:grid;gap:10px;margin-bottom:10px}.span-row{border:1px solid #d4e1ee;border-radius:10px;background:#f9fcff;padding:8px}
.span-summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;gap:8px;align-items:center;padding:5px 8px;border-radius:8px;background:#edf4fb;color:#16324f;font-weight:620;font-size:.84rem}.span-summary::-webkit-details-marker{display:none}
.span-row[open] .span-summary{border:1px solid #cbdced}
.span-summary-meta{font-weight:530;font-size:.78rem;color:#3e5876}
.span-body{display:grid;gap:8px;padding-top:8px}
.span-head{display:grid;grid-template-columns:repeat(5,minmax(0,1fr)) auto;gap:8px;align-items:end}
.region-box{border:1px solid #d6e2ef;border-radius:10px;background:#fff;padding:10px}.region-head{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:8px}
.region-actions{display:flex;flex-wrap:wrap;gap:6px}.region-list{display:grid;gap:8px}
.region-row{border:1px solid #dde7f2;border-radius:8px;padding:8px;background:#fbfdff;display:grid;grid-template-columns:1fr 1fr 1fr .8fr 1fr auto;gap:8px;align-items:end}
.mini-btn{border:1px solid #c9d7e8;border-radius:8px;padding:7px 10px;background:#edf3fb;color:#17314f;font-size:.8rem;font-weight:620;cursor:pointer}.mini-btn-danger{border-color:#e3b7b3;background:#fff2f1;color:#8f2b25}
.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}.btn{min-width:190px;border-radius:10px;border:1px solid transparent;padding:10px 13px;cursor:pointer;font-size:.9rem;font-weight:650;display:inline-flex;align-items:center;justify-content:center;gap:7px}
.btn-primary{color:#fff;background:linear-gradient(180deg,var(--accent),var(--accent2))}.btn-secondary{color:#1f3248;border-color:#c5d2e4;background:#e8edf6}.btn:disabled{opacity:.72;cursor:not-allowed}
.spinner{width:12px;height:12px;border-radius:50%;border:2px solid rgba(255,255,255,.42);border-top-color:#fff;animation:spin .8s linear infinite;display:none}.btn.loading .spinner{display:inline-block}@keyframes spin{to{transform:rotate(360deg)}}
.results{display:grid;gap:12px;grid-template-columns:minmax(0,1fr) 320px}.svg-wrap{border:1px solid #d1deec;border-radius:10px;background:#f5f9ff;overflow:auto;min-height:350px;padding:8px}
.legend{margin-top:8px;color:var(--muted);font-size:.76rem}.list{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:6px;font-size:.82rem}.list li{border:1px solid #d8e3ef;background:#fafcff;border-radius:8px;padding:7px 8px}
.list li.ok{border-color:#badcc9;background:#edf8f2}.list li.warn{border-color:#e6d2aa;background:#fff8ea}.list li.err{border-color:#e7b8b4;background:#fff3f2}
.alert{margin-top:10px;border:1px solid #e4b5b1;background:#fdeceb;border-radius:9px;color:#5f1d1b;padding:9px 10px}.alert h4{margin:0;font-size:.86rem}.alert p{margin:4px 0 0;font-size:.76rem}.alert ul{margin:7px 0 0;padding-left:18px;font-size:.8rem}
.links{margin-top:9px;display:grid;gap:6px}.links a{color:var(--accent);text-decoration:none;font-size:.83rem;font-weight:620}.links a:hover{text-decoration:underline}
.artifact-link{color:#174e80;text-decoration:none;font-weight:620}.artifact-link:hover{text-decoration:underline}
.log{margin-top:8px;border:1px dashed #bfcedf;border-radius:9px;padding:9px;background:#f8fbff;max-height:320px;overflow:auto;font-size:.77rem;font-family:"IBM Plex Mono","Consolas",monospace;white-space:pre-wrap}
.hidden{display:none}
@media (max-width:1180px){.results{grid-template-columns:1fr}.span-head{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:980px){.app{grid-template-columns:1fr}.sidebar{position:static;height:auto;border-right:none;border-bottom:1px solid #294662}.nav{grid-template-columns:repeat(4,minmax(0,1fr))}.nav button{text-align:center;padding:9px 7px}.region-row{grid-template-columns:1fr 1fr 1fr 1fr}}
@media (max-width:740px){.g3,.g2{grid-template-columns:1fr}.region-row{grid-template-columns:1fr}.btn{width:100%}.nav{grid-template-columns:repeat(2,minmax(0,1fr))}.top{flex-direction:column;align-items:flex-start}.span-head{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
<div class="brand"><div class="brand-top"><svg class="brand-icon" viewBox="0 0 64 64" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="slGrad" x1="0" x2="1" y1="0" y2="1"><stop offset="0%" stop-color="#22bde2"/><stop offset="100%" stop-color="#1f5ec7"/></linearGradient></defs><path d="M10 52V24l16-10 13 8v30H10z" fill="none" stroke="url(#slGrad)" stroke-width="4" stroke-linejoin="round"/><path d="M26 14l10-6 18 11v33H39" fill="none" stroke="url(#slGrad)" stroke-width="4" stroke-linejoin="round"/><path d="M20 34h18M20 44h18M26 24v28M34 24v28" stroke="url(#slGrad)" stroke-width="2.5" opacity=".7"/><path d="M15 57h40" stroke="url(#slGrad)" stroke-width="4"/></svg><p class="brand-word"><span class="structure">Structure</span><span class="lab">Lab</span></p></div></div>
<nav id="sidebar-nav" class="nav" aria-label="Navegacion principal">
<button type="button" class="active" data-view="view-design">Diseno</button>
<button type="button" data-view="view-import">Importar ETABS</button>
<button type="button" data-view="view-results">Resultados</button>
<button type="button" data-view="view-reports">Reportes</button>
</nav>
<p class="side-foot">Compatibilidad API preservada: /v1/jobs*</p>
</aside>
<main class="main">
<header class="top"><div><h1>Flujo RC Shear-Torsion</h1><p>Configura parametros de diseno, carga ETABS y revisa resultados con vista SVG en alzado. La capa avanzada permite configurar vanos, apoyos y regiones sin escribir JSON.</p></div><span id="global-status" class="status">Esperando ejecucion</span></header>
<form id="job-form" novalidate>
<section id="view-design" class="view active">
<div class="grid g2">
<section class="card"><h2>Informacion general</h2><p class="note">Parametros base del caso y configuracion de diseno.</p><div class="grid g3">
<div class="field"><label for="api_key">API Key (opcional)</label><input id="api_key" name="api_key" autocomplete="off" placeholder="Solo si APP_API_KEY esta activa" /></div>
<div class="field"><label for="case_name">Nombre del caso</label><input id="case_name" name="case_name" value="case_web" /></div>
<div class="field"><label for="beam_id">ID de viga</label><input id="beam_id" name="beam_id" value="B1" /></div>
<div class="field"><label for="sheet_name">Hoja ETABS</label><input id="sheet_name" name="sheet_name" value="Conc Bm Sum - ACI 318-08" /><p class="help">Debe coincidir exactamente en ambos Excel.</p></div>
<div class="field"><label for="detailing">Detallado</label><select id="detailing" name="detailing"><option value="DMO" selected>DMO</option><option value="DES">DES</option></select></div>
<div class="field"><label for="units_rebar_per_length">Unidad VRebar/TTrnRebar</label><select id="units_rebar_per_length" name="units_rebar_per_length"><option value="mm2/m" selected>mm2/m</option><option value="cm2/m">cm2/m</option></select></div>
</div></section>
<section class="card"><h2>Materiales y geometria</h2><p class="note">Propiedades y dimensiones principales de la viga.</p><div class="grid g2">
<div class="field"><label for="fc_mpa">f'c (MPa)</label><input id="fc_mpa" name="fc_mpa" type="number" value="28" step="0.1" /></div>
<div class="field"><label for="fy_mpa">fy (MPa)</label><input id="fy_mpa" name="fy_mpa" type="number" value="420" step="0.1" /></div>
<div class="field"><label for="width_mm">Ancho de viga (mm)</label><input id="width_mm" name="width_mm" type="number" value="300" step="0.1" /></div>
<div class="field"><label for="height_mm">Altura de viga (mm)</label><input id="height_mm" name="height_mm" type="number" value="600" step="0.1" /></div>
<div class="field"><label for="d_mm">Peralte efectivo d (mm)</label><input id="d_mm" name="d_mm" type="number" value="600" step="0.1" /></div>
<div class="field"><label for="db_bar">Barra longitudinal de referencia (db_bar)</label><select id="db_bar" name="db_bar"><option>#3</option><option>#4</option><option>#5</option><option selected>#6</option><option>#7</option><option>#8</option></select></div>
<div class="field"><label for="cover_side_mm">Recubrimiento lateral (mm)</label><input id="cover_side_mm" name="cover_side_mm" type="number" value="40" step="0.1" /></div>
<div class="field"><label for="cover_top_mm">Recubrimiento superior (mm)</label><input id="cover_top_mm" name="cover_top_mm" type="number" value="40" step="0.1" /></div>
<div class="field"><label for="cover_bottom_mm">Recubrimiento inferior (mm)</label><input id="cover_bottom_mm" name="cover_bottom_mm" type="number" value="40" step="0.1" /></div>
</div></section>
</div>
<section class="card"><h2>Refuerzo base y configuracion avanzada</h2><p class="note">Reglas de armado y opciones avanzadas. Todo se envia como payload compatible al backend.</p>
<input type="hidden" id="min_branches_c" name="min_branches_c" value="4" /><input type="hidden" id="min_branches_nc" name="min_branches_nc" value="2" /><input type="hidden" id="region_c_ratio" name="region_c_ratio" value="0.2" />
<details class="advanced" open><summary>Configuracion avanzada (opcional)</summary><div class="adv-body">
<input type="hidden" id="frame_pairs_json" name="frame_pairs_json" /><input type="hidden" id="optimization_overrides_json" name="optimization_overrides_json" /><input type="hidden" id="span_layout_json" name="span_layout_json" />
<div class="adv-block"><div class="toggle"><input type="checkbox" id="enable_span_layout" /><label for="enable_span_layout">Configurar vanos, apoyos y regiones por vano</label></div><p class="help">Permite definir apoyos/separacion entre vanos y multiples regiones con indicador de confinado.</p><div id="span-layout-fields" class="adv-disabled"><div id="span-layout-list" class="span-list"></div><button type="button" class="mini-btn" id="btn-add-span">Agregar vano</button></div></div>
<div class="adv-block"><div class="toggle"><input type="checkbox" id="enable_optimization_overrides" /><label for="enable_optimization_overrides">Personalizar optimizacion</label></div><p class="help">La UI construye internamente JSON compatible con backend.</p><div id="optimization-fields" class="grid g2 adv-disabled">
<div class="field"><label for="opt_generations">Cantidad de generaciones</label><input id="opt_generations" type="number" min="1" step="1" placeholder="Ej: 80" /><p class="help">Entero >= 1.</p></div>
<div class="field"><label for="opt_e_bars">Diametros para estribos cerrados</label><input id="opt_e_bars" type="text" placeholder="Ej: #3, #4, #6" /><p class="help">Separados por coma.</p></div>
<div class="field"><label for="opt_g_bars">Diametros para ramas simples</label><input id="opt_g_bars" type="text" placeholder="Ej: #3, #4, #6" /><p class="help">Separados por coma.</p></div>
<div class="field"><label for="opt_long_bars">Diametros para refuerzo longitudinal</label><input id="opt_long_bars" type="text" placeholder="Ej: #4, #5, #6" /><p class="help">Separados por coma.</p></div>
<div class="field"><label for="opt_spacing">Espaciamientos posibles de estribos (mm)</label><input id="opt_spacing" type="text" placeholder="Ej: 70, 80, 100" /><p class="help">Enteros positivos separados por coma.</p></div>
<div class="field"><label for="opt_long_counts">Cantidades posibles de barras longitudinales</label><input id="opt_long_counts" type="text" placeholder="Ej: 2, 4, 6, 8" /><p class="help">Enteros positivos separados por coma.</p></div>
</div></div>
</div></details></section></section>
<section id="view-import" class="view"><section class="card"><h2>Importacion ETABS y ejecucion</h2><p class="note">Carga sismo/gravedad y, opcionalmente, geometria para mapear Width/Depth por vano desde DesignSect.</p><div class="grid g3"><div class="field"><label for="seismic_excel">Excel sismico</label><input id="seismic_excel" name="seismic_excel" type="file" accept=".xlsx" required /></div><div class="field"><label for="gravity_excel">Excel gravedad</label><input id="gravity_excel" name="gravity_excel" type="file" accept=".xlsx" required /></div><div class="field"><label for="geometry_excel">Excel geometria (opcional)</label><input id="geometry_excel" name="geometry_excel" type="file" accept=".xlsx" /></div></div><div class="actions"><button type="submit" class="btn btn-primary" id="btn-submit"><span class="spinner" aria-hidden="true"></span><span id="btn-submit-label">Crear y ejecutar job</span></button><button type="button" class="btn btn-secondary" id="btn-clear">Limpiar estado</button></div></section></section>
<section id="view-results" class="view"><div class="results"><section class="card"><h2>Resultados - Vista en alzado de la viga</h2><p class="note">Preview SVG con vanos, apoyos, regiones, espaciamientos y arreglo transversal/longitudinal.</p><div id="beam-elevation-container" class="svg-wrap" aria-live="polite"></div><p id="beam-elevation-legend" class="legend">El SVG usa datos reales del case/job cuando existen, y fallback tecnico cuando faltan.</p></section><div class="grid"><section class="card"><h2>Estado del job</h2><p class="note">Monitoreo en tiempo real, errores y trazabilidad.</p><span id="status" class="status">Esperando ejecucion</span><div id="error-box" class="alert hidden" role="alert" aria-live="assertive"></div><details style="margin-top:10px"><summary style="cursor:pointer;font-size:.82rem;color:#315171;font-weight:620">Ver detalle de respuesta</summary><pre id="details" class="log hidden"></pre></details></section><section class="card"><h2>Resumen tecnico</h2><ul id="summary-list" class="list"></ul></section><section class="card"><h2>Checks visuales</h2><ul id="checks-list" class="list"></ul></section></div></div></section>
<section id="view-reports" class="view"><div class="grid g2"><section class="card"><h2>Export y accesos rapidos</h2><p class="note">Enlaces de estado y case generado.</p><div id="results-links" class="links"></div></section><section class="card"><h2>Artefactos detectados</h2><ul id="artifacts-list" class="list"></ul></section></div></section>
</form></main></div>
<script>
(() => {
const form=document.getElementById('job-form'),submitBtn=document.getElementById('btn-submit'),submitLabel=document.getElementById('btn-submit-label'),clearBtn=document.getElementById('btn-clear'),globalStatusEl=document.getElementById('global-status'),statusEl=document.getElementById('status'),resultsLinksEl=document.getElementById('results-links'),detailsEl=document.getElementById('details'),errorBoxEl=document.getElementById('error-box'),summaryListEl=document.getElementById('summary-list'),checksListEl=document.getElementById('checks-list'),artifactsListEl=document.getElementById('artifacts-list'),beamElevationContainer=document.getElementById('beam-elevation-container'),beamElevationLegend=document.getElementById('beam-elevation-legend'),hiddenFramePairsInput=document.getElementById('frame_pairs_json'),hiddenOptimizationInput=document.getElementById('optimization_overrides_json'),hiddenSpanLayoutInput=document.getElementById('span_layout_json'),enableSpanLayout=document.getElementById('enable_span_layout'),spanLayoutFields=document.getElementById('span-layout-fields'),spanLayoutList=document.getElementById('span-layout-list'),addSpanBtn=document.getElementById('btn-add-span'),enableOptimizationOverrides=document.getElementById('enable_optimization_overrides'),optimizationFields=document.getElementById('optimization-fields'),optGenerations=document.getElementById('opt_generations'),optEBars=document.getElementById('opt_e_bars'),optGBars=document.getElementById('opt_g_bars'),optLongBars=document.getElementById('opt_long_bars'),optSpacing=document.getElementById('opt_spacing'),optLongCounts=document.getElementById('opt_long_counts');
const navButtons=Array.from(document.querySelectorAll('[data-view]')),views=Array.from(document.querySelectorAll('.view'));
let currentJobId=null,currentPreviewPayload=null,pollTimer=null,isSubmitting=false;
const parseNum=v=>{const p=Number(v);return Number.isFinite(p)?p:null},clamp=(v,mx,mn)=>Math.max(mx,Math.min(mn,v));const DEFAULT_C_RATIO=0.2,DEFAULT_MIN_BRANCHES_C=4,DEFAULT_MIN_BRANCHES_NC=2;
function parseCsvTokens(raw){return String(raw||'').split(',').map(v=>v.trim()).filter(v=>v.length>0)}
function parsePositiveIntList(raw){const t=parseCsvTokens(raw);if(!t.length)return{ok:false,values:[],message:'La lista no puede estar vacia.'};const values=[];for(const token of t){const p=Number(token);if(!Number.isInteger(p)||p<=0)return{ok:false,values:[],message:`Valor invalido: ${token}. Usa enteros positivos.`};values.push(p)}return{ok:true,values,message:''}}
function headersWithApiKey(){const value=(document.getElementById('api_key').value||'').trim();return value?{'X-API-Key':value}:{}}
function switchView(viewId){views.forEach(v=>v.classList.toggle('active',v.id===viewId));navButtons.forEach(b=>b.classList.toggle('active',b.dataset.view===viewId))}
navButtons.forEach(b=>b.addEventListener('click',()=>switchView(b.dataset.view)));
function setStatus(message,kind){const text=message||'Esperando ejecucion';globalStatusEl.textContent=text;statusEl.textContent=text;globalStatusEl.className='status';statusEl.className='status';if(kind){globalStatusEl.classList.add(kind);statusEl.classList.add(kind)}}
function setSubmitting(submitting){isSubmitting=submitting;submitBtn.disabled=submitting;submitBtn.classList.toggle('loading',submitting);submitLabel.textContent=submitting?'Ejecutando...':'Crear y ejecutar job'}
function stopPolling(){if(pollTimer){clearInterval(pollTimer);pollTimer=null}}
function clearErrorBox(){errorBoxEl.classList.add('hidden');errorBoxEl.innerHTML=''}
function clearFieldErrors(){form.querySelectorAll('[aria-invalid="true"]').forEach(el=>el.removeAttribute('aria-invalid'));form.querySelectorAll('.field-error').forEach(el=>el.remove())}
function ensureFieldVisible(el){if(!el)return;el.scrollIntoView({behavior:'smooth',block:'center'})}
function markElementError(el,msg){if(!el)return;el.setAttribute('aria-invalid','true');const field=el.closest('.field');if(field){const p=document.createElement('p');p.className='field-error';p.textContent=msg;field.appendChild(p)}ensureFieldVisible(el)}
function mapBackendField(field){if(!field)return null;const raw=String(field).toLowerCase();const map=[['sheet_name','sheet_name'],['region_c_ratio','region_c_ratio'],['min_branches','min_branches_c'],['fc_mpa','fc_mpa'],['fy_mpa','fy_mpa'],['width_mm','width_mm'],['height_mm','height_mm'],['d_mm','d_mm'],['db_bar','db_bar'],['cover_side_mm','cover_side_mm'],['cover_top_mm','cover_top_mm'],['cover_bottom_mm','cover_bottom_mm'],['frame_pairs','enable_span_layout'],['span_layout','enable_span_layout'],['optimization','enable_optimization_overrides'],['seismic_excel','seismic_excel'],['gravity_excel','gravity_excel'],['geometry_excel','geometry_excel']];for(const [t,id] of map){if(raw.includes(t))return id}return null}
function normalizeErrorPayload(payload,status){if(!payload||typeof payload!=='object')return{error:'request_error',message:`No fue posible completar la solicitud (HTTP ${status}).`,details:[]};if(Array.isArray(payload.details))return{error:payload.error||'request_error',message:payload.message||'Error de solicitud',details:payload.details};if(Array.isArray(payload.detail))return{error:'validation_error',message:`No fue posible completar la solicitud (HTTP ${status}).`,details:payload.detail.map(it=>({code:it.type||'validation_error',field:Array.isArray(it.loc)?it.loc[it.loc.length-1]:'',message:it.msg||'Entrada invalida',severity:'error'}))};return{error:payload.error||'request_error',message:payload.message||payload.detail||'Error de solicitud',details:[]}}
function renderError(payload){clearErrorBox();clearFieldErrors();const details=Array.isArray(payload?.details)?payload.details:[];const items=[];for(const d of details){const mapped=mapBackendField(d.field||'');if(mapped)markElementError(document.getElementById(mapped),d.message||'Valor no valido');const pref=d.field?`${d.field}: `:'';const suf=d.code?` [${d.code}]`:'';items.push(`<li>${pref}${d.message||'Detalle de validacion'}${suf}</li>`)}const list=items.length?`<ul>${items.join('')}</ul>`:'';errorBoxEl.innerHTML=`<h4>${payload?.message||'Error de solicitud'}</h4><p>Codigo: <strong>${payload?.error||'request_error'}</strong></p>${list}`;errorBoxEl.classList.remove('hidden');setStatus('Se encontraron errores de validacion','err');switchView('view-results')}
function renderUiValidationErrors(errors){clearErrorBox();clearFieldErrors();const items=[];for(const e of errors){if(e.element)markElementError(e.element,e.message);items.push(`<li>${e.label}: ${e.message}</li>`)}errorBoxEl.innerHTML=`<h4>Revisa la configuracion avanzada</h4><p>Codigo: <strong>ui_validation_error</strong></p><ul>${items.join('')}</ul>`;errorBoxEl.classList.remove('hidden');setStatus('Corrige errores de configuracion avanzada','err');switchView('view-results')}
function showStatusPayload(payload){detailsEl.classList.remove('hidden');detailsEl.textContent=JSON.stringify(payload,null,2)}
function renderArtifacts(items){const vals=Array.isArray(items)?items:[];if(!vals.length||!currentJobId){artifactsListEl.innerHTML='<li>No hay artefactos disponibles aun.</li>';return}artifactsListEl.innerHTML=vals.map(v=>`<li><a class="artifact-link" href="/v1/jobs/${currentJobId}/artifacts/${encodeURIComponent(v)}" target="_blank" rel="noreferrer">${v}</a></li>`).join('')}
function setLinks(jobId,payload){const su=payload.status_url||`/v1/jobs/${jobId}`,cu=`/v1/jobs/${jobId}/case`;resultsLinksEl.innerHTML=`<a href="${su}" target="_blank" rel="noreferrer">Ver estado del job</a><a href="${cu}" target="_blank" rel="noreferrer">Ver case generado</a>`}
function setAdvancedControlsEnabled(container,en){container.classList.toggle('adv-disabled',!en);container.querySelectorAll('input,button,select,textarea').forEach(el=>{el.disabled=!en})}
function defaultRegionTemplate(ratioValue){const minC=DEFAULT_MIN_BRANCHES_C,minNC=DEFAULT_MIN_BRANCHES_NC,r=clamp(parseNum(ratioValue)||DEFAULT_C_RATIO,0.05,0.45),mid=1-r;return[{id:'R1',from:0,to:r,type:'C',min_branches:minC,spacing_mm:100},{id:'R2',from:r,to:mid,type:'NC',min_branches:minNC,spacing_mm:200},{id:'R3',from:mid,to:1,type:'C',min_branches:minC,spacing_mm:100}]}
function createRegionRow(initial={}){const row=document.createElement('div');row.className='region-row';row.innerHTML='<div class="field"><label>ID region</label><input type="text" class="region-id" placeholder="R1" /></div><div class="field"><label>Desde (0-1)</label><input type="number" class="region-from" step="0.01" min="0" max="1" placeholder="0.00" /></div><div class="field"><label>Hasta (0-1)</label><input type="number" class="region-to" step="0.01" min="0" max="1" placeholder="0.20" /></div><div class="field"><label>Confinado</label><input type="checkbox" class="region-confined" /></div><div class="field"><label>Min ramas</label><input type="number" class="region-min-branches" min="1" step="1" placeholder="auto" /></div><div class="field"><label>Accion</label><button type="button" class="mini-btn mini-btn-danger region-remove">Eliminar</button></div>';row.querySelector('.region-id').value=initial.id||'';row.querySelector('.region-from').value=Number.isFinite(initial.from)?String(initial.from):'';row.querySelector('.region-to').value=Number.isFinite(initial.to)?String(initial.to):'';row.querySelector('.region-confined').checked=String(initial.type||'NC').toUpperCase()==='C';row.querySelector('.region-min-branches').value=Number.isFinite(initial.min_branches)?String(initial.min_branches):'';row.querySelector('.region-remove').addEventListener('click',()=>{row.remove();currentPreviewPayload=null;refreshPreview()});return row}
function resetSpanRegions(spanRow,ratio){const list=spanRow.querySelector('.region-list');list.innerHTML='';defaultRegionTemplate(ratio).forEach(r=>list.appendChild(createRegionRow(r)))}
function createSpanRow(initial={}){
const row=document.createElement('details');
row.className='span-row';
row.open=true;
row.innerHTML='<summary class="span-summary"><span class="span-summary-title">Vano</span><span class="span-summary-meta"></span></summary><div class="span-body"><div class="span-head"><div class="field"><label>ID vano</label><input type="text" class="span-id" placeholder="S1" /></div><div class="field"><label>Vano sismico</label><input type="text" class="span-seismic" placeholder="190" /></div><div class="field"><label>Vano gravedad</label><input type="text" class="span-gravity" placeholder="190" /></div><div class="field"><label>Apoyo izq (mm)</label><input type="number" class="span-support-left" step="1" min="0" placeholder="0" /></div><div class="field"><label>Apoyo der (mm)</label><input type="number" class="span-support-right" step="1" min="0" placeholder="0" /></div><div class="field"><label>Accion</label><button type="button" class="mini-btn mini-btn-danger span-remove">Eliminar vano</button></div></div><div class="region-box"><div class="region-head"><strong>Regiones del vano</strong><div class="region-actions"><button type="button" class="mini-btn btn-regenerate-regions">Regenerar 3 regiones base</button><button type="button" class="mini-btn btn-add-region">Agregar region</button></div></div><p class="help">Las regiones deben cubrir continuo de 0.0 a 1.0.</p><div class="region-list"></div></div></div>';
const idIn=row.querySelector('.span-id'),sIn=row.querySelector('.span-seismic'),gIn=row.querySelector('.span-gravity'),slIn=row.querySelector('.span-support-left'),srIn=row.querySelector('.span-support-right'),removeBtn=row.querySelector('.span-remove'),addRegionBtn=row.querySelector('.btn-add-region'),regenBtn=row.querySelector('.btn-regenerate-regions'),regionList=row.querySelector('.region-list'),summaryTitle=row.querySelector('.span-summary-title'),summaryMeta=row.querySelector('.span-summary-meta');
idIn.value=initial.id||'';sIn.value=initial.seismic||'';gIn.value=initial.gravity||'';slIn.value=Number.isFinite(initial.support_left_mm)?String(initial.support_left_mm):'';srIn.value=Number.isFinite(initial.support_right_mm)?String(initial.support_right_mm):'';
const updateSummary=()=>{const id=(idIn.value||'').trim()||'sin ID',s=(sIn.value||'').trim()||'?',g=(gIn.value||'').trim()||'?',sl=(slIn.value||'').trim()||'0',sr=(srIn.value||'').trim()||'0';summaryTitle.textContent=`Vano ${id}`;summaryMeta.textContent=`Sismo:${s} | Gravedad:${g} | Ap.izq:${sl} mm | Ap.der:${sr} mm`};
[idIn,sIn,gIn,slIn,srIn].forEach(input=>input.addEventListener('input',updateSummary));
const regions=Array.isArray(initial.regions)&&initial.regions.length?initial.regions:defaultRegionTemplate(DEFAULT_C_RATIO);
regions.forEach(region=>regionList.appendChild(createRegionRow(region)));
updateSummary();
removeBtn.addEventListener('click',()=>{row.remove();currentPreviewPayload=null;refreshPreview()});
addRegionBtn.addEventListener('click',()=>{regionList.appendChild(createRegionRow({}));currentPreviewPayload=null;refreshPreview()});
regenBtn.addEventListener('click',()=>{resetSpanRegions(row,DEFAULT_C_RATIO);currentPreviewPayload=null;refreshPreview()});
return row
}
function syncAdvancedSections(){setAdvancedControlsEnabled(spanLayoutFields,enableSpanLayout.checked);if(enableSpanLayout.checked&&spanLayoutList.children.length===0)spanLayoutList.appendChild(createSpanRow({}));setAdvancedControlsEnabled(optimizationFields,enableOptimizationOverrides.checked)}
function parseRegionRowsStrict(spanRow,spanIndex,errors){const rows=Array.from(spanRow.querySelectorAll('.region-row'));if(!rows.length)return[];const regions=[];rows.forEach((row,index)=>{const idIn=row.querySelector('.region-id'),fromIn=row.querySelector('.region-from'),toIn=row.querySelector('.region-to'),confIn=row.querySelector('.region-confined'),mbIn=row.querySelector('.region-min-branches');const regionId=(idIn.value||'').trim()||`R${index+1}`;const fromV=parseNum(fromIn.value),toV=parseNum(toIn.value);if(fromV===null||toV===null){errors.push({label:`Vano ${spanIndex} - region ${index+1}`,element:fromV===null?fromIn:toIn,message:'Define valores numericos para desde y hasta.'});return}if(fromV<0||toV>1||fromV>=toV){errors.push({label:`Vano ${spanIndex} - region ${index+1}`,element:fromIn,message:'La region debe cumplir 0 <= desde < hasta <= 1.'});return}const mbRaw=(mbIn.value||'').trim();const mb=mbRaw?Number(mbRaw):null;if(mbRaw&&(!Number.isInteger(mb)||mb<1)){errors.push({label:`Vano ${spanIndex} - region ${index+1}`,element:mbIn,message:'Min ramas debe ser entero >= 1.'});return}regions.push({id:regionId,from:fromV,to:toV,type:confIn.checked?'C':'NC',min_branches:mb})});if(errors.length)return[];const ordered=[...regions].sort((a,b)=>a.from-b.from),tol=1e-9;if(!ordered.length||Math.abs(ordered[0].from-0)>tol||Math.abs(ordered[ordered.length-1].to-1)>tol){errors.push({label:`Vano ${spanIndex}`,element:spanRow.querySelector('.region-from'),message:'Las regiones deben iniciar en 0.0 y terminar en 1.0.'});return[]}let cur=0;for(const rg of ordered){if(Math.abs(rg.from-cur)>tol){errors.push({label:`Vano ${spanIndex}`,element:spanRow.querySelector('.region-from'),message:'Las regiones no pueden tener gaps ni solapes.'});return[]}cur=rg.to}return ordered}
function collectSpanLayoutStrict(errors){
const rows=Array.from(spanLayoutList.querySelectorAll('.span-row'));
if(!rows.length){errors.push({label:'Vanos',element:enableSpanLayout,message:'Agrega al menos un vano.'});return[]}
const spans=[];
rows.forEach((row,index)=>{
const idIn=row.querySelector('.span-id'),sIn=row.querySelector('.span-seismic'),gIn=row.querySelector('.span-gravity'),slIn=row.querySelector('.span-support-left'),srIn=row.querySelector('.span-support-right');
const spanId=(idIn.value||'').trim()||`S${index+1}`,s=(sIn.value||'').trim(),g=(gIn.value||'').trim();
if(!s)errors.push({label:`Vano ${index+1}`,element:sIn,message:'Vano sismico es obligatorio.'});
if(!g)errors.push({label:`Vano ${index+1}`,element:gIn,message:'Vano gravedad es obligatorio.'});
const slRaw=(slIn.value||'').trim(),srRaw=(srIn.value||'').trim();
const sl=slRaw?parseNum(slRaw):null,sr=srRaw?parseNum(srRaw):null;
if(!slRaw)errors.push({label:`Vano ${index+1}`,element:slIn,message:'Debes ingresar apoyo izquierdo (mm).'});
if(!srRaw)errors.push({label:`Vano ${index+1}`,element:srIn,message:'Debes ingresar apoyo derecho (mm).'});
if(slRaw&&(sl===null||sl<0))errors.push({label:`Vano ${index+1}`,element:slIn,message:'Apoyo izq debe ser >= 0.'});
if(srRaw&&(sr===null||sr<0))errors.push({label:`Vano ${index+1}`,element:srIn,message:'Apoyo der debe ser >= 0.'});
const regions=parseRegionRowsStrict(row,index+1,errors);
spans.push({id:spanId,seismic:s,gravity:g,support_left_mm:sl,support_right_mm:sr,regions})
});
return spans
}
function collectSpanLayoutPreview(){if(!enableSpanLayout.checked)return[];const rows=Array.from(spanLayoutList.querySelectorAll('.span-row'));if(!rows.length)return[];const minC=DEFAULT_MIN_BRANCHES_C,minNC=DEFAULT_MIN_BRANCHES_NC;return rows.map((row,index)=>{const spanId=(row.querySelector('.span-id').value||'').trim()||`S${index+1}`,s=(row.querySelector('.span-seismic').value||'').trim()||spanId,g=(row.querySelector('.span-gravity').value||'').trim()||s,sl=parseNum(row.querySelector('.span-support-left').value),sr=parseNum(row.querySelector('.span-support-right').value);const regionRows=Array.from(row.querySelectorAll('.region-row')),regions=[];for(let i=0;i<regionRows.length;i++){const rr=regionRows[i],fromV=parseNum(rr.querySelector('.region-from').value),toV=parseNum(rr.querySelector('.region-to').value);if(fromV===null||toV===null||fromV<0||toV>1||fromV>=toV)continue;const type=rr.querySelector('.region-confined').checked?'C':'NC',mbRaw=parseNum(rr.querySelector('.region-min-branches').value);regions.push({id:(rr.querySelector('.region-id').value||'').trim()||`R${i+1}`,from:fromV,to:toV,type,min_branches:Number.isInteger(mbRaw)&&mbRaw>=1?mbRaw:(type==='C'?minC:minNC),spacing_mm:type==='C'?100:200})}const ordered=[...regions].sort((a,b)=>a.from-b.from);let valid=ordered.length>0;if(valid){const tol=1e-9;if(Math.abs(ordered[0].from-0)>tol||Math.abs(ordered[ordered.length-1].to-1)>tol)valid=false;else{let cur=0;for(const rg of ordered){if(Math.abs(rg.from-cur)>tol){valid=false;break}cur=rg.to}}}const effective=valid?ordered:defaultRegionTemplate(DEFAULT_C_RATIO);return{id:spanId,seismic:s,gravity:g,support_left_mm:Number.isFinite(sl)&&sl>=0?sl:0,support_right_mm:Number.isFinite(sr)&&sr>=0?sr:0,regions:effective}})}
function buildAdvancedPayload(){hiddenFramePairsInput.value='';hiddenOptimizationInput.value='';hiddenSpanLayoutInput.value='';const errors=[];if(enableSpanLayout.checked){const spans=collectSpanLayoutStrict(errors);if(!errors.length){hiddenSpanLayoutInput.value=JSON.stringify(spans.map(s=>({id:s.id,seismic:s.seismic,gravity:s.gravity,support_left_mm:s.support_left_mm,support_right_mm:s.support_right_mm,regions:s.regions})));hiddenFramePairsInput.value=JSON.stringify(spans.map(s=>({id:s.id,seismic:s.seismic,gravity:s.gravity})))}}
if(enableOptimizationOverrides.checked){const genRaw=(optGenerations.value||'').trim(),gen=Number(genRaw);if(!genRaw)errors.push({label:'Generaciones',element:optGenerations,message:'Indica la cantidad de generaciones.'});else if(!Number.isInteger(gen)||gen<1)errors.push({label:'Generaciones',element:optGenerations,message:'Debe ser un entero >= 1.'});const eb=parseCsvTokens(optEBars.value),gb=parseCsvTokens(optGBars.value),lb=parseCsvTokens(optLongBars.value);if(!eb.length)errors.push({label:'Estribos cerrados',element:optEBars,message:'Define al menos un diametro.'});if(!gb.length)errors.push({label:'Ramas simples',element:optGBars,message:'Define al menos un diametro.'});if(!lb.length)errors.push({label:'Refuerzo longitudinal',element:optLongBars,message:'Define al menos un diametro.'});const sp=parsePositiveIntList(optSpacing.value),lc=parsePositiveIntList(optLongCounts.value);if(!sp.ok)errors.push({label:'Espaciamientos',element:optSpacing,message:sp.message});if(!lc.ok)errors.push({label:'Cantidades longitudinales',element:optLongCounts,message:lc.message});if(!errors.length)hiddenOptimizationInput.value=JSON.stringify({variables:{E_bars:eb,G_bars:gb,stirrup_spacing_mm:sp.values,longitudinal_bars:lb,longitudinal_bar_counts:lc.values},genetic_algorithm:{generations:gen}})}
if(errors.length){renderUiValidationErrors(errors);return false}return true}
const defaultSpacing=t=>String(t||'').toUpperCase()==='C'?100:200;
function fallbackRegionLabels(region,dbBar){const minB=Number(region.min_branches)||(region.type==='C'?4:2),gCount=Math.max(minB-2,0),spacing=Number(region.spacing_mm)||defaultSpacing(region.type),gText=gCount>0?` + ${gCount}G #3`:'';return{transverse:`1E #3${gText} @ ${Math.round(spacing)} mm`,longitudinal:`4${dbBar}`}}
function collectFallback(){const defaultRatio=DEFAULT_C_RATIO,dbBar=(document.getElementById('db_bar').value||'#6').trim()||'#6',layout=collectSpanLayoutPreview(),spans=[];if(layout.length){layout.forEach((span,i)=>{const regions=(span.regions||[]).map((region,j)=>{const lengthMm=Math.max(1,Math.round(6000*(region.to-region.from))),labels=fallbackRegionLabels(region,dbBar);return{region_id:region.id||`R${j+1}`,type:String(region.type||'NC').toUpperCase(),from:region.from,to:region.to,length_mm:lengthMm,length_estimated:true,spacing_mm:Number(region.spacing_mm)||defaultSpacing(region.type),spacing_estimated:true,transverse_label:labels.transverse,longitudinal_label:labels.longitudinal}});const spanLength=regions.reduce((a,r)=>a+(Number(r.length_mm)||0),0)||6000;spans.push({span_id:span.id||`S${i+1}`,seismic:span.seismic,gravity:span.gravity,support_left_mm:Math.max(0,Math.round(Number(span.support_left_mm)||0)),support_right_mm:Math.max(0,Math.round(Number(span.support_right_mm)||0)),length_mm:spanLength,length_estimated:true,regions})})}
if(!spans.length){const base=defaultRegionTemplate(defaultRatio).map(region=>{const labels=fallbackRegionLabels(region,dbBar);return{region_id:region.id,type:region.type,from:region.from,to:region.to,length_mm:Math.max(1,Math.round(6000*(region.to-region.from))),length_estimated:true,spacing_mm:region.spacing_mm,spacing_estimated:true,transverse_label:labels.transverse,longitudinal_label:labels.longitudinal}});spans.push({span_id:'S1',seismic:'S1',gravity:'S1',support_left_mm:0,support_right_mm:0,length_mm:6000,length_estimated:true,regions:base})}
const totalSpanMm=spans.reduce((a,s)=>a+(Number(s.length_mm)||0),0),totalSupportMm=spans.reduce((a,s)=>a+(Number(s.support_right_mm)||0),0);return{totalSpanMm,totalSupportMm,totalSystemMm:totalSpanMm+totalSupportMm,totalSpanEstimated:true,beamDepthMm:parseNum(document.getElementById('height_mm').value)||600,beamWidthMm:parseNum(document.getElementById('width_mm').value)||300,beamId:(document.getElementById('beam_id').value||'B1').trim()||'B1',detailing:(document.getElementById('detailing').value||'DMO').trim()||'DMO',fcMpa:parseNum(document.getElementById('fc_mpa').value)||28,fyMpa:parseNum(document.getElementById('fy_mpa').value)||420,spans,dataSource:'fallback'}}
function buildBeamData(source){const fb=collectFallback(),pp=source&&source.previewPayload;if(!pp||!Array.isArray(pp.spans)||!pp.spans.length)return fb;const beam=pp.beam||{},spans=pp.spans.map((sp,i)=>({span_id:sp.span_id||`S${i+1}`,seismic:sp.seismic||'',gravity:sp.gravity||'',support_left_mm:parseNum(sp.support_left_mm)||0,support_right_mm:parseNum(sp.support_right_mm)||0,length_mm:parseNum(sp.length_mm)||6000,length_estimated:!!sp.length_estimated,regions:Array.isArray(sp.regions)?sp.regions.map((rg,j)=>({region_id:rg.region_id||`R${j+1}`,type:String(rg.type||'NC').toUpperCase(),from:parseNum(rg.from),to:parseNum(rg.to),length_mm:parseNum(rg.length_mm)||1,length_estimated:!!rg.length_estimated,spacing_mm:parseNum(rg.spacing_mm)||defaultSpacing(rg.type),spacing_estimated:!!rg.spacing_estimated,transverse_label:rg.transverse_label||`${String(rg.type||'NC').toUpperCase()} @ ${parseNum(rg.spacing_mm)||defaultSpacing(rg.type)} mm`,longitudinal_label:rg.longitudinal_label||'long. n/d'})):[]}));const total=spans.reduce((a,s)=>a+(parseNum(s.length_mm)||0),0),supp=spans.reduce((a,s)=>a+(parseNum(s.support_right_mm)||0),0);return{totalSpanMm:parseNum(pp.total_span_mm)||total||fb.totalSpanMm,totalSupportMm:parseNum(pp.total_support_mm)||supp,totalSystemMm:parseNum(pp.total_system_mm)||((parseNum(pp.total_span_mm)||total||fb.totalSpanMm)+(parseNum(pp.total_support_mm)||supp)),totalSpanEstimated:!!pp.total_span_estimated,beamDepthMm:parseNum(beam.height_mm)||fb.beamDepthMm,beamWidthMm:parseNum(beam.width_mm)||fb.beamWidthMm,beamId:beam.beam_id||fb.beamId,detailing:beam.detailing||fb.detailing,fcMpa:parseNum(beam.fc_mpa)||fb.fcMpa,fyMpa:parseNum(beam.fy_mpa)||fb.fyMpa,spans,dataSource:'preview'}}
function buildBeamElevationSvg(d){
const W=1520,H=500,startX=70,topY=150,beamH=92,bottomY=topY+beamH,drawW=W-2*startX;
const spans=Array.isArray(d.spans)&&d.spans.length?d.spans:[];
const totalSpanFromData=Math.max(Number(d.totalSpanMm)||0,0);
const totalSpanFromSpans=spans.reduce((acc,sp)=>acc+Math.max(Number(sp.length_mm)||0,0),0);
const totalSpan=Math.max(totalSpanFromData||totalSpanFromSpans||6000,1);
const firstSupportLeftMm=spans.length?Math.max(Number(spans[0].support_left_mm)||0,0):0;
const supportRightMmSum=spans.reduce((acc,sp)=>acc+Math.max(Number(sp.support_right_mm)||0,0),0);
const totalSupport=Math.max(Number(d.totalSupportMm)||0,supportRightMmSum+firstSupportLeftMm);
const totalSystem=Math.max(Number(d.totalSystemMm)||0,totalSpan+totalSupport,1);

let cursor=startX,zoneRects='',zoneLines='',stirrups='',labels='',spanMarkers='',spanLabels='',spanCotas='',supportBands='',supportCotas='';
let zoneCounter=1;

const firstSupportW=firstSupportLeftMm>0?Math.max((firstSupportLeftMm/totalSystem)*drawW,7):0;
if(firstSupportW>0){
const firstSupportText=`${Math.round(firstSupportLeftMm)} mm`;
supportBands+=`<rect x="${startX.toFixed(2)}" y="${topY}" width="${firstSupportW.toFixed(2)}" height="${beamH}" fill="rgba(68,82,101,0.46)" stroke="#34485d" stroke-width="1.2" />`;
supportCotas+=`<line x1="${startX.toFixed(2)}" y1="${topY}" x2="${startX.toFixed(2)}" y2="122" stroke="#6c737d" stroke-width="0.95" /><line x1="${(startX+firstSupportW).toFixed(2)}" y1="${topY}" x2="${(startX+firstSupportW).toFixed(2)}" y2="122" stroke="#6c737d" stroke-width="0.95" /><line x1="${startX.toFixed(2)}" y1="122" x2="${(startX+firstSupportW).toFixed(2)}" y2="122" stroke="#4e545c" stroke-width="1.05" stroke-dasharray="4 2" marker-start="url(#arrow-support)" marker-end="url(#arrow-support)" /><text x="${(startX+firstSupportW/2).toFixed(2)}" y="112" text-anchor="middle" font-size="10.5" fill="#3b4047" font-weight="620">${firstSupportText}</text>`;
cursor=startX+firstSupportW;
}

spans.forEach((sp,si)=>{
const spanLen=Math.max(Number(sp.length_mm)||1,1);
const spanW=(spanLen/totalSystem)*drawW;
const spanStart=cursor,spanEnd=spanStart+spanW;

zoneRects+=`<rect x="${spanStart.toFixed(2)}" y="${topY}" width="${Math.max(spanW,2).toFixed(2)}" height="${beamH}" fill="rgba(24,71,113,0.06)" />`;
spanMarkers+=`<line x1="${spanStart.toFixed(2)}" y1="${topY}" x2="${spanStart.toFixed(2)}" y2="${bottomY}" stroke="#254b70" stroke-width="${si===0?'1.4':'1.8'}" stroke-dasharray="${si===0?'0':'5 4'}" />`;

const spanId=sp.span_id||`S${si+1}`;
const showSpanId=spanW>=42;
const spanIdFont=spanW<70?'10':'12';
if(showSpanId){
spanLabels+=`<text x="${(spanStart+spanW/2).toFixed(2)}" y="104" text-anchor="middle" font-size="${spanIdFont}" fill="#1b3552" font-weight="620">${spanId}</text>`;
}

const spanLenText=`${Math.round(spanLen)} mm${sp.length_estimated?' est.':''}`;
const spanCotaY=136;
const spanTextY=129;
const spanFont=spanW<95?9.2:10.6;
const showSpanText=spanW>=52;
const spanTextSvg=showSpanText?`<text x="${(spanStart+spanW/2).toFixed(2)}" y="${spanTextY}" text-anchor="middle" font-size="${spanFont.toFixed(1)}" fill="#1f3854" font-weight="620">${spanLenText}</text>`:'';
spanCotas+=`<line x1="${spanStart.toFixed(2)}" y1="${topY}" x2="${spanStart.toFixed(2)}" y2="${spanCotaY}" stroke="#3b6b94" stroke-width="0.95" /><line x1="${spanEnd.toFixed(2)}" y1="${topY}" x2="${spanEnd.toFixed(2)}" y2="${spanCotaY}" stroke="#3b6b94" stroke-width="0.95" /><line x1="${spanStart.toFixed(2)}" y1="${spanCotaY}" x2="${spanEnd.toFixed(2)}" y2="${spanCotaY}" stroke="#1e5a8a" stroke-width="1.1" marker-start="url(#arrow-span)" marker-end="url(#arrow-span)" />${spanTextSvg}`;

let regionCursor=spanStart;
const regions=Array.isArray(sp.regions)?sp.regions:[];
regions.forEach((rg,ri)=>{
const regionLen=Math.max(Number(rg.length_mm)||1,1),regionW=(regionLen/spanLen)*spanW,regionStart=regionCursor,regionEnd=regionStart+regionW,fill=(zoneCounter+ri)%2===0?'rgba(33,88,134,0.09)':'rgba(18,64,105,0.14)';
zoneRects+=`<rect x="${regionStart.toFixed(2)}" y="${topY}" width="${Math.max(regionW,2).toFixed(2)}" height="${beamH}" fill="${fill}" />`;
zoneLines+=`<line x1="${regionStart.toFixed(2)}" y1="${topY}" x2="${regionStart.toFixed(2)}" y2="${bottomY}" stroke="#28567f" stroke-width="1.1" stroke-dasharray="4 3" />`;
const spacing=Math.max(Number(rg.spacing_mm)||defaultSpacing(rg.type),1),step=clamp((spacing/totalSystem)*drawW,8,54);
for(let x=regionStart+5;x<regionEnd-5;x+=step){stirrups+=`<path d="M ${x.toFixed(2)} ${topY+6} L ${x.toFixed(2)} ${bottomY-6}" stroke="#2f4f6f" stroke-width="1.05" fill="none" />`}
const center=regionStart+regionW/2,line1=`Zona ${zoneCounter} (L=${Math.round(regionLen)} mm${rg.length_estimated?' est.':''})`,line2=`${rg.transverse_label||`@${Math.round(spacing)} mm`}`,line3=`${rg.longitudinal_label||'long. n/d'}`;
labels+=`<text x="${center.toFixed(2)}" y="286" text-anchor="middle" font-size="11" fill="#1a2f47" font-weight="620"><tspan x="${center.toFixed(2)}" dy="0">${line1}</tspan><tspan x="${center.toFixed(2)}" dy="14">${line2}</tspan><tspan x="${center.toFixed(2)}" dy="14">${line3}</tspan></text>`;
zoneCounter+=1;
regionCursor=regionEnd;
});

zoneLines+=`<line x1="${spanEnd.toFixed(2)}" y1="${topY}" x2="${spanEnd.toFixed(2)}" y2="${bottomY}" stroke="#28567f" stroke-width="1.1" stroke-dasharray="4 3" />`;

const supportR=Math.max(Number(sp.support_right_mm)||0,0);
if(supportR>0){
const supportW=Math.max((supportR/totalSystem)*drawW,7),supportX=spanEnd,supportCenter=supportX+supportW/2,supportText=`${Math.round(supportR)} mm`;
supportBands+=`<rect x="${supportX.toFixed(2)}" y="${topY}" width="${supportW.toFixed(2)}" height="${beamH}" fill="rgba(68,82,101,0.46)" stroke="#34485d" stroke-width="1.2" />`;
supportCotas+=`<line x1="${supportX.toFixed(2)}" y1="${topY}" x2="${supportX.toFixed(2)}" y2="122" stroke="#6c737d" stroke-width="0.95" /><line x1="${(supportX+supportW).toFixed(2)}" y1="${topY}" x2="${(supportX+supportW).toFixed(2)}" y2="122" stroke="#6c737d" stroke-width="0.95" /><line x1="${supportX.toFixed(2)}" y1="122" x2="${(supportX+supportW).toFixed(2)}" y2="122" stroke="#4e545c" stroke-width="1.05" stroke-dasharray="4 2" marker-start="url(#arrow-support)" marker-end="url(#arrow-support)" /><text x="${supportCenter.toFixed(2)}" y="112" text-anchor="middle" font-size="10.5" fill="#3b4047" font-weight="620">${supportText}</text>`;
cursor=supportX+supportW;
}else{
cursor=spanEnd;
}
});

const endX=cursor,totalText=`${Math.round(totalSystem)} mm${d.totalSpanEstimated?' (estimado)':''}`;
return `<svg id="beam-elevation" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Vista en alzado de la viga"><defs><marker id="arrow-total" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#1e334a" /></marker><marker id="arrow-span" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#1e5a8a" /></marker><marker id="arrow-support" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#4e545c" /></marker></defs><rect x="12" y="12" width="${W-24}" height="${H-24}" rx="8" fill="#f8fbff" stroke="#d0dcea" /><line x1="${startX}" y1="80" x2="${endX.toFixed(2)}" y2="80" stroke="#1e334a" stroke-width="1.4" marker-start="url(#arrow-total)" marker-end="url(#arrow-total)" /><text x="${((startX+endX)/2).toFixed(2)}" y="64" text-anchor="middle" font-size="16" fill="#16304a" font-weight="700">Longitud total sistema: ${totalText}</text><line x1="${startX-36}" y1="${topY}" x2="${startX-36}" y2="${bottomY}" stroke="#1e334a" stroke-width="1.2" marker-start="url(#arrow-total)" marker-end="url(#arrow-total)" /><text x="${startX-48}" y="${topY+beamH/2}" transform="rotate(-90 ${startX-48} ${topY+beamH/2})" text-anchor="middle" font-size="13" fill="#183753" font-weight="620">h = ${Math.round(d.beamDepthMm||600)} mm</text>${zoneRects}${supportBands}<rect x="${startX}" y="${topY}" width="${Math.max(endX-startX,2).toFixed(2)}" height="${beamH}" fill="none" stroke="#2b4f73" stroke-width="2.1" rx="4" />${spanMarkers}${zoneLines}${stirrups}${spanLabels}${spanCotas}${supportCotas}${labels}<line x1="${startX}" y1="${bottomY+2}" x2="${endX.toFixed(2)}" y2="${bottomY+2}" stroke="#3f5f7f" stroke-width="1.1" /></svg>`;
}
function renderBeam(container,data){container.innerHTML=buildBeamElevationSvg(data);beamElevationLegend.textContent=data.dataSource==='preview'?'Dibujo alimentado por datos reales de job/optimizacion.':'Se usan datos de fallback (estimados) hasta obtener preview del job.'}
function renderSummary(data,st){summaryListEl.innerHTML=[`<li><strong>Viga:</strong> ${data.beamId} | Detallado ${data.detailing}</li>`,`<li><strong>Material:</strong> f'c ${Math.round(data.fcMpa)} MPa | fy ${Math.round(data.fyMpa)} MPa</li>`,`<li><strong>Seccion:</strong> b=${Math.round(data.beamWidthMm)} mm | h=${Math.round(data.beamDepthMm)} mm</li>`,`<li><strong>Vanos:</strong> ${Array.isArray(data.spans)?data.spans.length:0}</li>`,`<li><strong>Longitud neta vanos:</strong> ${Math.round(data.totalSpanMm)} mm${data.totalSpanEstimated?' (estimado)':''}</li>`,`<li><strong>Longitud apoyos:</strong> ${Math.round(data.totalSupportMm||0)} mm</li>`,`<li><strong>Longitud total sistema:</strong> ${Math.round(data.totalSystemMm||data.totalSpanMm)} mm</li>`,`<li><strong>Estado job:</strong> ${(st&&st.status)||'sin job'}</li>`].join('')}
function renderChecks(st){const rows=[],s=st&&st.status?st.status:'idle';if(s==='completed')rows.push({c:'ok',m:'Job completado correctamente.'});else if(s==='failed')rows.push({c:'err',m:'Job finalizo en estado failed.'});else if(s==='running'||s==='queued')rows.push({c:'warn',m:`Job en progreso: ${s}.`});else rows.push({c:'warn',m:'Aun no se ha ejecutado un job en esta sesion.'});rows.push({c:'ok',m:'Contratos API preservados (/v1/jobs*).'});rows.push({c:'ok',m:'Preview SVG soporta vanos multiples, apoyos y regiones por vano.'});checksListEl.innerHTML=rows.map(r=>`<li class="${r.c}">${r.m}</li>`).join('')}
async function refreshPreviewFromJob(jobId,statusPayload){let preview=null;try{const r=await fetch(`/v1/jobs/${jobId}/preview`,{headers:headersWithApiKey()});if(r.ok){preview=await r.json();currentPreviewPayload=preview}}catch(e){preview=null}const data=buildBeamData({previewPayload:preview});renderBeam(beamElevationContainer,data);renderSummary(data,statusPayload);renderChecks(statusPayload)}
function refreshPreview(statusPayload=null){const data=buildBeamData({previewPayload:currentPreviewPayload});renderBeam(beamElevationContainer,data);renderSummary(data,statusPayload);renderChecks(statusPayload)}
async function refreshStatus(jobId){const response=await fetch(`/v1/jobs/${jobId}`,{headers:headersWithApiKey()}),payload=await response.json().catch(()=>({}));if(!response.ok){renderError(normalizeErrorPayload(payload,response.status));stopPolling();setSubmitting(false);return}showStatusPayload(payload);renderArtifacts(payload.artifacts);refreshPreview(payload);if(payload.status==='completed'){setStatus('Job completado. Puedes descargar resultados.','ok');await refreshPreviewFromJob(jobId,payload);stopPolling();setSubmitting(false);switchView('view-results');return}if(payload.status==='failed'){renderError({error:'job_failed',message:`El job termino en estado failed${payload.error?`: ${payload.error}`:''}`,details:[]});stopPolling();setSubmitting(false);return}setStatus(`Job en progreso: ${payload.status}`,'running')}
addSpanBtn.addEventListener('click',()=>{spanLayoutList.appendChild(createSpanRow({}));currentPreviewPayload=null;refreshPreview()});enableSpanLayout.addEventListener('change',()=>{syncAdvancedSections();currentPreviewPayload=null;refreshPreview()});enableOptimizationOverrides.addEventListener('change',syncAdvancedSections);spanLayoutList.addEventListener('input',()=>{currentPreviewPayload=null;refreshPreview()});spanLayoutList.addEventListener('change',()=>{currentPreviewPayload=null;refreshPreview()});['beam_id','detailing','fc_mpa','fy_mpa','width_mm','height_mm','db_bar'].forEach(id=>{const el=document.getElementById(id);if(el)el.addEventListener('input',()=>{currentPreviewPayload=null;refreshPreview()})});syncAdvancedSections();
form.addEventListener('submit',async(event)=>{event.preventDefault();if(isSubmitting)return;stopPolling();clearErrorBox();clearFieldErrors();detailsEl.classList.add('hidden');detailsEl.textContent='';setSubmitting(true);setStatus('Validando datos y creando job...','running');switchView('view-results');if(!buildAdvancedPayload()){setSubmitting(false);return}const formData=new FormData(form);if(!formData.get('frame_pairs_json'))formData.delete('frame_pairs_json');if(!formData.get('optimization_overrides_json'))formData.delete('optimization_overrides_json');if(!formData.get('span_layout_json'))formData.delete('span_layout_json');try{const response=await fetch('/v1/jobs/from-form',{method:'POST',body:formData,headers:headersWithApiKey()}),payload=await response.json().catch(()=>({}));if(!response.ok){renderError(normalizeErrorPayload(payload,response.status));setSubmitting(false);return}currentJobId=payload.job_id;currentPreviewPayload=null;setLinks(currentJobId,payload);renderArtifacts([]);setStatus(`Job ${currentJobId} creado. Iniciando monitoreo...`,'running');await refreshStatus(currentJobId);if(!pollTimer&&isSubmitting){pollTimer=setInterval(()=>{refreshStatus(currentJobId).catch((error)=>{renderError({error:'network_error',message:error?.message||'No fue posible consultar el estado del job',details:[]});stopPolling();setSubmitting(false)})},2500)}}catch(error){renderError({error:'network_error',message:error?.message||'No fue posible enviar la solicitud',details:[]});setSubmitting(false)}});
clearBtn.addEventListener('click',()=>{stopPolling();currentJobId=null;currentPreviewPayload=null;setSubmitting(false);setStatus('Esperando ejecucion');resultsLinksEl.innerHTML='';detailsEl.textContent='';detailsEl.classList.add('hidden');clearErrorBox();clearFieldErrors();renderArtifacts([]);refreshPreview()});
renderArtifacts([]);refreshPreview();
})();
</script>
</body>
</html>
"""


@router.get('/ui', response_class=HTMLResponse)
def ui_page() -> HTMLResponse:
    return HTMLResponse(content=UI_HTML)






