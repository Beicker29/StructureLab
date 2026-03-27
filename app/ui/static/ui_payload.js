(() => {
function parseCsvTokens(raw){
  return String(raw || '').split(',').map(v => v.trim()).filter(v => v.length > 0);
}

function parsePositiveIntList(raw){
  const tokens = parseCsvTokens(raw);
  if(!tokens.length){
    return {ok:false, values:[], message:'La lista no puede estar vacia.'};
  }
  const values = [];
  for(const token of tokens){
    const parsed = Number(token);
    if(!Number.isInteger(parsed) || parsed <= 0){
      return {ok:false, values:[], message:`Valor invalido: ${token}. Usa enteros positivos.`};
    }
    values.push(parsed);
  }
  return {ok:true, values, message:''};
}

function mapBackendField(field){
  if(!field) return null;
  const raw = String(field).toLowerCase();
  const map = [
    ['sheet_name','sheet_name'],
    ['region_c_ratio','region_c_ratio'],
    ['min_branches','min_branches_c'],
    ['fc_mpa','fc_mpa'],
    ['fy_mpa','fy_mpa'],
    ['width_mm','width_mm'],
    ['height_mm','height_mm'],
    ['d_mm','d_mm'],
    ['d_ratio','enable_span_layout'],
    ['clear_length_mm','enable_span_layout'],
    ['is_deep_beam','enable_span_layout'],
    ['db_bar','db_bar'],
    ['cover_side_mm','cover_side_mm'],
    ['cover_top_mm','cover_top_mm'],
    ['cover_bottom_mm','cover_bottom_mm'],
    ['frame_pairs','enable_span_layout'],
    ['span_layout','enable_span_layout'],
    ['optimization','enable_optimization_overrides'],
    ['population_size','opt_population_size'],
    ['generations','opt_generations'],
    ['seismic_excel','seismic_excel'],
    ['gravity_excel','gravity_excel'],
    ['geometry_excel','geometry_excel'],
  ];
  for(const [token, id] of map){
    if(raw.includes(token)) return id;
  }
  return null;
}

function normalizeErrorPayload(payload, status){
  if(!payload || typeof payload !== 'object'){
    return {
      error:'request_error',
      message:`No fue posible completar la solicitud (HTTP ${status}).`,
      details:[],
    };
  }
  if(Array.isArray(payload.details)){
    return {
      error:payload.error || 'request_error',
      message:payload.message || 'Error de solicitud',
      details:payload.details,
    };
  }
  if(Array.isArray(payload.detail)){
    return {
      error:'validation_error',
      message:`No fue posible completar la solicitud (HTTP ${status}).`,
      details:payload.detail.map(it => ({
        code:it.type || 'validation_error',
        field:Array.isArray(it.loc) ? it.loc[it.loc.length - 1] : '',
        message:it.msg || 'Entrada invalida',
        severity:'error',
      })),
    };
  }
  return {
    error:payload.error || 'request_error',
    message:payload.message || payload.detail || 'Error de solicitud',
    details:[],
  };
}

window.StructureLabPayload = {
  parseCsvTokens,
  parsePositiveIntList,
  mapBackendField,
  normalizeErrorPayload,
};
})();

