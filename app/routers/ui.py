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
        --bg-a: #e7edf6;
        --bg-b: #f6f8fc;
        --panel: #fcfdff;
        --panel-border: #cbd6e5;
        --text: #15253a;
        --muted: #54637c;
        --accent: #0e5a73;
        --accent-strong: #0a4b60;
        --secondary-bg: #e8edf5;
        --secondary-text: #1e2f45;
        --input-bg: #ffffff;
        --input-border: #bdc9da;
        --ok: #1f6b43;
        --warn: #8c5a00;
        --err: #a12821;
        --err-bg: #fdeceb;
        --err-border: #e5b1ad;
        --shadow: 0 10px 26px rgba(19, 37, 58, 0.08);
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        min-height: 100vh;
        font-family: "IBM Plex Sans", "Segoe UI", Tahoma, sans-serif;
        color: var(--text);
        background: linear-gradient(145deg, var(--bg-a) 0%, var(--bg-b) 52%, #eef3f9 100%);
      }

      .page {
        max-width: 1180px;
        margin: 0 auto;
        padding: 24px 16px 36px;
      }

      .page-header {
        margin-bottom: 14px;
      }

      .page-title {
        margin: 0;
        font-size: 1.5rem;
        letter-spacing: 0.01em;
      }

      .page-subtitle {
        margin: 6px 0 0;
        color: var(--muted);
        font-size: 0.94rem;
      }

      .workspace {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 350px;
        gap: 14px;
        align-items: start;
      }

      .panel {
        border: 1px solid var(--panel-border);
        border-radius: 14px;
        background: var(--panel);
        box-shadow: var(--shadow);
      }

      .section-card {
        padding: 16px 16px 14px;
      }

      .section-card + .section-card {
        margin-top: 10px;
      }

      .section-title {
        margin: 0 0 6px;
        font-size: 1.02rem;
        font-weight: 650;
      }

      .section-note {
        margin: 0 0 12px;
        color: var(--muted);
        font-size: 0.84rem;
      }

      .grid {
        display: grid;
        gap: 11px;
      }

      .cols-3 {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }

      .cols-2 {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .field label {
        display: block;
        margin-bottom: 5px;
        font-size: 0.84rem;
        font-weight: 620;
        color: #1a2c42;
      }

      .field input,
      .field select,
      .field textarea {
        width: 100%;
        padding: 10px 11px;
        border-radius: 9px;
        border: 1px solid var(--input-border);
        background: var(--input-bg);
        color: var(--text);
        font-size: 0.92rem;
        transition: border-color 0.18s ease, box-shadow 0.18s ease;
      }

      .field textarea {
        min-height: 104px;
        resize: vertical;
        font-family: "IBM Plex Mono", "Consolas", "Liberation Mono", monospace;
        font-size: 0.86rem;
      }

      .field input:focus,
      .field select:focus,
      .field textarea:focus {
        outline: none;
        border-color: var(--accent);
        box-shadow: 0 0 0 3px rgba(14, 90, 115, 0.14);
      }

      .field [aria-invalid="true"] {
        border-color: var(--err);
        background: #fff8f8;
      }

      .field-help {
        margin: 5px 0 0;
        font-size: 0.78rem;
        color: var(--muted);
      }

      .field-error {
        margin: 6px 0 0;
        font-size: 0.79rem;
        color: var(--err);
      }

      .advanced {
        border: 1px solid var(--panel-border);
        border-radius: 11px;
        background: #f7fafe;
      }

      .advanced > summary {
        list-style: none;
        cursor: pointer;
        padding: 11px 12px;
        font-size: 0.9rem;
        font-weight: 620;
        color: #1a3048;
      }

      .advanced > summary::-webkit-details-marker {
        display: none;
      }

      .advanced[open] > summary {
        border-bottom: 1px solid var(--panel-border);
      }

      .advanced-body {
        padding: 12px;
      }

      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 9px;
        align-items: center;
      }

      .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        min-width: 186px;
        border-radius: 10px;
        border: 1px solid transparent;
        padding: 10px 14px;
        font-size: 0.9rem;
        font-weight: 640;
        cursor: pointer;
      }

      .btn:disabled {
        cursor: not-allowed;
        opacity: 0.72;
      }

      .btn-primary {
        color: #fff;
        background: linear-gradient(180deg, var(--accent), var(--accent-strong));
      }

      .btn-primary:hover:enabled {
        filter: brightness(1.03);
      }

      .btn-secondary {
        color: var(--secondary-text);
        border-color: #c4d1e2;
        background: var(--secondary-bg);
      }

      .btn-secondary:hover:enabled {
        background: #dfe8f4;
      }

      .spinner {
        width: 13px;
        height: 13px;
        border-radius: 50%;
        border: 2px solid rgba(255, 255, 255, 0.45);
        border-top-color: rgba(255, 255, 255, 1);
        animation: spin 0.8s linear infinite;
        display: none;
      }

      .btn.is-loading .spinner {
        display: inline-block;
      }

      @keyframes spin {
        to {
          transform: rotate(360deg);
        }
      }

      .feedback-panel {
        position: sticky;
        top: 14px;
        padding: 14px;
      }

      .status-chip {
        display: inline-flex;
        align-items: center;
        min-height: 34px;
        border-radius: 999px;
        border: 1px solid #c9d5e4;
        background: #f2f6fb;
        color: #2a3d57;
        font-size: 0.85rem;
        font-weight: 620;
        padding: 7px 12px;
      }

      .status-chip.running {
        border-color: #d8be88;
        background: #fff8ea;
        color: var(--warn);
      }

      .status-chip.ok {
        border-color: #a8d0bb;
        background: #ecf8f1;
        color: var(--ok);
      }

      .status-chip.err {
        border-color: #e0afa9;
        background: #fff1f0;
        color: var(--err);
      }

      .alert {
        margin-top: 12px;
        border: 1px solid var(--err-border);
        background: var(--err-bg);
        border-radius: 10px;
        color: #5f1d1b;
        padding: 10px 11px;
      }

      .alert-title {
        margin: 0;
        font-size: 0.88rem;
        font-weight: 700;
      }

      .alert-code {
        margin-top: 4px;
        font-size: 0.76rem;
      }

      .alert-list {
        margin: 8px 0 0;
        padding-left: 18px;
        font-size: 0.8rem;
      }

      .hidden {
        display: none;
      }

      .links {
        margin-top: 10px;
        display: grid;
        gap: 6px;
      }

      .links a {
        color: var(--accent);
        text-decoration: none;
        font-size: 0.84rem;
        font-weight: 620;
      }

      .links a:hover {
        text-decoration: underline;
      }

      .details-log {
        margin-top: 10px;
        border: 1px dashed #bbc8da;
        border-radius: 10px;
        background: #f8fbff;
        padding: 10px;
        font-size: 0.78rem;
        line-height: 1.35;
        color: #263952;
        max-height: 380px;
        overflow: auto;
        font-family: "IBM Plex Mono", "Consolas", "Liberation Mono", monospace;
        white-space: pre-wrap;
      }

      @media (max-width: 1060px) {
        .workspace {
          grid-template-columns: 1fr;
        }

        .feedback-panel {
          position: static;
        }
      }

      @media (max-width: 860px) {
        .cols-3 {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }

      @media (max-width: 620px) {
        .cols-3,
        .cols-2 {
          grid-template-columns: 1fr;
        }

        .btn {
          width: 100%;
        }
      }
    </style>
  </head>
  <body>
    <main class="page">
      <header class="page-header">
        <h1 class="page-title">ShearTors RC · Crear y ejecutar job</h1>
        <p class="page-subtitle">
          Genera el caso desde formulario, valida entradas y ejecuta el flujo ETABS sin editar manualmente el <code>case.json</code>.
        </p>
      </header>

      <div class="workspace">
        <form id="job-form" novalidate>
          <section class="panel section-card">
            <h2 class="section-title">Información general</h2>
            <p class="section-note">Parámetros base del caso y configuración de diseño.</p>
            <div class="grid cols-3">
              <div class="field">
                <label for="api_key">API Key (opcional)</label>
                <input id="api_key" name="api_key" autocomplete="off" placeholder="Solo si APP_API_KEY está activa" />
              </div>
              <div class="field">
                <label for="case_name">Nombre del caso</label>
                <input id="case_name" name="case_name" value="case_web" />
              </div>
              <div class="field">
                <label for="beam_id">Beam ID</label>
                <input id="beam_id" name="beam_id" value="B1" />
              </div>
              <div class="field">
                <label for="sheet_name">Hoja ETABS</label>
                <input id="sheet_name" name="sheet_name" value="Conc Bm Sum - ACI 318-08" />
                <p class="field-help">Debe coincidir exactamente con el nombre de hoja en ambos archivos Excel.</p>
              </div>
              <div class="field">
                <label for="detailing">Detailing</label>
                <select id="detailing" name="detailing">
                  <option value="DMO" selected>DMO</option>
                  <option value="DES">DES</option>
                </select>
              </div>
              <div class="field">
                <label for="units_rebar_per_length">Unidad VRebar/TTrnRebar</label>
                <select id="units_rebar_per_length" name="units_rebar_per_length">
                  <option value="mm2/m" selected>mm2/m</option>
                  <option value="cm2/m">cm2/m</option>
                </select>
                <p class="field-help">Usa la unidad con la que ETABS exportó demandas de refuerzo transversal.</p>
              </div>
            </div>
          </section>

          <section class="panel section-card">
            <h2 class="section-title">Materiales</h2>
            <p class="section-note">Resistencias de concreto y acero para validación de reglas y detailing.</p>
            <div class="grid cols-2">
              <div class="field">
                <label for="fc_mpa">f'c (MPa)</label>
                <input id="fc_mpa" name="fc_mpa" type="number" value="28" step="0.1" />
              </div>
              <div class="field">
                <label for="fy_mpa">fy (MPa)</label>
                <input id="fy_mpa" name="fy_mpa" type="number" value="420" step="0.1" />
              </div>
            </div>
          </section>

          <section class="panel section-card">
            <h2 class="section-title">Geometría</h2>
            <p class="section-note">Dimensiones globales y recubrimientos para chequeos de espaciamiento y capacidad.</p>
            <div class="grid cols-3">
              <div class="field">
                <label for="width_mm">Ancho de viga (mm)</label>
                <input id="width_mm" name="width_mm" type="number" value="300" step="0.1" />
              </div>
              <div class="field">
                <label for="height_mm">Altura de viga (mm)</label>
                <input id="height_mm" name="height_mm" type="number" value="600" step="0.1" />
              </div>
              <div class="field">
                <label for="d_mm">Peralte efectivo d (mm)</label>
                <input id="d_mm" name="d_mm" type="number" value="600" step="0.1" />
              </div>
              <div class="field">
                <label for="cover_side_mm">Recubrimiento lateral (mm)</label>
                <input id="cover_side_mm" name="cover_side_mm" type="number" value="40" step="0.1" />
              </div>
              <div class="field">
                <label for="cover_top_mm">Recubrimiento superior (mm)</label>
                <input id="cover_top_mm" name="cover_top_mm" type="number" value="40" step="0.1" />
              </div>
              <div class="field">
                <label for="cover_bottom_mm">Recubrimiento inferior (mm)</label>
                <input id="cover_bottom_mm" name="cover_bottom_mm" type="number" value="40" step="0.1" />
              </div>
            </div>
          </section>

          <section class="panel section-card">
            <h2 class="section-title">Refuerzo base</h2>
            <p class="section-note">Parámetros de regiones C/NC para construcción automática de vanos y regiones.</p>
            <div class="grid cols-3">
              <div class="field">
                <label for="db_bar">Barra longitudinal de referencia (db_bar)</label>
                <select id="db_bar" name="db_bar">
                  <option>#3</option>
                  <option>#4</option>
                  <option>#5</option>
                  <option selected>#6</option>
                  <option>#7</option>
                  <option>#8</option>
                </select>
              </div>
              <div class="field">
                <label for="min_branches_c">Mínimo ramas en región C</label>
                <input id="min_branches_c" name="min_branches_c" type="number" value="4" step="1" />
              </div>
              <div class="field">
                <label for="min_branches_nc">Mínimo ramas en región NC</label>
                <input id="min_branches_nc" name="min_branches_nc" type="number" value="2" step="1" />
              </div>
              <div class="field">
                <label for="region_c_ratio">Fracción C en extremos</label>
                <input id="region_c_ratio" name="region_c_ratio" type="number" value="0.2" step="0.01" />
                <p class="field-help">Valor válido entre 0 y 0.5. La zona central se calcula automáticamente.</p>
              </div>
            </div>
          </section>

          <section class="panel section-card">
            <h2 class="section-title">Archivos ETABS</h2>
            <p class="section-note">Carga ambos archivos <code>.xlsx</code> con la misma hoja seleccionada.</p>
            <div class="grid cols-2">
              <div class="field">
                <label for="seismic_excel">Excel sísmico</label>
                <input id="seismic_excel" name="seismic_excel" type="file" accept=".xlsx" required />
              </div>
              <div class="field">
                <label for="gravity_excel">Excel gravedad</label>
                <input id="gravity_excel" name="gravity_excel" type="file" accept=".xlsx" required />
              </div>
            </div>
          </section>

          <section class="panel section-card">
            <details class="advanced">
              <summary>Configuración avanzada (opcional)</summary>
              <div class="advanced-body">
                <div class="grid">
                  <div class="field">
                    <label for="frame_names_csv">Vanos por CSV</label>
                    <input id="frame_names_csv" name="frame_names_csv" placeholder="Ejemplo: 190, 192, 205" />
                    <p class="field-help">Si se deja vacío, se usa la intersección automática entre sísmico y gravedad.</p>
                  </div>
                  <div class="field">
                    <label for="frame_pairs_json">Mapeo avanzado de vanos (JSON)</label>
                    <textarea id="frame_pairs_json" name="frame_pairs_json" placeholder='[{"id":"S1","seismic":"190","gravity":"190"}]'></textarea>
                    <p class="field-help">Úsalo cuando los UniqueName difieren entre ambos archivos ETABS.</p>
                  </div>
                  <div class="field">
                    <label for="optimization_overrides_json">Overrides de optimización (JSON)</label>
                    <textarea id="optimization_overrides_json" name="optimization_overrides_json" placeholder='{"genetic_algorithm":{"generations":40}}'></textarea>
                    <p class="field-help">Solo incluye las claves a sobrescribir; el resto usa defaults del sistema.</p>
                  </div>
                </div>
              </div>
            </details>
          </section>

          <section class="panel section-card">
            <div class="actions">
              <button type="submit" class="btn btn-primary" id="btn-submit">
                <span class="spinner" aria-hidden="true"></span>
                <span id="btn-submit-label">Crear y ejecutar job</span>
              </button>
              <button type="button" class="btn btn-secondary" id="btn-clear">Limpiar estado</button>
            </div>
          </section>
        </form>

        <aside class="panel feedback-panel" id="feedback-panel">
          <h2 class="section-title">Ejecución y resultados</h2>
          <p class="section-note">Monitoreo del job, errores del backend y accesos rápidos a resultados.</p>
          <div id="status" class="status-chip" aria-live="polite">Esperando ejecución</div>
          <div id="error-box" class="alert hidden" role="alert" aria-live="assertive"></div>
          <div id="links" class="links"></div>
          <pre id="details" class="details-log hidden"></pre>
        </aside>
      </div>
    </main>

    <script>
      const form = document.getElementById("job-form");
      const submitBtn = document.getElementById("btn-submit");
      const submitLabel = document.getElementById("btn-submit-label");
      const clearBtn = document.getElementById("btn-clear");
      const statusEl = document.getElementById("status");
      const linksEl = document.getElementById("links");
      const detailsEl = document.getElementById("details");
      const errorBoxEl = document.getElementById("error-box");
      const feedbackPanel = document.getElementById("feedback-panel");

      let pollTimer = null;
      let isSubmitting = false;
      let currentJobId = null;

      function scrollToFeedback() {
        feedbackPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      }

      function escapeHtml(value) {
        return String(value)
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#39;");
      }

      function headersWithApiKey() {
        const key = (document.getElementById("api_key").value || "").trim();
        if (!key) return {};
        return { "X-API-Key": key };
      }

      function setStatus(text, tone = "") {
        statusEl.className = "status-chip";
        if (tone) statusEl.classList.add(tone);
        statusEl.textContent = text;
      }

      function stopPolling() {
        if (pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
      }

      function setSubmitting(flag) {
        isSubmitting = flag;
        submitBtn.disabled = flag;
        submitBtn.classList.toggle("is-loading", flag);
        submitLabel.textContent = flag ? "Creando job..." : "Crear y ejecutar job";
      }

      function clearErrorBox() {
        errorBoxEl.classList.add("hidden");
        errorBoxEl.innerHTML = "";
      }

      function clearFieldErrors() {
        form.querySelectorAll("[aria-invalid='true']").forEach((element) => {
          element.setAttribute("aria-invalid", "false");
        });
        form.querySelectorAll(".field-error").forEach((element) => element.remove());
      }

      function mapBackendField(fieldPath) {
        if (!fieldPath) return null;
        const raw = String(fieldPath).trim();
        if (!raw) return null;
        if (form.elements.namedItem(raw)) return raw;

        const lowered = raw.toLowerCase();
        const mappings = [
          ["sheet_name", "sheet_name"],
          ["region_c_ratio", "region_c_ratio"],
          ["min_branches", "min_branches_c"],
          ["fc_mpa", "fc_mpa"],
          ["fy_mpa", "fy_mpa"],
          ["width_mm", "width_mm"],
          ["height_mm", "height_mm"],
          ["d_mm", "d_mm"],
          ["db_bar", "db_bar"],
          ["cover_side_mm", "cover_side_mm"],
          ["cover_top_mm", "cover_top_mm"],
          ["cover_bottom_mm", "cover_bottom_mm"],
          ["frame_pairs", "frame_pairs_json"],
          ["frame_names", "frame_names_csv"],
          ["optimization", "optimization_overrides_json"],
          ["seismic_excel", "seismic_excel"],
          ["gravity_excel", "gravity_excel"],
        ];
        for (const [token, mapped] of mappings) {
          if (lowered.includes(token)) return mapped;
        }
        return null;
      }

      function attachFieldError(fieldName, message) {
        if (!fieldName || !message) return;
        const element = form.elements.namedItem(fieldName);
        if (!element || element instanceof RadioNodeList) return;

        element.setAttribute("aria-invalid", "true");
        const wrapper = element.closest(".field");
        if (!wrapper) return;

        const msg = document.createElement("p");
        msg.className = "field-error";
        msg.textContent = message;
        wrapper.appendChild(msg);
      }

      function normalizeErrorPayload(rawPayload, statusCode) {
        const fallback = {
          error: "request_error",
          message: `No fue posible completar la solicitud (HTTP ${statusCode}).`,
          details: [],
        };
        if (!rawPayload || typeof rawPayload !== "object") return fallback;

        let details = [];
        if (Array.isArray(rawPayload.details)) {
          details = rawPayload.details;
        } else if (Array.isArray(rawPayload.detail)) {
          details = rawPayload.detail.map((item) => {
            const loc = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "";
            return {
              code: item.type || "validation_error",
              field: loc || "",
              message: item.msg || "Entrada invalida",
              severity: "error",
            };
          });
        }

        const message =
          rawPayload.message ||
          (typeof rawPayload.detail === "string" ? rawPayload.detail : fallback.message);

        return {
          error: rawPayload.error || (statusCode === 422 ? "validation_error" : fallback.error),
          message,
          details,
        };
      }

      function renderError(errorPayload) {
        clearErrorBox();
        clearFieldErrors();

        const title = escapeHtml(errorPayload.message || "Error de solicitud");
        const code = escapeHtml(errorPayload.error || "request_error");
        let detailsHtml = "";

        if (Array.isArray(errorPayload.details) && errorPayload.details.length > 0) {
          const items = [];
          for (const item of errorPayload.details) {
            const field = item.field ? String(item.field) : "";
            const mappedField = mapBackendField(field);
            if (mappedField) {
              attachFieldError(mappedField, item.message || "Valor no válido");
            }
            const itemCode = item.code ? ` [${escapeHtml(item.code)}]` : "";
            const itemField = field ? `${escapeHtml(field)}: ` : "";
            items.push(`<li>${itemField}${escapeHtml(item.message || "Detalle de validación")}${itemCode}</li>`);
          }
          detailsHtml = `<ul class="alert-list">${items.join("")}</ul>`;
        }

        errorBoxEl.innerHTML =
          `<p class="alert-title">${title}</p>` +
          `<p class="alert-code">Código: <strong>${code}</strong></p>` +
          detailsHtml;
        errorBoxEl.classList.remove("hidden");
        setStatus("Se encontraron errores de validación", "err");
        scrollToFeedback();
      }

      function setLinks(jobId, payload) {
        const statusUrl = payload.status_url || `/v1/jobs/${jobId}`;
        const downloadUrl = payload.download_url || `/v1/jobs/${jobId}/download`;
        linksEl.innerHTML =
          `<a href="${statusUrl}" target="_blank" rel="noreferrer">Ver estado del job</a>` +
          `<a href="${downloadUrl}" target="_blank" rel="noreferrer">Descargar reportes ZIP</a>` +
          `<a href="/v1/jobs/${jobId}/case" target="_blank" rel="noreferrer">Ver case generado</a>`;
      }

      function showStatusPayload(payload) {
        detailsEl.classList.remove("hidden");
        detailsEl.textContent = JSON.stringify(payload, null, 2);
      }

      async function refreshStatus(jobId) {
        const response = await fetch(`/v1/jobs/${jobId}`, { headers: headersWithApiKey() });
        const payload = await response.json().catch(() => ({}));

        if (!response.ok) {
          renderError(normalizeErrorPayload(payload, response.status));
          stopPolling();
          setSubmitting(false);
          return;
        }

        showStatusPayload(payload);

        if (payload.status === "completed") {
          setStatus("Job completado. Puedes descargar resultados.", "ok");
          stopPolling();
          setSubmitting(false);
          scrollToFeedback();
          return;
        }
        if (payload.status === "failed") {
          const failure = payload.error ? `: ${payload.error}` : "";
          renderError({
            error: "job_failed",
            message: `El job terminó en estado failed${failure}`,
            details: [],
          });
          stopPolling();
          setSubmitting(false);
          return;
        }
        setStatus(`Job en progreso: ${payload.status}`, "running");
      }

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (isSubmitting) return;

        stopPolling();
        clearErrorBox();
        clearFieldErrors();
        detailsEl.classList.add("hidden");
        detailsEl.textContent = "";
        linksEl.innerHTML = "";

        setSubmitting(true);
        setStatus("Validando datos y creando job...", "running");
        scrollToFeedback();

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
          const payload = await response.json().catch(() => ({}));
          if (!response.ok) {
            renderError(normalizeErrorPayload(payload, response.status));
            setSubmitting(false);
            return;
          }

          currentJobId = payload.job_id;
          setLinks(currentJobId, payload);
          setStatus(`Job ${currentJobId} creado. Iniciando monitoreo...`, "running");
          await refreshStatus(currentJobId);

          if (!pollTimer && isSubmitting) {
            pollTimer = setInterval(() => {
              refreshStatus(currentJobId).catch((error) => {
                renderError({
                  error: "network_error",
                  message: error?.message || "No fue posible consultar el estado del job",
                  details: [],
                });
                stopPolling();
                setSubmitting(false);
              });
            }, 2500);
          }
        } catch (error) {
          renderError({
            error: "network_error",
            message: error?.message || "No fue posible enviar la solicitud",
            details: [],
          });
          setSubmitting(false);
        }
      });

      clearBtn.addEventListener("click", () => {
        stopPolling();
        currentJobId = null;
        setSubmitting(false);
        setStatus("Esperando ejecución");
        linksEl.innerHTML = "";
        detailsEl.textContent = "";
        detailsEl.classList.add("hidden");
        clearErrorBox();
        clearFieldErrors();
      });
    </script>
  </body>
</html>
"""


@router.get("/ui", response_class=HTMLResponse)
def ui_page() -> HTMLResponse:
    return HTMLResponse(content=UI_HTML)
