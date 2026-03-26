(() => {
function fmtKg(value){
  const num = Number(value);
  return Number.isFinite(num) ? `${num.toFixed(2)} kg` : 'n/d';
}

function fmtPct(value){
  const num = Number(value);
  return Number.isFinite(num) ? `${num.toFixed(2)} %` : 'n/d';
}

function renderSummaryHtml(data, statusPayload){
  return [
    `<li><strong>Viga:</strong> ${data.beamId} | Detallado ${data.detailing}</li>`,
    `<li><strong>Material:</strong> f'c ${Math.round(data.fcMpa)} MPa | fy ${Math.round(data.fyMpa)} MPa</li>`,
    `<li><strong>Vanos:</strong> ${Array.isArray(data.spans)?data.spans.length:0}</li>`,
    `<li><strong>Longitud neta vanos:</strong> ${Math.round(data.totalSpanMm)} mm${data.totalSpanEstimated?' (estimado)':''}</li>`,
    `<li><strong>Longitud apoyos:</strong> ${Math.round(data.totalSupportMm||0)} mm</li>`,
    `<li><strong>Longitud total sistema:</strong> ${Math.round(data.totalSystemMm||data.totalSpanMm)} mm</li>`,
    `<li><strong>Estado job:</strong> ${(statusPayload&&statusPayload.status)||'sin job'}</li>`,
  ].join('');
}

function buildCheckRows(statusPayload){
  const rows = [];
  const status = statusPayload && statusPayload.status ? statusPayload.status : 'idle';
  if(status === 'completed') rows.push({c:'ok', m:'Job completado correctamente.'});
  else if(status === 'failed') rows.push({c:'err', m:'Job finalizo en estado failed.'});
  else if(status === 'running' || status === 'queued') rows.push({c:'warn', m:`Job en progreso: ${status}.`});
  else rows.push({c:'warn', m:'Aun no se ha ejecutado un job en esta sesion.'});
  rows.push({c:'ok', m:'Contratos API preservados (/v1/jobs*).'});
  rows.push({c:'ok', m:'Preview SVG soporta vanos multiples, apoyos y regiones por vano.'});
  return rows;
}

window.StructureLabStatus = {
  fmtKg,
  fmtPct,
  renderSummaryHtml,
  buildCheckRows,
};
})();
