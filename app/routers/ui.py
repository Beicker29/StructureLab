from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

UI_HTML = """<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ShearTors RC - Carga de Caso</title>
    <style>
      :root {
        --bg: #f4f7fb;
        --card: #ffffff;
        --text: #172030;
        --muted: #5f6c80;
        --primary: #0f766e;
        --primary-dark: #115e59;
        --border: #d9e1ee;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        color: var(--text);
        background: radial-gradient(circle at top left, #e8eef9, var(--bg));
      }
      main { max-width: 980px; margin: 24px auto; padding: 0 16px; }
      .card {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 24px rgba(16, 24, 40, 0.06);
      }
      h1 { margin: 0 0 8px; font-size: 1.6rem; }
      p { margin: 0 0 16px; color: var(--muted); }
      .grid {
        display: grid;
        gap: 12px;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      }
      label { font-size: 0.9rem; font-weight: 600; display: block; margin-bottom: 4px; }
      input, select, textarea, button {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid #c9d3e3;
        border-radius: 8px;
        font-size: 0.95rem;
      }
      textarea { min-height: 96px; resize: vertical; }
      .actions { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
      button {
        width: auto;
        min-width: 170px;
        border: none;
        background: var(--primary);
        color: white;
        cursor: pointer;
        font-weight: 600;
      }
      button:hover { background: var(--primary-dark); }
      .secondary {
        background: #e5e7eb;
        color: #111827;
      }
      .secondary:hover { background: #d1d5db; }
      .mono {
        font-family: Consolas, "Courier New", monospace;
        background: #f8fafc;
        border: 1px dashed #c9d3e3;
        padding: 10px;
        border-radius: 8px;
        margin-top: 12px;
        white-space: pre-wrap;
      }
      .status { margin-top: 10px; font-weight: 600; }
      .ok { color: #166534; }
      .warn { color: #92400e; }
      .err { color: #b91c1c; }
      @media (max-width: 640px) {
        .actions button { width: 100%; }
      }
    </style>
  </head>
  <body>
    <main>
      <div class="card">
        <h1>ShearTors RC - Ejecutar Caso sin case.json</h1>
        <p>Sube los dos Excel de ETABS, completa parametros base y la app generara automaticamente el case.json.</p>

        <form id="job-form">
          <div class="grid">
            <div>
              <label for="api_key">API Key (opcional)</label>
              <input id="api_key" name="api_key" placeholder="Solo si APP_API_KEY esta activa" />
            </div>
            <div>
              <label for="case_name">Nombre del caso</label>
              <input id="case_name" name="case_name" value="case_web" />
            </div>
            <div>
              <label for="sheet_name">Hoja ETABS</label>
              <input id="sheet_name" name="sheet_name" value="Conc Bm Sum - ACI 318-08" />
            </div>
            <div>
              <label for="detailing">Detailing</label>
              <select id="detailing" name="detailing">
                <option value="DMO" selected>DMO</option>
                <option value="DES">DES</option>
              </select>
            </div>
            <div>
              <label for="units_rebar_per_length">Unidad VRebar/TTrnRebar</label>
              <select id="units_rebar_per_length" name="units_rebar_per_length">
                <option value="mm2/m" selected>mm2/m</option>
                <option value="cm2/m">cm2/m</option>
              </select>
            </div>
            <div>
              <label for="beam_id">Beam ID</label>
              <input id="beam_id" name="beam_id" value="B1" />
            </div>
            <div>
              <label for="cover_side_mm">Recubrimiento lateral (mm)</label>
              <input id="cover_side_mm" name="cover_side_mm" type="number" value="40" step="0.1" />
            </div>
            <div>
              <label for="cover_top_mm">Recubrimiento superior (mm)</label>
              <input id="cover_top_mm" name="cover_top_mm" type="number" value="40" step="0.1" />
            </div>
            <div>
              <label for="cover_bottom_mm">Recubrimiento inferior (mm)</label>
              <input id="cover_bottom_mm" name="cover_bottom_mm" type="number" value="40" step="0.1" />
            </div>
            <div>
              <label for="fc_mpa">f'c (MPa)</label>
              <input id="fc_mpa" name="fc_mpa" type="number" value="28" step="0.1" />
            </div>
            <div>
              <label for="fy_mpa">fy (MPa)</label>
              <input id="fy_mpa" name="fy_mpa" type="number" value="420" step="0.1" />
            </div>
            <div>
              <label for="width_mm">Ancho de viga (mm)</label>
              <input id="width_mm" name="width_mm" type="number" value="300" step="0.1" />
            </div>
            <div>
              <label for="height_mm">Altura de viga (mm)</label>
              <input id="height_mm" name="height_mm" type="number" value="600" step="0.1" />
            </div>
            <div>
              <label for="d_mm">Peralte efectivo d (mm)</label>
              <input id="d_mm" name="d_mm" type="number" value="600" step="0.1" />
            </div>
            <div>
              <label for="db_bar">Barra longitudinal (db_bar)</label>
              <select id="db_bar" name="db_bar">
                <option>#3</option>
                <option>#4</option>
                <option>#5</option>
                <option selected>#6</option>
                <option>#7</option>
                <option>#8</option>
              </select>
            </div>
            <div>
              <label for="min_branches_c">Min ramas en regiones C</label>
              <input id="min_branches_c" name="min_branches_c" type="number" value="4" step="1" />
            </div>
            <div>
              <label for="min_branches_nc">Min ramas en region NC</label>
              <input id="min_branches_nc" name="min_branches_nc" type="number" value="2" step="1" />
            </div>
            <div>
              <label for="region_c_ratio">Fraccion C en extremos</label>
              <input id="region_c_ratio" name="region_c_ratio" type="number" value="0.2" step="0.01" />
            </div>
            <div>
              <label for="seismic_excel">Excel sismico</label>
              <input id="seismic_excel" name="seismic_excel" type="file" accept=".xlsx" required />
            </div>
            <div>
              <label for="gravity_excel">Excel gravedad</label>
              <input id="gravity_excel" name="gravity_excel" type="file" accept=".xlsx" required />
            </div>
          </div>

          <div style="margin-top: 12px;">
            <label for="frame_names_csv">Vanos a incluir (opcional, CSV)</label>
            <input id="frame_names_csv" name="frame_names_csv" placeholder="Ej: 190, 192, 205. Si se deja vacio se usa interseccion automatica." />
          </div>
          <div style="margin-top: 12px;">
            <label for="frame_pairs_json">Mapeo avanzado de vanos (opcional, JSON)</label>
            <textarea id="frame_pairs_json" name="frame_pairs_json" placeholder='[{"id":"S1","seismic":"190","gravity":"190"}]'></textarea>
          </div>
          <div style="margin-top: 12px;">
            <label for="optimization_overrides_json">Overrides de optimizacion (opcional, JSON)</label>
            <textarea id="optimization_overrides_json" name="optimization_overrides_json" placeholder='{"genetic_algorithm":{"generations":40}}'></textarea>
          </div>

          <div class="actions">
            <button type="submit">Crear y ejecutar job</button>
            <button type="button" class="secondary" id="btn-clear">Limpiar estado</button>
          </div>
        </form>

        <div id="status" class="status"></div>
        <div id="links"></div>
        <div id="details" class="mono" style="display:none;"></div>
      </div>
    </main>

    <script>
      const form = document.getElementById("job-form");
      const statusEl = document.getElementById("status");
      const linksEl = document.getElementById("links");
      const detailsEl = document.getElementById("details");
      const clearBtn = document.getElementById("btn-clear");
      let pollTimer = null;

      function setStatus(text, cssClass = "") {
        statusEl.className = "status " + cssClass;
        statusEl.textContent = text;
      }

      function headersWithApiKey() {
        const key = document.getElementById("api_key").value.trim();
        if (!key) return {};
        return { "X-API-Key": key };
      }

      function stopPolling() {
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
      }

      async function refreshStatus(jobId) {
        const response = await fetch(`/v1/jobs/${jobId}`, { headers: headersWithApiKey() });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.message || payload.detail || "Error consultando estado");
        }

        detailsEl.style.display = "block";
        detailsEl.textContent = JSON.stringify(payload, null, 2);

        if (payload.status === "completed") {
          setStatus("Job completado. Ya puedes descargar resultados.", "ok");
          stopPolling();
          return;
        }
        if (payload.status === "failed") {
          setStatus("Job fallido: " + (payload.error || "sin detalle"), "err");
          stopPolling();
          return;
        }
        setStatus("Job en progreso: " + payload.status, "warn");
      }

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        stopPolling();
        linksEl.innerHTML = "";
        detailsEl.style.display = "none";
        setStatus("Enviando archivos y creando job...", "warn");

        const formData = new FormData(form);
        if (!formData.get("frame_pairs_json")) formData.delete("frame_pairs_json");
        if (!formData.get("optimization_overrides_json")) formData.delete("optimization_overrides_json");
        if (!formData.get("frame_names_csv")) formData.delete("frame_names_csv");

        try {
          const response = await fetch("/v1/jobs/from-form", {
            method: "POST",
            body: formData,
            headers: headersWithApiKey(),
          });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.message || payload.detail || "No fue posible crear el job");
          }

          const jobId = payload.job_id;
          setStatus("Job creado: " + jobId, "warn");
          linksEl.innerHTML =
            `<p><a href="${payload.status_url}" target="_blank" rel="noreferrer">Ver estado</a> | ` +
            `<a href="${payload.download_url}" target="_blank" rel="noreferrer">Descargar ZIP</a> | ` +
            `<a href="/v1/jobs/${jobId}/case" target="_blank" rel="noreferrer">Ver case generado</a></p>`;

          await refreshStatus(jobId);
          pollTimer = setInterval(() => {
            refreshStatus(jobId).catch((err) => {
              stopPolling();
              setStatus(err.message, "err");
            });
          }, 2500);
        } catch (err) {
          setStatus(err.message || String(err), "err");
        }
      });

      clearBtn.addEventListener("click", () => {
        stopPolling();
        setStatus("");
        linksEl.innerHTML = "";
        detailsEl.textContent = "";
        detailsEl.style.display = "none";
      });
    </script>
  </body>
</html>
"""


@router.get("/ui", response_class=HTMLResponse)
def ui_page() -> HTMLResponse:
    return HTMLResponse(content=UI_HTML)

