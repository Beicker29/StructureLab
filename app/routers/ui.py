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
    :root{--bg:#eef3f9;--surface:#fff;--line:#c9d6e5;--text:#13243a;--muted:#5a6f8a;--brand:#10324f;--brand2:#0c2740;--accent:#0f5f79;--accent2:#0b4d62;--ok:#1f6b43;--warn:#8c5a00;--err:#a12821}
    *{box-sizing:border-box} html,body{height:100%}
    body{margin:0;background:linear-gradient(160deg,#e8eff8 0%,var(--bg) 56%,#f6f9fd 100%);color:var(--text);font-family:"IBM Plex Sans","Segoe UI",Tahoma,sans-serif}
    .app{min-height:100vh;display:grid;grid-template-columns:250px minmax(0,1fr)}
    .sidebar{background:linear-gradient(180deg,var(--brand),var(--brand2));color:#dbe6f2;padding:14px;border-right:1px solid #244564;position:sticky;top:0;height:100vh;display:flex;flex-direction:column;gap:12px}
    .brand{border:1px solid rgba(136,167,196,.26);background:rgba(11,28,45,.35);border-radius:12px;padding:11px}
    .brand h2{margin:0;font-size:1.08rem;color:#f4f9ff} .brand p{margin:4px 0 0;font-size:.76rem;color:#9eb5cb}
    .nav{display:grid;gap:7px}
    .nav button{appearance:none;border:1px solid transparent;background:transparent;color:#d0deec;text-align:left;border-radius:9px;padding:9px 10px;font-size:.88rem;font-weight:620;cursor:pointer}
    .nav button:hover{background:rgba(120,152,183,.18);border-color:rgba(155,184,211,.24);color:#f4f8fc}
    .nav button.active{background:linear-gradient(180deg,#385474,#2a4768);border-color:#4f6884;color:#fff}
    .side-foot{margin-top:auto;border-top:1px solid rgba(132,162,190,.2);padding-top:10px;font-size:.75rem;color:#9fb3c9}
    .main{padding:14px}
    .top{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:13px 15px;display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
    .top h1{margin:0;font-size:1.22rem} .top p{margin:5px 0 0;color:var(--muted);font-size:.84rem;max-width:760px}
    .status{display:inline-flex;align-items:center;min-height:34px;border-radius:999px;border:1px solid #bfd0e4;background:#edf4fb;color:#2a3e56;font-size:.83rem;font-weight:640;padding:7px 12px}
    .status.running{border-color:#dcc28f;background:#fff8e9;color:var(--warn)} .status.ok{border-color:#afd4c1;background:#ecf8f1;color:var(--ok)} .status.err{border-color:#e3b0ab;background:#fff1f0;color:var(--err)}
    .view{display:none;margin-top:12px;gap:12px} .view.active{display:grid}
    .card{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:13px}
    .card h2{margin:0 0 6px;font-size:1rem} .note{margin:0 0 10px;color:var(--muted);font-size:.8rem}
    .grid{display:grid;gap:10px} .g2{grid-template-columns:repeat(2,minmax(0,1fr))} .g3{grid-template-columns:repeat(3,minmax(0,1fr))}
    .field label{display:block;margin-bottom:4px;font-size:.82rem;font-weight:630}
    .field input,.field select{width:100%;border:1px solid #bfccde;border-radius:8px;padding:9px 10px;font-size:.9rem;background:#fff}
    .field input:focus,.field select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(15,95,121,.14)}
    .field [aria-invalid="true"]{border-color:var(--err);background:#fff8f8}
    .help{margin:5px 0 0;color:var(--muted);font-size:.75rem} .field-error{margin:5px 0 0;color:var(--err);font-size:.78rem}
    .advanced{border:1px solid #d5e1ef;border-radius:10px;background:#f7fbff} .advanced>summary{list-style:none;cursor:pointer;padding:10px 11px;font-size:.86rem;font-weight:640;color:#1d3c5d} .advanced>summary::-webkit-details-marker{display:none} .advanced[open]>summary{border-bottom:1px solid #d5e1ef}
    .adv-body{padding:10px} .adv-block{border:1px solid #d5e1ee;border-radius:10px;padding:10px;background:#fff} .adv-block+.adv-block{margin-top:10px}
    .toggle{display:flex;align-items:center;gap:8px;margin-bottom:6px} .toggle input{width:16px;height:16px}
    .adv-disabled{opacity:.62} .pairs{display:grid;gap:8px;margin-bottom:8px} .pair-row{display:grid;gap:8px;grid-template-columns:1fr 1fr 1fr auto;align-items:end}
    .mini-btn{border:1px solid #c9d7e8;border-radius:8px;padding:7px 10px;background:#edf3fb;color:#17314f;font-size:.8rem;font-weight:620;cursor:pointer} .mini-btn-danger{border-color:#e3b7b3;background:#fff2f1;color:#8f2b25}
    .actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
    .btn{min-width:190px;border-radius:10px;border:1px solid transparent;padding:10px 13px;cursor:pointer;font-size:.9rem;font-weight:650;display:inline-flex;align-items:center;justify-content:center;gap:7px}
    .btn-primary{color:#fff;background:linear-gradient(180deg,var(--accent),var(--accent2))} .btn-secondary{color:#1f3248;border-color:#c5d2e4;background:#e8edf6} .btn:disabled{opacity:.72;cursor:not-allowed}
    .spinner{width:12px;height:12px;border-radius:50%;border:2px solid rgba(255,255,255,.42);border-top-color:#fff;animation:spin .8s linear infinite;display:none}.btn.loading .spinner{display:inline-block}@keyframes spin{to{transform:rotate(360deg)}}
    .results{display:grid;gap:12px;grid-template-columns:minmax(0,1fr) 320px}
    .svg-wrap{border:1px solid #d1deec;border-radius:10px;background:#f5f9ff;overflow:auto;min-height:330px;padding:8px}
    .legend{margin-top:8px;color:var(--muted);font-size:.76rem}
    .list{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:6px;font-size:.82rem}
    .list li{border:1px solid #d8e3ef;background:#fafcff;border-radius:8px;padding:7px 8px}
    .list li.ok{border-color:#badcc9;background:#edf8f2}.list li.warn{border-color:#e6d2aa;background:#fff8ea}.list li.err{border-color:#e7b8b4;background:#fff3f2}
    .alert{margin-top:10px;border:1px solid #e4b5b1;background:#fdeceb;border-radius:9px;color:#5f1d1b;padding:9px 10px}.alert h4{margin:0;font-size:.86rem}.alert p{margin:4px 0 0;font-size:.76rem}.alert ul{margin:7px 0 0;padding-left:18px;font-size:.8rem}
    .links{margin-top:9px;display:grid;gap:6px}.links a{color:var(--accent);text-decoration:none;font-size:.83rem;font-weight:620}.links a:hover{text-decoration:underline}
    .log{margin-top:8px;border:1px dashed #bfcedf;border-radius:9px;padding:9px;background:#f8fbff;max-height:320px;overflow:auto;font-size:.77rem;font-family:"IBM Plex Mono","Consolas",monospace;white-space:pre-wrap}
    .hidden{display:none}
    @media (max-width:1140px){.results{grid-template-columns:1fr}} @media (max-width:980px){.app{grid-template-columns:1fr}.sidebar{position:static;height:auto;border-right:none;border-bottom:1px solid #294662}.nav{grid-template-columns:repeat(4,minmax(0,1fr))}.nav button{text-align:center;padding:9px 7px}}
    @media (max-width:820px){.g3{grid-template-columns:repeat(2,minmax(0,1fr))}.pair-row{grid-template-columns:1fr 1fr}} @media (max-width:620px){.g3,.g2{grid-template-columns:1fr}.pair-row{grid-template-columns:1fr}.btn{width:100%}.nav{grid-template-columns:repeat(2,minmax(0,1fr))}.top{flex-direction:column;align-items:flex-start}}
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand"><h2>ShearTors RC</h2><p>FastAPI engineering dashboard</p></div>
      <nav id="sidebar-nav" class="nav" aria-label="Navegacion principal">
        <button type="button" class="active" data-view="view-design">Design</button>
        <button type="button" data-view="view-import">ETABS Import</button>
        <button type="button" data-view="view-results">Results</button>
        <button type="button" data-view="view-reports">Reports</button>
      </nav>
      <p class="side-foot">Deploy target: Render</p>
    </aside>

    <main class="main">
      <header class="top">
        <div><h1>RC Beam Shear-Torsion Workflow</h1><p>Completa parametros de diseno, carga ETABS y monitorea resultados con preview SVG tecnico.</p></div>
        <span id="global-status" class="status">Esperando ejecucion</span>
      </header>

      <form id="job-form" novalidate>
        <section id="view-design" class="view active">
          <div class="grid g2">
            <section class="card">
              <h2>Informacion general</h2><p class="note">Parametros base del caso y configuracion de diseno.</p>
              <div class="grid g3">
                <div class="field"><label for="api_key">API Key (opcional)</label><input id="api_key" name="api_key" autocomplete="off" placeholder="Solo si APP_API_KEY esta activa" /></div>
                <div class="field"><label for="case_name">Nombre del caso</label><input id="case_name" name="case_name" value="case_web" /></div>
                <div class="field"><label for="beam_id">Beam ID</label><input id="beam_id" name="beam_id" value="B1" /></div>
                <div class="field"><label for="sheet_name">Hoja ETABS</label><input id="sheet_name" name="sheet_name" value="Conc Bm Sum - ACI 318-08" /><p class="help">Debe coincidir exactamente en ambos Excel.</p></div>
                <div class="field"><label for="detailing">Detailing</label><select id="detailing" name="detailing"><option value="DMO" selected>DMO</option><option value="DES">DES</option></select></div>
                <div class="field"><label for="units_rebar_per_length">Unidad VRebar/TTrnRebar</label><select id="units_rebar_per_length" name="units_rebar_per_length"><option value="mm2/m" selected>mm2/m</option><option value="cm2/m">cm2/m</option></select></div>
              </div>
            </section>
            <section class="card">
              <h2>Materiales y geometria</h2><p class="note">Propiedades y dimensiones principales de la viga.</p>
              <div class="grid g2">
                <div class="field"><label for="fc_mpa">f'c (MPa)</label><input id="fc_mpa" name="fc_mpa" type="number" value="28" step="0.1" /></div>
                <div class="field"><label for="fy_mpa">fy (MPa)</label><input id="fy_mpa" name="fy_mpa" type="number" value="420" step="0.1" /></div>
                <div class="field"><label for="width_mm">Ancho de viga (mm)</label><input id="width_mm" name="width_mm" type="number" value="300" step="0.1" /></div>
                <div class="field"><label for="height_mm">Altura de viga (mm)</label><input id="height_mm" name="height_mm" type="number" value="600" step="0.1" /></div>
                <div class="field"><label for="d_mm">Peralte efectivo d (mm)</label><input id="d_mm" name="d_mm" type="number" value="600" step="0.1" /></div>
                <div class="field"><label for="db_bar">Barra longitudinal de referencia (db_bar)</label><select id="db_bar" name="db_bar"><option>#3</option><option>#4</option><option>#5</option><option selected>#6</option><option>#7</option><option>#8</option></select></div>
                <div class="field"><label for="cover_side_mm">Recubrimiento lateral (mm)</label><input id="cover_side_mm" name="cover_side_mm" type="number" value="40" step="0.1" /></div>
                <div class="field"><label for="cover_top_mm">Recubrimiento superior (mm)</label><input id="cover_top_mm" name="cover_top_mm" type="number" value="40" step="0.1" /></div>
                <div class="field"><label for="cover_bottom_mm">Recubrimiento inferior (mm)</label><input id="cover_bottom_mm" name="cover_bottom_mm" type="number" value="40" step="0.1" /></div>
              </div>
            </section>
          </div>

          <section class="card">
            <h2>Refuerzo base y configuracion avanzada</h2><p class="note">Reglas de armado por region y ajustes opcionales de optimizacion.</p>
            <div class="grid g3">
              <div class="field"><label for="min_branches_c">Minimo ramas en region C</label><input id="min_branches_c" name="min_branches_c" type="number" value="4" step="1" min="1" /><p class="help">Si TTrnRebar > 0 usa minimo 2 ramas.</p></div>
              <div class="field"><label for="min_branches_nc">Minimo ramas en region NC</label><input id="min_branches_nc" name="min_branches_nc" type="number" value="2" step="1" min="1" /><p class="help">Con TTrnRebar > 0, una sola rama no es valida.</p></div>
              <div class="field"><label for="region_c_ratio">Fraccion C en extremos</label><input id="region_c_ratio" name="region_c_ratio" type="number" value="0.2" step="0.01" /><p class="help">Valor valido entre 0 y 0.5.</p></div>
            </div>

            <details class="advanced"><summary>Configuracion avanzada (opcional)</summary><div class="adv-body"><input type="hidden" id="frame_pairs_json" name="frame_pairs_json" /><input type="hidden" id="optimization_overrides_json" name="optimization_overrides_json" />
              <div class="adv-block"><div class="toggle"><input type="checkbox" id="enable_frame_pairs" /><label for="enable_frame_pairs">Usar mapeo avanzado de vanos</label></div><p class="help">Define pares solo si vano sismico y gravedad no coinciden.</p><div id="frame-pairs-fields" class="adv-disabled"><div id="frame-pairs-list" class="pairs"></div><button type="button" class="mini-btn" id="btn-add-pair">Agregar mapeo</button></div></div>
              <div class="adv-block"><div class="toggle"><input type="checkbox" id="enable_optimization_overrides" /><label for="enable_optimization_overrides">Personalizar optimizacion</label></div><p class="help">La UI construye internamente JSON compatible con backend.</p><div id="optimization-fields" class="grid g2 adv-disabled"><div class="field"><label for="opt_generations">Cantidad de generaciones</label><input id="opt_generations" type="number" min="1" step="1" placeholder="Ej: 80" /><p class="help">Entero >= 1.</p></div><div class="field"><label for="opt_e_bars">Diametros para estribos cerrados</label><input id="opt_e_bars" type="text" placeholder="Ej: #3, #4, #6" /><p class="help">Separados por coma.</p></div><div class="field"><label for="opt_g_bars">Diametros para ramas simples</label><input id="opt_g_bars" type="text" placeholder="Ej: #3, #4, #6" /><p class="help">Separados por coma.</p></div><div class="field"><label for="opt_long_bars">Diametros para refuerzo longitudinal</label><input id="opt_long_bars" type="text" placeholder="Ej: #4, #5, #6" /><p class="help">Separados por coma.</p></div><div class="field"><label for="opt_spacing">Espaciamientos posibles de estribos (mm)</label><input id="opt_spacing" type="text" placeholder="Ej: 70, 80, 100" /><p class="help">Enteros positivos separados por coma.</p></div><div class="field"><label for="opt_long_counts">Cantidades posibles de barras longitudinales</label><input id="opt_long_counts" type="text" placeholder="Ej: 2, 4, 6, 8" /><p class="help">Enteros positivos separados por coma.</p></div></div></div>
            </div></details>
          </section>
        </section>

        <section id="view-import" class="view">
          <section class="card"><h2>ETABS Import y ejecucion</h2><p class="note">Carga los dos Excel y ejecuta el job asincrono sin cambiar contratos API.</p><div class="grid g2"><div class="field"><label for="seismic_excel">Excel sismico</label><input id="seismic_excel" name="seismic_excel" type="file" accept=".xlsx" required /></div><div class="field"><label for="gravity_excel">Excel gravedad</label><input id="gravity_excel" name="gravity_excel" type="file" accept=".xlsx" required /></div></div><div class="actions"><button type="submit" class="btn btn-primary" id="btn-submit"><span class="spinner" aria-hidden="true"></span><span id="btn-submit-label">Crear y ejecutar job</span></button><button type="button" class="btn btn-secondary" id="btn-clear">Limpiar estado</button></div></section>
        </section>

        <section id="view-results" class="view">
          <div class="results">
            <section class="card"><h2>Results - Beam elevation preview</h2><p class="note">Vista en alzado para lectura de zonas, espaciamientos y longitud total.</p><div id="beam-elevation-container" class="svg-wrap" aria-live="polite"></div><p id="beam-elevation-legend" class="legend">El SVG usa datos reales del case cuando existen, y fallback tecnico cuando faltan.</p></section>
            <div class="grid"><section class="card"><h2>Estado del job</h2><p class="note">Monitoreo en tiempo real, errores y trazabilidad.</p><span id="status" class="status">Esperando ejecucion</span><div id="error-box" class="alert hidden" role="alert" aria-live="assertive"></div><details style="margin-top:10px"><summary style="cursor:pointer;font-size:.82rem;color:#315171;font-weight:620">Ver detalle de respuesta</summary><pre id="details" class="log hidden"></pre></details></section><section class="card"><h2>Resumen tecnico</h2><ul id="summary-list" class="list"></ul></section><section class="card"><h2>Checks visuales</h2><ul id="checks-list" class="list"></ul></section></div>
          </div>
        </section>

        <section id="view-reports" class="view">
          <div class="grid g2"><section class="card"><h2>Export y accesos rapidos</h2><p class="note">Enlaces de estado, case generado y descarga ZIP.</p><div id="results-links" class="links"></div><div id="report-links" class="links"></div></section><section class="card"><h2>Artefactos detectados</h2><ul id="artifacts-list" class="list"></ul></section></div>
        </section>
      </form>
    </main>
  </div>

  <script>
    const form=document.getElementById("job-form"),submitBtn=document.getElementById("btn-submit"),submitLabel=document.getElementById("btn-submit-label"),clearBtn=document.getElementById("btn-clear"),globalStatusEl=document.getElementById("global-status"),statusEl=document.getElementById("status"),resultsLinksEl=document.getElementById("results-links"),reportLinksEl=document.getElementById("report-links"),detailsEl=document.getElementById("details"),errorBoxEl=document.getElementById("error-box"),summaryListEl=document.getElementById("summary-list"),checksListEl=document.getElementById("checks-list"),artifactsListEl=document.getElementById("artifacts-list"),beamElevationContainer=document.getElementById("beam-elevation-container"),beamElevationLegend=document.getElementById("beam-elevation-legend"),hiddenFramePairsInput=document.getElementById("frame_pairs_json"),hiddenOptimizationInput=document.getElementById("optimization_overrides_json"),enableFramePairs=document.getElementById("enable_frame_pairs"),framePairsFields=document.getElementById("frame-pairs-fields"),framePairsList=document.getElementById("frame-pairs-list"),addPairBtn=document.getElementById("btn-add-pair"),enableOptimizationOverrides=document.getElementById("enable_optimization_overrides"),optimizationFields=document.getElementById("optimization-fields"),optGenerations=document.getElementById("opt_generations"),optEBars=document.getElementById("opt_e_bars"),optGBars=document.getElementById("opt_g_bars"),optLongBars=document.getElementById("opt_long_bars"),optSpacing=document.getElementById("opt_spacing"),optLongCounts=document.getElementById("opt_long_counts");
    const navButtons=Array.from(document.querySelectorAll("[data-view]")),views=Array.from(document.querySelectorAll(".view"));
    let pollTimer=null,isSubmitting=false,currentJobId=null,currentCasePayload=null;
    const clamp=(v,min,max)=>Math.min(Math.max(v,min),max);
    const parseNum=(raw)=>{const n=Number(raw);return Number.isFinite(n)?n:null};
    function switchView(id){views.forEach(v=>v.classList.toggle("active",v.id===id));navButtons.forEach(b=>b.classList.toggle("active",b.dataset.view===id))}
    navButtons.forEach(btn=>btn.addEventListener("click",()=>switchView(btn.dataset.view)));
    function ensureFieldVisible(el){if(!el)return;const view=el.closest(".view");if(view)switchView(view.id);el.scrollIntoView({behavior:"smooth",block:"center"})}
    function headersWithApiKey(){const key=(document.getElementById("api_key").value||"").trim();return key?{"X-API-Key":key}:{}}
    function setStatus(text,tone=""){[globalStatusEl,statusEl].forEach(el=>{if(!el)return;el.className="status";if(tone)el.classList.add(tone);el.textContent=text})}
    function stopPolling(){if(pollTimer){clearInterval(pollTimer);pollTimer=null}}
    function setSubmitting(flag){isSubmitting=flag;submitBtn.disabled=flag;submitBtn.classList.toggle("loading",flag);submitLabel.textContent=flag?"Creando job...":"Crear y ejecutar job"}
    function clearErrorBox(){errorBoxEl.classList.add("hidden");errorBoxEl.innerHTML=""}
    function clearFieldErrors(){form.querySelectorAll("[aria-invalid='true']").forEach(el=>el.setAttribute("aria-invalid","false"));form.querySelectorAll(".field-error").forEach(el=>el.remove())}
    function markElementError(el,msg){if(!el)return;el.setAttribute("aria-invalid","true");const w=el.closest(".field");if(w){const p=document.createElement("p");p.className="field-error";p.textContent=msg;w.appendChild(p)}ensureFieldVisible(el)}
    function mapBackendField(field){if(!field)return null;const raw=String(field).toLowerCase();const map=[["sheet_name","sheet_name"],["region_c_ratio","region_c_ratio"],["min_branches","min_branches_c"],["fc_mpa","fc_mpa"],["fy_mpa","fy_mpa"],["width_mm","width_mm"],["height_mm","height_mm"],["d_mm","d_mm"],["db_bar","db_bar"],["cover_side_mm","cover_side_mm"],["cover_top_mm","cover_top_mm"],["cover_bottom_mm","cover_bottom_mm"],["frame_pairs","enable_frame_pairs"],["optimization","enable_optimization_overrides"],["seismic_excel","seismic_excel"],["gravity_excel","gravity_excel"]];for(const [t,id]of map){if(raw.includes(t))return id}return null}
    function normalizeErrorPayload(payload,status){if(!payload||typeof payload!=="object")return{error:"request_error",message:`No fue posible completar la solicitud (HTTP ${status}).`,details:[]};if(Array.isArray(payload.details))return{error:payload.error||"request_error",message:payload.message||"Error de solicitud",details:payload.details};if(Array.isArray(payload.detail))return{error:"validation_error",message:`No fue posible completar la solicitud (HTTP ${status}).`,details:payload.detail.map(it=>({code:it.type||"validation_error",field:Array.isArray(it.loc)?it.loc[it.loc.length-1]:"",message:it.msg||"Entrada invalida",severity:"error"}))};return{error:payload.error||"request_error",message:payload.message||payload.detail||"Error de solicitud",details:[]}}
    function renderError(payload){clearErrorBox();clearFieldErrors();const details=Array.isArray(payload?.details)?payload.details:[];const items=[];for(const d of details){const mapped=mapBackendField(d.field||"");if(mapped)markElementError(document.getElementById(mapped),d.message||"Valor no valido");const pref=d.field?`${d.field}: `:"";const suf=d.code?` [${d.code}]`:"";items.push(`<li>${pref}${d.message||"Detalle de validacion"}${suf}</li>`)}const list=items.length?`<ul>${items.join("")}</ul>`:"";errorBoxEl.innerHTML=`<h4>${payload?.message||"Error de solicitud"}</h4><p>Codigo: <strong>${payload?.error||"request_error"}</strong></p>${list}`;errorBoxEl.classList.remove("hidden");setStatus("Se encontraron errores de validacion","err");switchView("view-results")}
    function renderUiValidationErrors(errors){clearErrorBox();const items=[];for(const e of errors){if(e.element)markElementError(e.element,e.message);items.push(`<li>${e.label}: ${e.message}</li>`)}errorBoxEl.innerHTML=`<h4>Revisa la configuracion avanzada</h4><p>Codigo: <strong>ui_validation_error</strong></p><ul>${items.join("")}</ul>`;errorBoxEl.classList.remove("hidden");setStatus("Corrige errores de configuracion avanzada","err");switchView("view-results")}
    function showStatusPayload(payload){detailsEl.classList.remove("hidden");detailsEl.textContent=JSON.stringify(payload,null,2)}
    function renderArtifacts(items){const vals=Array.isArray(items)?items:[];artifactsListEl.innerHTML=vals.length?vals.map(v=>`<li>${v}</li>`).join(""):"<li>No hay artefactos disponibles aun.</li>"}
    function setLinks(jobId,payload){const su=payload.status_url||`/v1/jobs/${jobId}`,du=payload.download_url||`/v1/jobs/${jobId}/download`,cu=`/v1/jobs/${jobId}/case`;const html=`<a href="${su}" target="_blank" rel="noreferrer">Ver estado del job</a><a href="${du}" target="_blank" rel="noreferrer">Descargar reportes ZIP</a><a href="${cu}" target="_blank" rel="noreferrer">Ver case generado</a>`;resultsLinksEl.innerHTML=html;reportLinksEl.innerHTML=html}
    function createPairRow(initial={}){const row=document.createElement("div");row.className="pair-row";row.innerHTML=`<div class="field"><label>ID del vano</label><input type="text" class="pair-id" placeholder="Ej: S1" /></div><div class="field"><label>Vano sismico</label><input type="text" class="pair-seismic" placeholder="Ej: 190" /></div><div class="field"><label>Vano gravedad</label><input type="text" class="pair-gravity" placeholder="Ej: 190" /></div><div class="field"><label>Accion</label><button type="button" class="mini-btn mini-btn-danger pair-remove">Eliminar</button></div>`;row.querySelector(".pair-id").value=initial.id||"";row.querySelector(".pair-seismic").value=initial.seismic||"";row.querySelector(".pair-gravity").value=initial.gravity||"";row.querySelector(".pair-remove").addEventListener("click",()=>row.remove());return row}
    function parseCsvTokens(raw){return String(raw||"").split(",").map(v=>v.trim()).filter(v=>v.length>0)}
    function parsePositiveIntList(raw){const t=parseCsvTokens(raw);if(!t.length)return{ok:false,values:[],message:"La lista no puede estar vacia."};const values=[];for(const token of t){const p=Number(token);if(!Number.isInteger(p)||p<=0)return{ok:false,values:[],message:`Valor invalido: ${token}. Usa enteros positivos.`};values.push(p)}return{ok:true,values,message:""}}
    function setAdvancedControlsEnabled(container,en){container.classList.toggle("adv-disabled",!en);container.querySelectorAll("input,button").forEach(el=>{el.disabled=!en})}
    function syncAdvancedSections(){setAdvancedControlsEnabled(framePairsFields,enableFramePairs.checked);if(enableFramePairs.checked&&framePairsList.children.length===0)framePairsList.appendChild(createPairRow({}));setAdvancedControlsEnabled(optimizationFields,enableOptimizationOverrides.checked)}
    function buildAdvancedPayload(){hiddenFramePairsInput.value="";hiddenOptimizationInput.value="";const errors=[];if(enableFramePairs.checked){const rows=Array.from(framePairsList.querySelectorAll(".pair-row"));if(!rows.length){errors.push({label:"Mapeo avanzado",element:enableFramePairs,message:"Agrega al menos un mapeo."})}else{const pairs=[];rows.forEach((row,i)=>{const idIn=row.querySelector(".pair-id"),sIn=row.querySelector(".pair-seismic"),gIn=row.querySelector(".pair-gravity"),id=(idIn.value||"").trim()||`S${i+1}`,s=(sIn.value||"").trim(),g=(gIn.value||"").trim();if(!s)errors.push({label:`Mapeo fila ${i+1}`,element:sIn,message:"Vano sismico es obligatorio."});if(!g)errors.push({label:`Mapeo fila ${i+1}`,element:gIn,message:"Vano gravedad es obligatorio."});pairs.push({id,seismic:s,gravity:g})});if(!errors.length)hiddenFramePairsInput.value=JSON.stringify(pairs)}}if(enableOptimizationOverrides.checked){const genRaw=(optGenerations.value||"").trim(),gen=Number(genRaw);if(!genRaw)errors.push({label:"Generaciones",element:optGenerations,message:"Indica la cantidad de generaciones."});else if(!Number.isInteger(gen)||gen<1)errors.push({label:"Generaciones",element:optGenerations,message:"Debe ser un entero >= 1."});const eb=parseCsvTokens(optEBars.value),gb=parseCsvTokens(optGBars.value),lb=parseCsvTokens(optLongBars.value);if(!eb.length)errors.push({label:"Estribos cerrados",element:optEBars,message:"Define al menos un diametro."});if(!gb.length)errors.push({label:"Ramas simples",element:optGBars,message:"Define al menos un diametro."});if(!lb.length)errors.push({label:"Refuerzo longitudinal",element:optLongBars,message:"Define al menos un diametro."});const sp=parsePositiveIntList(optSpacing.value),lc=parsePositiveIntList(optLongCounts.value);if(!sp.ok)errors.push({label:"Espaciamientos",element:optSpacing,message:sp.message});if(!lc.ok)errors.push({label:"Cantidades longitudinales",element:optLongCounts,message:lc.message});if(!errors.length)hiddenOptimizationInput.value=JSON.stringify({variables:{E_bars:eb,G_bars:gb,stirrup_spacing_mm:sp.values,longitudinal_bars:lb,longitudinal_bar_counts:lc.values},genetic_algorithm:{generations:gen}})}if(errors.length){renderUiValidationErrors(errors);return false}return true}
    const defaultSpacing=t=>String(t||"").toUpperCase()==="C"?100:200;
    function collectFallback(){const r=clamp(parseNum(document.getElementById("region_c_ratio").value)||0.2,0.05,0.45);return{totalSpanMm:6000,totalSpanEstimated:true,beamDepthMm:parseNum(document.getElementById("height_mm").value)||600,beamWidthMm:parseNum(document.getElementById("width_mm").value)||300,beamId:(document.getElementById("beam_id").value||"B1").trim()||"B1",detailing:(document.getElementById("detailing").value||"DMO").trim()||"DMO",fcMpa:parseNum(document.getElementById("fc_mpa").value)||28,fyMpa:parseNum(document.getElementById("fy_mpa").value)||420,zones:[{id:"R1",label:"Zone 1",type:"C",startRatio:0,endRatio:r,spacingMm:100,spacingEstimated:true},{id:"R2",label:"Zone 2",type:"NC",startRatio:r,endRatio:1-r,spacingMm:200,spacingEstimated:true},{id:"R3",label:"Zone 3",type:"C",startRatio:1-r,endRatio:1,spacingMm:100,spacingEstimated:true}]}}
    function spanLength(span){if(!span||typeof span!=="object")return null;for(const k of ["total_span_mm","length_mm","span_mm","length"]){const v=parseNum(span[k]);if(v&&v>0)return v}return null}
    function buildBeamData(source){const fb=collectFallback(),cp=source&&source.casePayload;if(!cp||!Array.isArray(cp.beams)||!cp.beams.length)return fb;const beam=cp.beams[0]||{},span=Array.isArray(beam.spans)&&beam.spans.length?beam.spans[0]:null,regions=span&&Array.isArray(span.regions)?span.regions:[],zones=[];regions.forEach((rg,i)=>{const a=clamp(parseNum(rg.from)??0,0,1),b=clamp(parseNum(rg.to)??0,0,1);if(b<=a)return;const sRaw=parseNum(rg.spacing_mm),s=sRaw&&sRaw>0?sRaw:defaultSpacing(rg.type);zones.push({id:rg.id||`R${i+1}`,label:`Zone ${i+1}`,type:String(rg.type||"NC").toUpperCase(),startRatio:a,endRatio:b,spacingMm:s,spacingEstimated:!(sRaw&&sRaw>0)})});const L=spanLength(span);return{totalSpanMm:L||fb.totalSpanMm,totalSpanEstimated:!L,beamDepthMm:parseNum(beam.height_mm)||parseNum(span&&span.height_mm)||fb.beamDepthMm,beamWidthMm:parseNum(beam.width_mm)||parseNum(span&&span.width_mm)||fb.beamWidthMm,beamId:beam.beam_id||fb.beamId,detailing:beam.detailing||fb.detailing,fcMpa:parseNum(beam.fc_mpa)||fb.fcMpa,fyMpa:parseNum(beam.fy_mpa)||fb.fyMpa,zones:zones.length?zones:fb.zones}}
    function buildBeamSvg(d){const W=1200,H=350,x0=90,y=120,h=86,bw=W-2*x0,dy=66,by=y+h,total=Math.max(d.totalSpanMm||6000,1000),zones=Array.isArray(d.zones)&&d.zones.length?d.zones:[];let zoneRects="",zoneLines="",stirrup="",labels="";zones.forEach((z,i)=>{const xs=x0+z.startRatio*bw,xe=x0+z.endRatio*bw,zw=Math.max(xe-xs,8),fill=i%2?"rgba(36,92,140,0.07)":"rgba(20,65,106,0.10)";zoneRects+=`<rect x="${xs.toFixed(2)}" y="${y}" width="${zw.toFixed(2)}" height="${h}" fill="${fill}" />`;zoneLines+=`<line x1="${xs.toFixed(2)}" y1="${y}" x2="${xs.toFixed(2)}" y2="${by}" stroke="#28567f" stroke-width="1.2" stroke-dasharray="4 3" />`;const step=clamp((z.spacingMm/total)*bw,8,56);for(let xx=xs+6;xx<xe-6;xx+=step){stirrup+=`<path d="M ${xx.toFixed(2)} ${y+6} L ${xx.toFixed(2)} ${by-6}" stroke="#2f4f6f" stroke-width="1.1" fill="none" />`}const L=Math.round((z.endRatio-z.startRatio)*total),cx=xs+zw/2,sp=`@${Math.round(z.spacingMm)} mm c/c${z.spacingEstimated?" est.":""}`;labels+=`<text x="${cx.toFixed(2)}" y="270" text-anchor="middle" font-size="15" fill="#1a2f47" font-weight="620">${z.label} (L=${L} mm, ${sp})</text>`});const spanTxt=`${Math.round(total)} mm${d.totalSpanEstimated?" (estimado)":""}`;return `<svg id="beam-elevation" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Beam elevation"><defs><marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#1e334a" /></marker></defs><rect x="12" y="12" width="${W-24}" height="${H-24}" rx="8" fill="#f8fbff" stroke="#d0dcea" /><line x1="${x0}" y1="${dy}" x2="${x0+bw}" y2="${dy}" stroke="#1e334a" stroke-width="1.4" marker-start="url(#arrow)" marker-end="url(#arrow)" /><text x="${x0+bw/2}" y="${dy-10}" text-anchor="middle" font-size="16" fill="#16304a" font-weight="700">Total span: ${spanTxt}</text><line x1="${x0-36}" y1="${y}" x2="${x0-36}" y2="${by}" stroke="#1e334a" stroke-width="1.2" marker-start="url(#arrow)" marker-end="url(#arrow)" /><text x="${x0-48}" y="${y+h/2}" transform="rotate(-90 ${x0-48} ${y+h/2})" text-anchor="middle" font-size="13" fill="#183753" font-weight="620">h = ${Math.round(d.beamDepthMm||600)} mm</text><polygon points="${x0-14},${by+24} ${x0+14},${by+24} ${x0},${by+2}" fill="#5f748d" /><polygon points="${x0+bw-14},${by+24} ${x0+bw+14},${by+24} ${x0+bw},${by+2}" fill="#5f748d" />${zoneRects}<rect x="${x0}" y="${y}" width="${bw}" height="${h}" fill="none" stroke="#2b4f73" stroke-width="2.1" rx="4" />${zoneLines}${stirrup}<line x1="${x0+bw}" y1="${y}" x2="${x0+bw}" y2="${by}" stroke="#28567f" stroke-width="1.2" stroke-dasharray="4 3" />${labels}</svg>`}
    function renderBeam(container,data){container.innerHTML=buildBeamSvg(data);beamElevationLegend.textContent=data.totalSpanEstimated?"Se usan datos de fallback: total span estimado en 6000 mm. Se actualiza al obtener case real.":"Dibujo alimentado por case real del job. Si faltan espaciamientos, se usan valores estimados."}
    function renderSummary(data,st){summaryListEl.innerHTML=[`<li><strong>Beam:</strong> ${data.beamId} | Detailing ${data.detailing}</li>`,`<li><strong>Material:</strong> f'c ${Math.round(data.fcMpa)} MPa | fy ${Math.round(data.fyMpa)} MPa</li>`,`<li><strong>Seccion:</strong> b=${Math.round(data.beamWidthMm)} mm | h=${Math.round(data.beamDepthMm)} mm</li>`,`<li><strong>Total span:</strong> ${Math.round(data.totalSpanMm)} mm${data.totalSpanEstimated?" (estimado)":""}</li>`,`<li><strong>Job status:</strong> ${(st&&st.status)||"sin job"}</li>`].join("")}
    function renderChecks(st){const rows=[];const s=st&&st.status?st.status:"idle";if(s==="completed")rows.push({c:"ok",m:"Job completado correctamente."});else if(s==="failed")rows.push({c:"err",m:"Job finalizo en estado failed."});else if(s==="running"||s==="queued")rows.push({c:"warn",m:`Job en progreso: ${s}.`});else rows.push({c:"warn",m:"Aun no se ha ejecutado un job en esta sesion."});rows.push({c:"ok",m:"Contratos API preservados (/v1/jobs*)."});rows.push({c:"ok",m:"Preview SVG activo con fallback seguro."});checksListEl.innerHTML=rows.map(r=>`<li class="${r.c}">${r.m}</li>`).join("")}
    async function refreshCasePreview(jobId,statusPayload){let cp=null;try{const r=await fetch(`/v1/jobs/${jobId}/case`,{headers:headersWithApiKey()});if(r.ok){cp=await r.json();currentCasePayload=cp}}catch(e){cp=null}const data=buildBeamData({casePayload:cp});renderBeam(beamElevationContainer,data);renderSummary(data,statusPayload);renderChecks(statusPayload)}
    function refreshPreview(statusPayload=null){const data=buildBeamData({casePayload:currentCasePayload});renderBeam(beamElevationContainer,data);renderSummary(data,statusPayload);renderChecks(statusPayload)}
    async function refreshStatus(jobId){const response=await fetch(`/v1/jobs/${jobId}`,{headers:headersWithApiKey()}),payload=await response.json().catch(()=>({}));if(!response.ok){renderError(normalizeErrorPayload(payload,response.status));stopPolling();setSubmitting(false);return}showStatusPayload(payload);renderArtifacts(payload.artifacts);refreshPreview(payload);if(payload.status==="completed"){setStatus("Job completado. Puedes descargar resultados.","ok");await refreshCasePreview(jobId,payload);stopPolling();setSubmitting(false);switchView("view-results");return}if(payload.status==="failed"){renderError({error:"job_failed",message:`El job termino en estado failed${payload.error?`: ${payload.error}`:""}`,details:[]});stopPolling();setSubmitting(false);return}setStatus(`Job en progreso: ${payload.status}`,"running")}
    addPairBtn.addEventListener("click",()=>framePairsList.appendChild(createPairRow({})));enableFramePairs.addEventListener("change",syncAdvancedSections);enableOptimizationOverrides.addEventListener("change",syncAdvancedSections);syncAdvancedSections();
    ["beam_id","detailing","fc_mpa","fy_mpa","width_mm","height_mm","region_c_ratio"].forEach(id=>{const el=document.getElementById(id);if(el)el.addEventListener("input",()=>{currentCasePayload=null;refreshPreview()})});
    form.addEventListener("submit",async(event)=>{event.preventDefault();if(isSubmitting)return;stopPolling();clearErrorBox();clearFieldErrors();detailsEl.classList.add("hidden");detailsEl.textContent="";setSubmitting(true);setStatus("Validando datos y creando job...","running");switchView("view-results");if(!buildAdvancedPayload()){setSubmitting(false);return}const formData=new FormData(form);if(!formData.get("frame_pairs_json"))formData.delete("frame_pairs_json");if(!formData.get("optimization_overrides_json"))formData.delete("optimization_overrides_json");try{const response=await fetch("/v1/jobs/from-form",{method:"POST",body:formData,headers:headersWithApiKey()}),payload=await response.json().catch(()=>({}));if(!response.ok){renderError(normalizeErrorPayload(payload,response.status));setSubmitting(false);return}currentJobId=payload.job_id;currentCasePayload=null;setLinks(currentJobId,payload);renderArtifacts([]);setStatus(`Job ${currentJobId} creado. Iniciando monitoreo...`,"running");await refreshStatus(currentJobId);if(!pollTimer&&isSubmitting){pollTimer=setInterval(()=>{refreshStatus(currentJobId).catch((error)=>{renderError({error:"network_error",message:error?.message||"No fue posible consultar el estado del job",details:[]});stopPolling();setSubmitting(false)})},2500)}}catch(error){renderError({error:"network_error",message:error?.message||"No fue posible enviar la solicitud",details:[]});setSubmitting(false)}});
    clearBtn.addEventListener("click",()=>{stopPolling();currentJobId=null;currentCasePayload=null;setSubmitting(false);setStatus("Esperando ejecucion");resultsLinksEl.innerHTML="";reportLinksEl.innerHTML="";detailsEl.textContent="";detailsEl.classList.add("hidden");clearErrorBox();clearFieldErrors();renderArtifacts([]);refreshPreview()});
    renderArtifacts([]);refreshPreview();
  </script>
</body>
</html>
"""


@router.get("/ui", response_class=HTMLResponse)
def ui_page() -> HTMLResponse:
    return HTMLResponse(content=UI_HTML)
