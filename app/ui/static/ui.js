(() => {
const form=document.getElementById('job-form'),submitBtn=document.getElementById('btn-submit'),submitLabel=document.getElementById('btn-submit-label'),clearBtn=document.getElementById('btn-clear'),globalStatusEl=document.getElementById('global-status'),statusEl=document.getElementById('status'),resultsLinksEl=document.getElementById('results-links'),detailsEl=document.getElementById('details'),errorBoxEl=document.getElementById('error-box'),summaryListEl=document.getElementById('summary-list'),checksListEl=document.getElementById('checks-list'),artifactsListEl=document.getElementById('artifacts-list'),beamElevationContainer=document.getElementById('beam-elevation-container'),beamElevationLegend=document.getElementById('beam-elevation-legend'),regionOptionsEl=document.getElementById('region-options'),saveSelectionBtn=document.getElementById('btn-save-selection'),selectionSaveMsg=document.getElementById('selection-save-msg'),hiddenFramePairsInput=document.getElementById('frame_pairs_json'),hiddenOptimizationInput=document.getElementById('optimization_overrides_json'),hiddenSpanLayoutInput=document.getElementById('span_layout_json'),enableSpanLayout=document.getElementById('enable_span_layout'),spanLayoutFields=document.getElementById('span-layout-fields'),spanLayoutList=document.getElementById('span-layout-list'),addSpanBtn=document.getElementById('btn-add-span'),enableOptimizationOverrides=document.getElementById('enable_optimization_overrides'),optimizationFields=document.getElementById('optimization-fields'),optGenerations=document.getElementById('opt_generations'),optPopulationSize=document.getElementById('opt_population_size'),optEBars=document.getElementById('opt_e_bars'),optGBars=document.getElementById('opt_g_bars'),optLongBars=document.getElementById('opt_long_bars'),optSpacing=document.getElementById('opt_spacing'),optLongCounts=document.getElementById('opt_long_counts'),optLongitudinalMode=document.getElementById('opt_longitudinal_mode');
const navButtons=Array.from(document.querySelectorAll('[data-view]')),views=Array.from(document.querySelectorAll('.view'));
let currentJobId=null,currentPreviewPayload=null,pollTimer=null,isSubmitting=false,regionOptionSelections={},spanLongSelections={};
const parseNum=v=>{const p=Number(v);return Number.isFinite(p)?p:null},clamp=(v,mx,mn)=>Math.max(mx,Math.min(mn,v));const DEFAULT_C_RATIO=0.2,DEFAULT_MIN_BRANCHES_C=4,DEFAULT_MIN_BRANCHES_NC=2;
const payloadModule=window.StructureLabPayload||{},statusModule=window.StructureLabStatus||{},svgModule=window.StructureLabSvg||{};
if(optLongitudinalMode){optLongitudinalMode.value='span_coupled'}
function parseCsvTokens(raw){if(payloadModule.parseCsvTokens)return payloadModule.parseCsvTokens(raw);return String(raw||'').split(',').map(v=>v.trim()).filter(v=>v.length>0)}
function parsePositiveIntList(raw){if(payloadModule.parsePositiveIntList)return payloadModule.parsePositiveIntList(raw);const t=parseCsvTokens(raw);if(!t.length)return{ok:false,values:[],message:'La lista no puede estar vacia.'};const values=[];for(const token of t){const p=Number(token);if(!Number.isInteger(p)||p<=0)return{ok:false,values:[],message:`Valor invalido: ${token}. Usa enteros positivos.`};values.push(p)}return{ok:true,values,message:''}}
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
function mapBackendField(field){if(payloadModule.mapBackendField)return payloadModule.mapBackendField(field);if(!field)return null;const raw=String(field).toLowerCase();const map=[['sheet_name','sheet_name'],['region_c_ratio','region_c_ratio'],['min_branches','min_branches_c'],['fc_mpa','fc_mpa'],['fy_mpa','fy_mpa'],['width_mm','width_mm'],['height_mm','height_mm'],['d_mm','d_mm'],['d_ratio','enable_span_layout'],['clear_length_mm','enable_span_layout'],['db_bar','db_bar'],['cover_side_mm','cover_side_mm'],['cover_top_mm','cover_top_mm'],['cover_bottom_mm','cover_bottom_mm'],['frame_pairs','enable_span_layout'],['span_layout','enable_span_layout'],['optimization','enable_optimization_overrides'],['population_size','opt_population_size'],['generations','opt_generations'],['seismic_excel','seismic_excel'],['gravity_excel','gravity_excel'],['geometry_excel','geometry_excel']];for(const [t,id] of map){if(raw.includes(t))return id}return null}
function normalizeErrorPayload(payload,status){if(payloadModule.normalizeErrorPayload)return payloadModule.normalizeErrorPayload(payload,status);if(!payload||typeof payload!=='object')return{error:'request_error',message:`No fue posible completar la solicitud (HTTP ${status}).`,details:[]};if(Array.isArray(payload.details))return{error:payload.error||'request_error',message:payload.message||'Error de solicitud',details:payload.details};if(Array.isArray(payload.detail))return{error:'validation_error',message:`No fue posible completar la solicitud (HTTP ${status}).`,details:payload.detail.map(it=>({code:it.type||'validation_error',field:Array.isArray(it.loc)?it.loc[it.loc.length-1]:'',message:it.msg||'Entrada invalida',severity:'error'}))};return{error:payload.error||'request_error',message:payload.message||payload.detail||'Error de solicitud',details:[]}}
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
row.innerHTML='<summary class="span-summary"><span class="span-summary-title">Vano</span><span class="span-summary-meta"></span></summary><div class="span-body"><div class="span-head"><div class="field"><label>ID vano</label><input type="text" class="span-id" placeholder="S1" /></div><div class="field"><label>Vano sismico</label><input type="text" class="span-seismic" placeholder="190" /></div><div class="field"><label>Vano gravedad</label><input type="text" class="span-gravity" placeholder="190" /></div><div class="field"><label>Fraccion d/h</label><input type="number" class="span-d-ratio" step="0.01" min="0.01" max="1" placeholder="0.90" /></div><div class="field"><label>Apoyo izq (mm)</label><input type="number" class="span-support-left" step="1" min="0" placeholder="0" /></div><div class="field"><label>Apoyo der (mm)</label><input type="number" class="span-support-right" step="1" min="0" placeholder="0" /></div><div class="field"><label>L libre real (mm)</label><input type="number" class="span-clear-length" step="1" min="1" placeholder="auto ETABS" /></div><div class="field"><label>Accion</label><button type="button" class="mini-btn mini-btn-danger span-remove">Eliminar vano</button></div></div><div class="region-box"><div class="region-head"><strong>Regiones del vano</strong><div class="region-actions"><button type="button" class="mini-btn btn-regenerate-regions">Regenerar 3 regiones base</button><button type="button" class="mini-btn btn-add-region">Agregar region</button></div></div><p class="help">Las regiones deben cubrir continuo de 0.0 a 1.0.</p><div class="region-list"></div></div></div>';
const idIn=row.querySelector('.span-id'),sIn=row.querySelector('.span-seismic'),gIn=row.querySelector('.span-gravity'),drIn=row.querySelector('.span-d-ratio'),slIn=row.querySelector('.span-support-left'),srIn=row.querySelector('.span-support-right'),clIn=row.querySelector('.span-clear-length'),removeBtn=row.querySelector('.span-remove'),addRegionBtn=row.querySelector('.btn-add-region'),regenBtn=row.querySelector('.btn-regenerate-regions'),regionList=row.querySelector('.region-list'),summaryTitle=row.querySelector('.span-summary-title'),summaryMeta=row.querySelector('.span-summary-meta');
idIn.value=initial.id||'';sIn.value=initial.seismic||'';gIn.value=initial.gravity||'';drIn.value=Number.isFinite(initial.d_ratio)?String(initial.d_ratio):'0.90';slIn.value=Number.isFinite(initial.support_left_mm)?String(initial.support_left_mm):'';srIn.value=Number.isFinite(initial.support_right_mm)?String(initial.support_right_mm):'';clIn.value=Number.isFinite(initial.clear_length_mm)?String(initial.clear_length_mm):'';
const updateSummary=()=>{const id=(idIn.value||'').trim()||'sin ID',s=(sIn.value||'').trim()||'?',g=(gIn.value||'').trim()||'?',dr=(drIn.value||'').trim()||'0.90',sl=(slIn.value||'').trim()||'0',sr=(srIn.value||'').trim()||'0',cl=(clIn.value||'').trim();summaryTitle.textContent=`Vano ${id}`;summaryMeta.textContent=`Sismo:${s} | Gravedad:${g} | d/h:${dr} | Ap.izq:${sl} mm | Ap.der:${sr} mm | L libre real:${cl||'modelo'} mm`};
[idIn,sIn,gIn,drIn,slIn,srIn,clIn].forEach(input=>input.addEventListener('input',updateSummary));
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
const idIn=row.querySelector('.span-id'),sIn=row.querySelector('.span-seismic'),gIn=row.querySelector('.span-gravity'),drIn=row.querySelector('.span-d-ratio'),slIn=row.querySelector('.span-support-left'),srIn=row.querySelector('.span-support-right'),clIn=row.querySelector('.span-clear-length');
const spanId=(idIn.value||'').trim()||`S${index+1}`,s=(sIn.value||'').trim(),g=(gIn.value||'').trim(),drRaw=(drIn.value||'').trim(),dr=drRaw?parseNum(drRaw):null;
if(!s)errors.push({label:`Vano ${index+1}`,element:sIn,message:'Vano sismico es obligatorio.'});
if(!g)errors.push({label:`Vano ${index+1}`,element:gIn,message:'Vano gravedad es obligatorio.'});if(!drRaw)errors.push({label:`Vano ${index+1}`,element:drIn,message:'Debes ingresar fraccion d/h.'});if(drRaw&&(dr===null||dr<=0||dr>1))errors.push({label:`Vano ${index+1}`,element:drIn,message:'d/h debe estar en (0,1].'});
const slRaw=(slIn.value||'').trim(),srRaw=(srIn.value||'').trim(),clRaw=(clIn.value||'').trim();
const sl=slRaw?parseNum(slRaw):null,sr=srRaw?parseNum(srRaw):null,cl=clRaw?parseNum(clRaw):null;
if(!slRaw)errors.push({label:`Vano ${index+1}`,element:slIn,message:'Debes ingresar apoyo izquierdo (mm).'});
if(!srRaw)errors.push({label:`Vano ${index+1}`,element:srIn,message:'Debes ingresar apoyo derecho (mm).'});
if(slRaw&&(sl===null||sl<0))errors.push({label:`Vano ${index+1}`,element:slIn,message:'Apoyo izq debe ser >= 0.'});
if(srRaw&&(sr===null||sr<0))errors.push({label:`Vano ${index+1}`,element:srIn,message:'Apoyo der debe ser >= 0.'});
if(clRaw&&(cl===null||cl<=0))errors.push({label:`Vano ${index+1}`,element:clIn,message:'L libre real debe ser > 0.'});
const regions=parseRegionRowsStrict(row,index+1,errors);
spans.push({id:spanId,seismic:s,gravity:g,d_ratio:dr,support_left_mm:sl,support_right_mm:sr,clear_length_mm:cl,regions})
});
return spans
}
function collectSpanLayoutPreview(){if(!enableSpanLayout.checked)return[];const rows=Array.from(spanLayoutList.querySelectorAll('.span-row'));if(!rows.length)return[];const minC=DEFAULT_MIN_BRANCHES_C,minNC=DEFAULT_MIN_BRANCHES_NC;return rows.map((row,index)=>{const spanId=(row.querySelector('.span-id').value||'').trim()||`S${index+1}`,s=(row.querySelector('.span-seismic').value||'').trim()||spanId,g=(row.querySelector('.span-gravity').value||'').trim()||s,dr=parseNum(row.querySelector('.span-d-ratio').value),sl=parseNum(row.querySelector('.span-support-left').value),sr=parseNum(row.querySelector('.span-support-right').value),cl=parseNum(row.querySelector('.span-clear-length').value);const regionRows=Array.from(row.querySelectorAll('.region-row')),regions=[];for(let i=0;i<regionRows.length;i++){const rr=regionRows[i],fromV=parseNum(rr.querySelector('.region-from').value),toV=parseNum(rr.querySelector('.region-to').value);if(fromV===null||toV===null||fromV<0||toV>1||fromV>=toV)continue;const type=rr.querySelector('.region-confined').checked?'C':'NC',mbRaw=parseNum(rr.querySelector('.region-min-branches').value);regions.push({id:(rr.querySelector('.region-id').value||'').trim()||`R${i+1}`,from:fromV,to:toV,type,min_branches:Number.isInteger(mbRaw)&&mbRaw>=1?mbRaw:(type==='C'?minC:minNC),spacing_mm:type==='C'?100:200})}const ordered=[...regions].sort((a,b)=>a.from-b.from);let valid=ordered.length>0;if(valid){const tol=1e-9;if(Math.abs(ordered[0].from-0)>tol||Math.abs(ordered[ordered.length-1].to-1)>tol)valid=false;else{let cur=0;for(const rg of ordered){if(Math.abs(rg.from-cur)>tol){valid=false;break}cur=rg.to}}}const effective=valid?ordered:defaultRegionTemplate(DEFAULT_C_RATIO);return{id:spanId,seismic:s,gravity:g,d_ratio:Number.isFinite(dr)&&dr>0&&dr<=1?dr:0.9,support_left_mm:Number.isFinite(sl)&&sl>=0?sl:0,support_right_mm:Number.isFinite(sr)&&sr>=0?sr:0,clear_length_mm:Number.isFinite(cl)&&cl>0?cl:null,regions:effective}})}
function buildAdvancedPayload(){
hiddenFramePairsInput.value='';hiddenOptimizationInput.value='';hiddenSpanLayoutInput.value='';const errors=[];
if(enableSpanLayout.checked){const spans=collectSpanLayoutStrict(errors);if(!errors.length){hiddenSpanLayoutInput.value=JSON.stringify(spans.map(s=>({id:s.id,seismic:s.seismic,gravity:s.gravity,d_ratio:s.d_ratio,support_left_mm:s.support_left_mm,support_right_mm:s.support_right_mm,clear_length_mm:s.clear_length_mm,regions:s.regions})));hiddenFramePairsInput.value=JSON.stringify(spans.map(s=>({id:s.id,seismic:s.seismic,gravity:s.gravity})))}}
if(enableOptimizationOverrides.checked){const genRaw=(optGenerations.value||'').trim(),gen=Number(genRaw),popRaw=(optPopulationSize&&optPopulationSize.value||'').trim(),pop=Number(popRaw),longModeRaw=String((optLongitudinalMode&&optLongitudinalMode.value)||'span_coupled').trim(),longMode=longModeRaw||'span_coupled';if(!genRaw)errors.push({label:'Generaciones',element:optGenerations,message:'Indica la cantidad de generaciones.'});else if(!Number.isInteger(gen)||gen<1)errors.push({label:'Generaciones',element:optGenerations,message:'Debe ser un entero >= 1.'});if(!popRaw)errors.push({label:'Tamano de poblacion',element:optPopulationSize,message:'Indica el tamano de poblacion.'});else if(!Number.isInteger(pop)||pop<4)errors.push({label:'Tamano de poblacion',element:optPopulationSize,message:'Debe ser un entero >= 4.'});if(!['legacy_region_independent','span_coupled'].includes(longMode))errors.push({label:'Modo longitudinal',element:optLongitudinalMode,message:'Selecciona un modo longitudinal valido.'});const eb=parseCsvTokens(optEBars.value),gb=parseCsvTokens(optGBars.value),lb=parseCsvTokens(optLongBars.value);if(!eb.length)errors.push({label:'Estribos cerrados',element:optEBars,message:'Define al menos un diametro.'});if(!gb.length)errors.push({label:'Ramas simples',element:optGBars,message:'Define al menos un diametro.'});if(!lb.length)errors.push({label:'Refuerzo longitudinal',element:optLongBars,message:'Define al menos un diametro.'});const sp=parsePositiveIntList(optSpacing.value),lc=parsePositiveIntList(optLongCounts.value);if(!sp.ok)errors.push({label:'Espaciamientos',element:optSpacing,message:sp.message});if(!lc.ok)errors.push({label:'Cantidades longitudinales',element:optLongCounts,message:lc.message});if(!errors.length)hiddenOptimizationInput.value=JSON.stringify({longitudinal_mode:longMode,variables:{E_bars:eb,G_bars:gb,stirrup_spacing_mm:sp.values,longitudinal_bars:lb,longitudinal_bar_counts:lc.values},genetic_algorithm:{population_size:pop,generations:gen}})}else if(enableSpanLayout.checked){hiddenOptimizationInput.value=JSON.stringify({longitudinal_mode:'span_coupled'})}
if(errors.length){renderUiValidationErrors(errors);return false}
return true
}
const defaultSpacing=t=>String(t||'').toUpperCase()==='C'?100:200;
function fallbackRegionLabels(region,dbBar){const minB=Number(region.min_branches)||(region.type==='C'?4:2),gCount=Math.max(minB-2,0),spacing=Number(region.spacing_mm)||defaultSpacing(region.type),gText=gCount>0?` + ${gCount}G #3`:'';return{transverse:`1E #3${gText} @ ${Math.round(spacing)} mm`,longitudinal:`4${dbBar}`}}
function collectFallback(){
const defaultRatio=DEFAULT_C_RATIO,dbBar=(document.getElementById('db_bar').value||'#6').trim()||'#6',layout=collectSpanLayoutPreview(),defaultWidth=parseNum(document.getElementById('width_mm').value)||300,defaultHeight=parseNum(document.getElementById('height_mm').value)||600,spans=[];
if(layout.length){
layout.forEach((span,i)=>{
const spanWidth=Math.max(1,Number(span.width_mm)||defaultWidth),spanHeight=Math.max(1,Number(span.height_mm)||defaultHeight),spanDRatio=Math.min(1,Math.max(0.01,Number(span.d_ratio)||0.9));
const clearLen=Number(span.clear_length_mm),hasClearLen=Number.isFinite(clearLen)&&clearLen>0,baseLen=hasClearLen?clearLen:6000;
const regions=(span.regions||[]).map((region,j)=>{const lengthMm=Math.max(1,Math.round(baseLen*(region.to-region.from))),labels=fallbackRegionLabels(region,dbBar);return{region_id:region.id||`R${j+1}`,type:String(region.type||'NC').toUpperCase(),from:region.from,to:region.to,length_mm:lengthMm,length_estimated:!hasClearLen,spacing_mm:Number(region.spacing_mm)||defaultSpacing(region.type),spacing_estimated:true,transverse_label:labels.transverse,longitudinal_label:labels.longitudinal}});
const spanLength=regions.reduce((a,r)=>a+(Number(r.length_mm)||0),0)||Math.round(baseLen);
spans.push({span_id:span.id||`S${i+1}`,seismic:span.seismic,gravity:span.gravity,d_ratio:spanDRatio,d_mm:Math.round(spanHeight*spanDRatio),width_mm:Math.round(spanWidth),height_mm:Math.round(spanHeight),support_left_mm:Math.max(0,Math.round(Number(span.support_left_mm)||0)),support_right_mm:Math.max(0,Math.round(Number(span.support_right_mm)||0)),clear_length_mm:hasClearLen?Math.round(clearLen):null,length_mm:spanLength,length_estimated:!hasClearLen,regions})
})
}
if(!spans.length){const base=defaultRegionTemplate(defaultRatio).map(region=>{const labels=fallbackRegionLabels(region,dbBar);return{region_id:region.id,type:region.type,from:region.from,to:region.to,length_mm:Math.max(1,Math.round(6000*(region.to-region.from))),length_estimated:true,spacing_mm:region.spacing_mm,spacing_estimated:true,transverse_label:labels.transverse,longitudinal_label:labels.longitudinal}});spans.push({span_id:'S1',seismic:'S1',gravity:'S1',d_ratio:0.9,d_mm:Math.round(defaultHeight*0.9),width_mm:Math.round(defaultWidth),height_mm:Math.round(defaultHeight),support_left_mm:0,support_right_mm:0,clear_length_mm:null,length_mm:6000,length_estimated:true,regions:base})}
const totalSpanMm=spans.reduce((a,s)=>a+(Number(s.length_mm)||0),0),totalSupportMm=spans.reduce((a,s)=>a+(Number(s.support_right_mm)||0),0),maxHeight=spans.reduce((m,s)=>Math.max(m,Number(s.height_mm)||0),0),maxWidth=spans.reduce((m,s)=>Math.max(m,Number(s.width_mm)||0),0);return{totalSpanMm,totalSupportMm,totalSystemMm:totalSpanMm+totalSupportMm,totalSpanEstimated:spans.some(s=>!!s.length_estimated),beamDepthMm:maxHeight||defaultHeight,beamWidthMm:maxWidth||defaultWidth,beamId:(document.getElementById('beam_id').value||'B1').trim()||'B1',detailing:(document.getElementById('detailing').value||'DMO').trim()||'DMO',fcMpa:parseNum(document.getElementById('fc_mpa').value)||28,fyMpa:parseNum(document.getElementById('fy_mpa').value)||420,spans,dataSource:'fallback'}
}
function buildBeamData(source){
const fb=collectFallback(),pp=source&&source.previewPayload;
if(!pp||!Array.isArray(pp.spans)||!pp.spans.length)return fb;
const beam=pp.beam||{},spans=pp.spans.map((sp,i)=>({
span_id:sp.span_id||`S${i+1}`,
seismic:sp.seismic||'',
gravity:sp.gravity||'',
d_mm:parseNum(sp.d_mm),
width_mm:parseNum(sp.width_mm),
height_mm:parseNum(sp.height_mm),
support_left_mm:parseNum(sp.support_left_mm)||0,
support_right_mm:parseNum(sp.support_right_mm)||0,
length_mm:parseNum(sp.length_mm)||6000,
length_estimated:!!sp.length_estimated,
regions:Array.isArray(sp.regions)?sp.regions.map((rg,j)=>{
const regionId=rg.region_id||`R${j+1}`;
const spanId=sp.span_id||`S${i+1}`;
const key=`${spanId}__${regionId}`;
const saved=regionOptionSelections[key]||{};
const transverseLabel=saved.transverse_label||rg.transverse_label||`${String(rg.type||'NC').toUpperCase()} @ ${parseNum(rg.spacing_mm)||defaultSpacing(rg.type)} mm`;
const longitudinalLabel=saved.longitudinal_label||rg.longitudinal_label||'long. n/d';
return({
region_id:regionId,
type:String(rg.type||'NC').toUpperCase(),
from:parseNum(rg.from),
to:parseNum(rg.to),
length_mm:parseNum(rg.length_mm)||1,
length_estimated:!!rg.length_estimated,
spacing_mm:parseNum(rg.spacing_mm)||defaultSpacing(rg.type),
spacing_estimated:!!rg.spacing_estimated,
transverse_label:transverseLabel,
longitudinal_label:longitudinalLabel,
selected_option:parseNum(rg.selected_option),
best_option:parseNum(rg.best_option),
best_weight_kg:parseNum(rg.best_weight_kg),
selected_weight_kg:parseNum(rg.selected_weight_kg),
options:Array.isArray(rg.options)?rg.options.map((opt,k)=>(
{
option:parseNum(opt.option)||k+1,
transverse_label:String(opt.transverse_label||''),
longitudinal_label:String(opt.longitudinal_label||''),
weight_transverse_kg:parseNum(opt.weight_transverse_kg),
weight_longitudinal_kg:parseNum(opt.weight_longitudinal_kg),
weight_total_kg:parseNum(opt.weight_total_kg),
})):[],
});
}):[],
}));
const total=spans.reduce((a,s)=>a+(parseNum(s.length_mm)||0),0),supp=spans.reduce((a,s)=>a+(parseNum(s.support_right_mm)||0),0),maxHeight=spans.reduce((m,s)=>Math.max(m,parseNum(s.height_mm)||0),0),maxWidth=spans.reduce((m,s)=>Math.max(m,parseNum(s.width_mm)||0),0);
return{totalSpanMm:parseNum(pp.total_span_mm)||total||fb.totalSpanMm,totalSupportMm:parseNum(pp.total_support_mm)||supp,totalSystemMm:parseNum(pp.total_system_mm)||((parseNum(pp.total_span_mm)||total||fb.totalSpanMm)+(parseNum(pp.total_support_mm)||supp)),totalSpanEstimated:!!pp.total_span_estimated,beamDepthMm:parseNum(beam.height_mm)||maxHeight||fb.beamDepthMm,beamWidthMm:parseNum(beam.width_mm)||maxWidth||fb.beamWidthMm,beamId:beam.beam_id||fb.beamId,detailing:beam.detailing||fb.detailing,fcMpa:parseNum(beam.fc_mpa)||fb.fcMpa,fyMpa:parseNum(beam.fy_mpa)||fb.fyMpa,spans,dataSource:'preview'}
}
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
const secW=Math.max(1,Math.round(Number(sp.width_mm)||Number(d.beamWidthMm)||300));
const secH=Math.max(1,Math.round(Number(sp.height_mm)||Number(d.beamDepthMm)||600));
if(showSpanId){
spanLabels+=`<text x="${(spanStart+spanW/2).toFixed(2)}" y="101" text-anchor="middle" font-size="${spanIdFont}" fill="#1b3552" font-weight="620">${spanId}</text><text x="${(spanStart+spanW/2).toFixed(2)}" y="116" text-anchor="middle" font-size="10.5" fill="#2a4968" font-weight="600">${secW} x ${secH} mm</text>`;
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
function renderBeam(container,data){const svgBuilder=svgModule.buildBeamElevationSvg||buildBeamElevationSvg;container.innerHTML=svgBuilder(data);beamElevationLegend.textContent=data.dataSource==='preview'?'Dibujo alimentado por datos reales de job/optimizacion.':'Se usan datos de fallback (estimados) hasta obtener preview del job.'}
function syncBeamPreviewWithSelections(){
const data=buildBeamData({previewPayload:currentPreviewPayload});
renderBeam(beamElevationContainer,data);
}
function fmtKg(value){if(statusModule.fmtKg)return statusModule.fmtKg(value);const num=Number(value);return Number.isFinite(num)?`${num.toFixed(2)} kg`:'n/d'}
function fmtPct(value){if(statusModule.fmtPct)return statusModule.fmtPct(value);const num=Number(value);return Number.isFinite(num)?`${num.toFixed(2)} %`:'n/d'}
function fmtStirrupCount(value){const count=Number(value);if(!Number.isFinite(count)||count<0)return'n/d';const rounded=Math.round(count);return rounded===1?'1 estribo':`${rounded} estribos`}
function formatTransverseOptionText(opt){const label=String(opt&&opt.label||'').trim();const count=fmtStirrupCount(opt&&opt.stirrup_count);const countPart=count&&count!=='n/d'?` | ${count}`:'';return`${label}${countPart} | ${fmtKg(opt&&opt.weight_kg)}`}
function uniqueLabelOptions(options,labelKey,weightKey,maxItems=10){const map={};(options||[]).forEach(opt=>{const label=String(opt&&opt[labelKey]||'').trim();if(!label)return;const raw=Number(opt&&opt[weightKey]);const weight=Number.isFinite(raw)?raw:0;const current=map[label];if(!current||weight<current.weight_kg)map[label]={label,weight_kg:weight}});const ordered=Object.values(map).sort((a,b)=>a.weight_kg-b.weight_kg);if(Number.isInteger(maxItems)&&maxItems>0)return ordered.slice(0,maxItems);return ordered}
function buildLongArrangementLabel(bar,count,emptyLabel=''){const b=String(bar||'').trim();const c=Number(count);if(!b||!Number.isFinite(c)||c<=0)return emptyLabel;return `${Math.round(c)} x ${b}`}
function normalizeAdditionalLabel(value){const label=String(value||'').trim();return label||'no se requiere'}
function normalizeMatchLabel(value){return String(value||'').trim().toLowerCase().replace(/\s+/g,' ')}
function applyBackendDefaultSelection(previewPayload){
const def=previewPayload&&previewPayload.default_selection&&typeof previewPayload.default_selection==='object'?previewPayload.default_selection:null;
if(!def)return;
const spanRows=Array.isArray(def.spans)?def.spans:[];
spanRows.forEach(sp=>{
const spanId=String(sp&&sp.span_id||'').trim();
if(!spanId)return;
const spanSetValue=String(sp&&sp.span_option_set_value||'').trim();
const baseValue=String(sp&&sp.base_value||'').trim();
const baseLabel=String(sp&&sp.base_label||'').trim();
if(spanSetValue)spanLongSelections[spanId]={mode:'set',value:spanSetValue,option:Number.isFinite(Number(sp&&sp.option))?Number(sp.option):null};
else if(baseValue||baseLabel)spanLongSelections[spanId]={mode:'custom',value:baseValue,label:baseLabel,option:Number.isFinite(Number(sp&&sp.option))?Number(sp.option):null};
const regions=Array.isArray(sp&&sp.regions)?sp.regions:[];
regions.forEach(rg=>{
const regionId=String(rg&&rg.region_id||'').trim();
if(!regionId)return;
const key=`${spanId}__${regionId}`;
regionOptionSelections[key]={
transverse_label:String(rg&&rg.transverse_label||'').trim(),
longitudinal_label:String(rg&&rg.longitudinal_label||'').trim(),
base_longitudinal_label:String(rg&&rg.base_longitudinal_label||baseLabel||'').trim(),
additional_longitudinal_label:normalizeAdditionalLabel(rg&&rg.additional_longitudinal_label),
additional_value:'',
option:Number.isFinite(Number(rg&&rg.option))?Number(rg.option):null,
};
});
});
}
function getAdditionalOptionsByBaseValue(region,baseValue){
const key=String(baseValue||'').trim();
if(!key)return[];
const map=region&&region.additionalOptionsByBase&&typeof region.additionalOptionsByBase==='object'?region.additionalOptionsByBase:{};
const rows=Array.isArray(map[key])?map[key]:[];
if(!rows.length)return[];
const parsed=rows.map((row,index)=>{
const label=normalizeAdditionalLabel(row&&row.label);
const longLabel=String(row&&row.longitudinal_label||'').trim()||label;
const parsedWeight=Number(row&&row.weight_kg);
const parsedLongTotal=Number(row&&row.weight_longitudinal_total_kg);
const parsedBaseRegion=Number(row&&row.weight_base_region_kg);
const weight=label==='no se requiere'?0:(Number.isFinite(parsedWeight)?parsedWeight:0);
const baseRegionWeight=Number.isFinite(parsedBaseRegion)?parsedBaseRegion:0;
const longitudinalTotalWeightKg=Number.isFinite(parsedLongTotal)?parsedLongTotal:(baseRegionWeight+weight);
const option=Number.isFinite(Number(row&&row.option))?Number(row.option):null;
const value=String(row&&row.value||`add_${option!==null?option:index+1}_${label.replace(/\s+/g,'_')}`).trim();
return{value,label,longitudinal_label:longLabel,weight_kg:weight,weight_base_region_kg:baseRegionWeight,longitudinal_total_weight_kg:longitudinalTotalWeightKg,option};
}).filter(opt=>opt.value&&opt.label);
return parsed.sort((a,b)=>{if(a.weight_kg!==b.weight_kg)return a.weight_kg-b.weight_kg;return (a.option||0)-(b.option||0);}).slice(0,10);
}
function normalizeSpanBaseOptions(spanPayload){
const raw=spanPayload&&Array.isArray(spanPayload.longitudinal_base_options)?spanPayload.longitudinal_base_options:[];
const parsed=raw.map((opt,index)=>{
const option=Number.isFinite(Number(opt&&opt.option))?Number(opt.option):null;
const value=String(opt&&opt.value||`base_${option!==null?option:index+1}`).trim();
const baseLabel=String(opt&&opt.base_label||'no se requiere').trim()||'no se requiere';
const longWeightRaw=Number(opt&&opt.long_weight_kg);
const fallbackWeightRaw=Number(opt&&opt.weight_kg);
const totalWeightRaw=Number(opt&&opt.total_weight_kg);
const weightKg=Number.isFinite(longWeightRaw)?longWeightRaw:(Number.isFinite(fallbackWeightRaw)?fallbackWeightRaw:0);
const totalWeightKg=Number.isFinite(totalWeightRaw)?totalWeightRaw:weightKg;
return{value,option,base_label:baseLabel,weight_kg:weightKg,total_weight_kg:totalWeightKg};
}).filter(opt=>opt.value&&opt.base_label);
return parsed.sort((a,b)=>{if(a.total_weight_kg!==b.total_weight_kg)return a.total_weight_kg-b.total_weight_kg;if(a.weight_kg!==b.weight_kg)return a.weight_kg-b.weight_kg;return (a.option||0)-(b.option||0);}).slice(0,10);
}
function normalizeSpanLongitudinalOptionSets(spanPayload,regionRows){
const raw=spanPayload&&Array.isArray(spanPayload.span_longitudinal_option_sets)?spanPayload.span_longitudinal_option_sets:[];
if(!raw.length)return[];
const regionIds=new Set((regionRows||[]).map(r=>String(r&&r.regionId||'').trim()).filter(Boolean));
const parsed=raw.map((item,index)=>{
const option=Number.isFinite(Number(item&&item.option))?Number(item.option):null;
const value=String(item&&item.value||`longset_${option!==null?option:index+1}`).trim();
const baseLabel=String(item&&item.base_label||'no se requiere').trim()||'no se requiere';
const baseValue=String(item&&item.base_value||'').trim();
const totalRaw=Number(item&&item.total_weight_kg);
const longTotalRaw=Number(item&&item.total_longitudinal_weight_kg);
const transTotalRaw=Number(item&&item.total_transverse_weight_kg);
const rankRaw=Number(item&&item.rank);
const rows=Array.isArray(item&&item.regions)?item.regions:[];
const region_map={};
let sumTotal=0;
let sumLong=0;
let sumTrans=0;
rows.forEach(r=>{
const regionId=String(r&&r.region_id||'').trim();
if(!regionId)return;
const additionalLabel=normalizeAdditionalLabel(r&&r.additional_label);
const longLabel=String(r&&r.longitudinal_label||additionalLabel).trim()||additionalLabel;
const transLabel=String(r&&r.transverse_label||'').trim();
const totalW=Number(r&&r.weight_total_kg);
const longW=Number(r&&r.weight_longitudinal_kg);
const transW=Number(r&&r.weight_transverse_kg);
const addW=Number(r&&r.weight_additional_kg);
const baseW=Number(r&&r.weight_base_region_kg);
const weightLong=Number.isFinite(longW)?longW:((Number.isFinite(baseW)?baseW:0)+(Number.isFinite(addW)?addW:0));
const weightTrans=Number.isFinite(transW)?transW:0;
const weightTotal=Number.isFinite(totalW)?totalW:(weightLong+weightTrans);
sumTotal+=weightTotal;
sumLong+=weightLong;
sumTrans+=weightTrans;
region_map[regionId]={transverse_label:transLabel,additional_label:additionalLabel,longitudinal_label:longLabel,weight_total_kg:weightTotal,weight_transverse_kg:weightTrans,weight_longitudinal_kg:weightLong,weight_additional_kg:Number.isFinite(addW)?addW:0,weight_base_region_kg:Number.isFinite(baseW)?baseW:0};
});
const missing=[...regionIds].some(id=>!region_map[id]);
if(missing)return null;
const total=Number.isFinite(totalRaw)?totalRaw:sumTotal;
const totalLong=Number.isFinite(longTotalRaw)?longTotalRaw:sumLong;
const totalTrans=Number.isFinite(transTotalRaw)?transTotalRaw:sumTrans;
const rank=Number.isFinite(rankRaw)&&rankRaw>0?Math.round(rankRaw):(index+1);
return{value,option,rank,base_label:baseLabel,base_value:baseValue,total_weight_kg:total,total_longitudinal_weight_kg:totalLong,total_transverse_weight_kg:totalTrans,region_map};
}).filter(Boolean).sort((a,b)=>{if(a.total_longitudinal_weight_kg!==b.total_longitudinal_weight_kg)return a.total_longitudinal_weight_kg-b.total_longitudinal_weight_kg;if(a.total_weight_kg!==b.total_weight_kg)return a.total_weight_kg-b.total_weight_kg;return (a.option||0)-(b.option||0);});
return parsed.slice(0,10);
}
function normalizeSpanOptionChoices(spanPayload){
const raw=spanPayload&&Array.isArray(spanPayload.span_option_choices)?spanPayload.span_option_choices:[];
if(!raw.length)return[];
const parsed=raw.map((item,index)=>{
const option=Number.isFinite(Number(item&&item.option))?Number(item.option):(index+1);
const total=Number(item&&item.total_weight_kg);
const longTotal=Number(item&&item.long_weight_kg);
return{option,total_weight_kg:Number.isFinite(total)?total:Number.POSITIVE_INFINITY,long_weight_kg:Number.isFinite(longTotal)?longTotal:0};
}).filter(item=>Number.isFinite(item.option)&&item.option>0&&Number.isFinite(item.total_weight_kg));
parsed.sort((a,b)=>{if(a.total_weight_kg!==b.total_weight_kg)return a.total_weight_kg-b.total_weight_kg;return a.option-b.option;});
return parsed.slice(0,10);
}

function renderRegionOptions(previewPayload){
if(!regionOptionsEl)return;
if(selectionSaveMsg)selectionSaveMsg.textContent='';
if(saveSelectionBtn)saveSelectionBtn.disabled=true;
const spans=previewPayload&&Array.isArray(previewPayload.spans)?previewPayload.spans:[];
const hasSavedSelections=Object.keys(regionOptionSelections||{}).length>0||Object.keys(spanLongSelections||{}).length>0;
if(!hasSavedSelections&&previewPayload)applyBackendDefaultSelection(previewPayload);
const spanBuckets=[];

spans.forEach((sp,sIndex)=>{
const spanId=sp.span_id||`S${sIndex+1}`;
const regions=Array.isArray(sp.regions)?sp.regions:[];
const regionRows=[];
regions.forEach((rg,rIndex)=>{
const regionId=rg.region_id||`R${rIndex+1}`;
const longModeRaw=String(rg.longitudinal_mode||'').trim().toLowerCase();
const optionLimit=longModeRaw==='span_coupled'?2000:10;
const optionsRaw=Array.isArray(rg.options)?rg.options:[];
const options=optionsRaw.map((opt,optIndex)=>{
const baseLabel=String(opt.base_longitudinal_label||buildLongArrangementLabel(opt.base_long_bar,opt.base_long_count,'no se requiere')).trim()||'no se requiere';
const additionalLabel=normalizeAdditionalLabel(opt.additional_longitudinal_label||buildLongArrangementLabel(opt.extra_long_bar,opt.extra_long_count,''));
return{
option:Number.isFinite(Number(opt.option))?Number(opt.option):optIndex+1,
transverse_label:String(opt.transverse_label||'').trim(),
longitudinal_label:String(opt.longitudinal_label||'').trim(),
base_longitudinal_label:baseLabel,
additional_longitudinal_label:additionalLabel,
base_long_bar:String(opt.base_long_bar||'').trim(),
base_long_count:Number.isFinite(Number(opt.base_long_count))?Number(opt.base_long_count):null,
extra_long_bar:String(opt.extra_long_bar||'').trim(),
extra_long_count:Number.isFinite(Number(opt.extra_long_count))?Number(opt.extra_long_count):null,
weight_total_kg:Number.isFinite(Number(opt.weight_total_kg))?Number(opt.weight_total_kg):0,
weight_transverse_kg:Number.isFinite(Number(opt.weight_transverse_kg))?Number(opt.weight_transverse_kg):0,
weight_longitudinal_kg:Number.isFinite(Number(opt.weight_longitudinal_kg))?Number(opt.weight_longitudinal_kg):0,
};
}).sort((a,b)=>{const aw=Number.isFinite(Number(a.weight_total_kg))?Number(a.weight_total_kg):Number.POSITIVE_INFINITY;const bw=Number.isFinite(Number(b.weight_total_kg))?Number(b.weight_total_kg):Number.POSITIVE_INFINITY;if(aw!==bw)return aw-bw;return (Number(a.option)||0)-(Number(b.option)||0)}).slice(0,optionLimit);
if(!options.length)return;
const best=options[0];
const transOptionsSource=(Array.isArray(rg.transverse_options)?rg.transverse_options:[]).map(opt=>({label:String(opt&&opt.label||'').trim(),weight_kg:Number.isFinite(Number(opt&&opt.weight_kg))?Number(opt.weight_kg):0,stirrup_count:Number.isFinite(Number(opt&&opt.stirrup_count))?Number(opt.stirrup_count):null,stirrup_unit_weight_kg:Number.isFinite(Number(opt&&opt.stirrup_unit_weight_kg))?Number(opt.stirrup_unit_weight_kg):null,})).filter(opt=>opt.label).sort((a,b)=>{const aw=Number.isFinite(Number(a.weight_kg))?Number(a.weight_kg):Number.POSITIVE_INFINITY;const bw=Number.isFinite(Number(b.weight_kg))?Number(b.weight_kg):Number.POSITIVE_INFINITY;if(aw!==bw)return aw-bw;return String(a.label).localeCompare(String(b.label));});
const longOptionsSource=(Array.isArray(rg.longitudinal_options)?rg.longitudinal_options:[]).map(opt=>({label:String(opt&&opt.label||'').trim(),weight_kg:Number.isFinite(Number(opt&&opt.weight_kg))?Number(opt.weight_kg):0,})).filter(opt=>opt.label);
const transOptions=transOptionsSource.length?transOptionsSource:uniqueLabelOptions(options,'transverse_label','weight_transverse_kg',10);
const longOptions=longOptionsSource.length?longOptionsSource:uniqueLabelOptions(options,'longitudinal_label','weight_longitudinal_kg',10);
if(!transOptions.length||!longOptions.length)return;
const longLookup={};
longOptions.forEach(opt=>{longLookup[opt.label]=opt});
regionRows.push({
key:`${spanId}__${regionId}`,
spanId,
regionId,
bestOption:best.option,
bestWeight:Number(best.weight_total_kg)||0,
transOptions,
longOptions,
longLookup,
defaultTrans:String(best.transverse_label||transOptions[0].label||'').trim()||transOptions[0].label,
options,
longMode:longModeRaw,
defaultLong:String(best.longitudinal_label||longOptions[0].label||'').trim(),
defaultBaseLong:String(best.base_longitudinal_label||'no se requiere').trim()||'no se requiere',
defaultAdditionalLong:normalizeAdditionalLabel(best.additional_longitudinal_label),
referenceBestWeight:Number(best.weight_total_kg)||0,
additionalOptionsByBase:(rg&&typeof rg.additional_options_by_base==='object'&&rg.additional_options_by_base)?rg.additional_options_by_base:{},
});
});
if(!regionRows.length)return;

const isSpanCoupled=regionRows.some(region=>region.longMode==='span_coupled');
if(isSpanCoupled){
const spanBaseOptions=normalizeSpanBaseOptions(sp);
if(!spanBaseOptions.length)return;
const spanLongOptionSets=normalizeSpanLongitudinalOptionSets(sp,regionRows);
const spanOptionChoices=normalizeSpanOptionChoices(sp);
const backendDefaultSetValue=String(sp.default_longitudinal_option_set_value||'').trim();
const defaultSet=spanLongOptionSets.find(opt=>String(opt.value)===backendDefaultSetValue)||spanLongOptionSets[0]||null;
if(defaultSet&&defaultSet.region_map){
regionRows.forEach(region=>{
const preset=defaultSet.region_map[region.regionId];
if(!preset)return;
const preferredTrans=String(preset.transverse_label||'').trim();
const preferredLong=String(preset.longitudinal_label||'').trim();
if(preferredTrans&&region.transOptions.some(opt=>opt.label===preferredTrans))region.defaultTrans=preferredTrans;
if(preferredLong&&region.longOptions.some(opt=>opt.label===preferredLong))region.defaultLong=preferredLong;
region.defaultBaseLong=String(defaultSet.base_label||region.defaultBaseLong||'no se requiere').trim()||'no se requiere';
region.defaultAdditionalLong=normalizeAdditionalLabel(preset.additional_label||region.defaultAdditionalLong);
const rowWeight=Number(preset.weight_total_kg);
if(Number.isFinite(rowWeight)&&rowWeight>0)region.referenceBestWeight=rowWeight;
});
}
const defaultBaseFromSet=defaultSet?String(defaultSet.base_label||'').trim():'';
const defaultBaseBySet=defaultBaseFromSet?spanBaseOptions.find(opt=>String(opt.base_label||'').trim()===defaultBaseFromSet):null;
const backendDefaultBaseValue=String(sp.default_longitudinal_base_value||'').trim();
const defaultSpanBaseValue=defaultBaseBySet?defaultBaseBySet.value:(spanBaseOptions.some(opt=>opt.value===backendDefaultBaseValue)?backendDefaultBaseValue:spanBaseOptions[0].value);
const defaultSpanLongSetValue=defaultSet?defaultSet.value:(spanLongOptionSets.some(opt=>opt.value===backendDefaultSetValue)?backendDefaultSetValue:'__custom__');
spanBuckets.push({spanId,regions:regionRows,isSpanCoupled:true,spanBaseOptions,defaultSpanBaseValue,spanLongOptionSets,defaultSpanLongSetValue,spanOptionChoices,defaultSpanOptionNumber:null});
return;
}

let commonLongLabels=regionRows[0].longOptions.map(opt=>opt.label);
for(let i=1;i<regionRows.length;i+=1){const labels=new Set(regionRows[i].longOptions.map(opt=>opt.label));commonLongLabels=commonLongLabels.filter(label=>labels.has(label));}
let hasCommonLong=commonLongLabels.length>0;
let spanLongOptions=[];
if(hasCommonLong){spanLongOptions=commonLongLabels.map(label=>({label,weight_kg:regionRows.reduce((acc,region)=>acc+(Number((region.longLookup[label]||{}).weight_kg)||0),0)})).sort((a,b)=>a.weight_kg-b.weight_kg).slice(0,10);}
if(!spanLongOptions.length){
hasCommonLong=false;
const unionMap={};
regionRows.forEach(region=>{region.longOptions.forEach(opt=>{if(!unionMap[opt.label])unionMap[opt.label]={label:opt.label,weight_kg:0,coverage:0};unionMap[opt.label].weight_kg+=Number(opt.weight_kg)||0;unionMap[opt.label].coverage+=1;});});
spanLongOptions=Object.values(unionMap).sort((a,b)=>{if(b.coverage!==a.coverage)return b.coverage-a.coverage;if(a.weight_kg!==b.weight_kg)return a.weight_kg-b.weight_kg;return String(a.label).localeCompare(String(b.label));}).slice(0,10);
}
if(!spanLongOptions.length)return;
spanBuckets.push({spanId,regions:regionRows,spanLongOptions,defaultSpanLong:spanLongOptions[0].label,hasCommonLong,isSpanCoupled:false});
});

if(!spanBuckets.length){regionOptionsEl.innerHTML='<p class="help">No hay alternativas de seleccion disponibles por vano/region para este job.</p>';return;}

regionOptionsEl.innerHTML='';
const summary=document.createElement('div');
summary.className='region-opt-summary';
regionOptionsEl.appendChild(summary);
const states=[];
const optimalBeamWeight=Number(previewPayload&&previewPayload.optimal_beam_weight_kg);
const updateSummary=()=>{const fallbackBestSum=states.reduce((acc,item)=>acc+(Number.isFinite(item.best)?item.best:0),0);const bestSum=Number.isFinite(optimalBeamWeight)?optimalBeamWeight:fallbackBestSum;const hasInvalidSelection=states.some(item=>!Number.isFinite(item.selected));if(hasInvalidSelection){summary.innerHTML=`Peso opcion optima (viga completa): <strong>${fmtKg(bestSum)}</strong> | Peso opcion seleccionada (viga completa): <strong>n/d</strong> | Diferencia: <strong>n/d</strong> | <strong>Seleccion inconsistente</strong>`;if(saveSelectionBtn)saveSelectionBtn.disabled=true;return;}const selectedSum=states.reduce((acc,item)=>acc+(Number.isFinite(item.selected)?item.selected:0),0);const pct=bestSum>0?((selectedSum-bestSum)/bestSum)*100:null;summary.innerHTML=`Peso opcion optima (viga completa): <strong>${fmtKg(bestSum)}</strong> | Peso opcion seleccionada (viga completa): <strong>${fmtKg(selectedSum)}</strong> | Diferencia: <strong>${fmtPct(pct)}</strong>`;if(saveSelectionBtn)saveSelectionBtn.disabled=!currentJobId;};

spanBuckets.forEach((bucket,bIndex)=>{
const details=document.createElement('details');
details.className='span-row region-opt-span';
details.open=bIndex===0;
details.innerHTML=`<summary class="span-summary"><span class="span-summary-title">Vano ${bucket.spanId}</span><span class="span-summary-meta">${bucket.regions.length} regiones con alternativas</span></summary><div class="span-body"></div>`;
const body=details.querySelector('.span-body');
const spanCard=document.createElement('div');
spanCard.className='region-opt-card';
let spanLongSelect=null;
let spanSetSelect=null;

if(bucket.isSpanCoupled){
spanCard.innerHTML=`<div class="region-opt-head"><strong>Vano ${bucket.spanId}</strong></div><div class="field"><label>Top 10 opciones longitudinales del vano (backend)</label><select class="span-opt-set"></select></div><div class="span-set-highlight" aria-live="polite"></div><div class="field"><label>Refuerzo longitudinal base del vano</label><select class="span-opt-longitudinal"></select></div><p class="help">Selecciona una opcion pre-calculada o usa Personalizada para elegir base + adicional por region.</p>`;
spanSetSelect=spanCard.querySelector('.span-opt-set');
spanLongSelect=spanCard.querySelector('.span-opt-longitudinal');
(bucket.spanLongOptionSets||[]).forEach(opt=>{const el=document.createElement('option');el.value=opt.value;el.textContent=`#${opt.rank} | ${opt.base_label} | total ${fmtKg(opt.total_weight_kg)} | long ${fmtKg(opt.total_longitudinal_weight_kg)}`;spanSetSelect.appendChild(el);});
const customOpt=document.createElement('option');customOpt.value='__custom__';customOpt.textContent='Personalizada';spanSetSelect.appendChild(customOpt);
bucket.spanBaseOptions.forEach(opt=>{const el=document.createElement('option');el.value=opt.value;el.textContent=`${opt.base_label} | ${fmtKg(opt.weight_kg)} (long. vano) | total ${fmtKg(opt.total_weight_kg)}`;spanLongSelect.appendChild(el);});
const savedSpan=spanLongSelections[bucket.spanId]||{};
const savedSet=(savedSpan&&savedSpan.mode==='set')?String(savedSpan.value||'').trim():'';
spanSetSelect.value=(bucket.spanLongOptionSets||[]).some(opt=>opt.value===savedSet)?savedSet:bucket.defaultSpanLongSetValue;
const savedBaseValue=(savedSpan&&savedSpan.mode==='custom')?savedSpan.value:null;
const initialBaseOption=bucket.spanBaseOptions.find(opt=>opt.value===savedBaseValue)||bucket.spanBaseOptions.find(opt=>opt.value===bucket.defaultSpanBaseValue)||bucket.spanBaseOptions[0];
spanLongSelect.value=initialBaseOption.value;
if(spanSetSelect.value==='__custom__'){spanLongSelections[bucket.spanId]={mode:'custom',value:initialBaseOption.value,label:initialBaseOption.base_label,option:initialBaseOption.option};}
else{const chosenSet=(bucket.spanLongOptionSets||[]).find(opt=>opt.value===spanSetSelect.value)||null;spanLongSelections[bucket.spanId]={mode:'set',value:spanSetSelect.value,option:chosenSet&&Number.isFinite(Number(chosenSet.option))?Number(chosenSet.option):null};}
}else{
const headText=bucket.hasCommonLong?'Longitudinal comun para todas las regiones':'Sin longitudinal comun global (seleccion por region)';
const helpText=bucket.hasCommonLong?'Solo se muestran opciones que cumplen en todas las regiones del vano.':'No hay un longitudinal comun entre todas las regiones; ajusta longitudinal por region.';
const labelText=bucket.hasCommonLong?'Refuerzo longitudinal del vano':'Referencia longitudinal del vano';
spanCard.innerHTML=`<div class="region-opt-head"><strong>Vano ${bucket.spanId}</strong><span>${headText}</span></div><div class="field"><label>${labelText}</label><select class="span-opt-longitudinal"></select></div><p class="help">${helpText}</p>`;
spanLongSelect=spanCard.querySelector('.span-opt-longitudinal');
bucket.spanLongOptions.forEach(opt=>{const el=document.createElement('option');el.value=opt.label;el.textContent=`${opt.label} | ${fmtKg(opt.weight_kg)}${bucket.hasCommonLong?' (vano)':' (referencia)'}`;spanLongSelect.appendChild(el);});
const savedSpan=spanLongSelections[bucket.spanId];
const savedLabel=(savedSpan&&savedSpan.mode==='label')?savedSpan.label:null;
const initialSpanLong=bucket.spanLongOptions.some(opt=>opt.label===savedLabel)?savedLabel:bucket.defaultSpanLong;
spanLongSelect.value=initialSpanLong;
if(bucket.hasCommonLong){spanLongSelections[bucket.spanId]={mode:'label',label:initialSpanLong};}else{delete spanLongSelections[bucket.spanId];}
}

body.appendChild(spanCard);
const regionSyncFns=[];
const spanSetHighlight=spanCard.querySelector('.span-set-highlight');
const updateSpanSetHighlight=()=>{
if(!bucket.isSpanCoupled||!spanSetSelect||!spanSetHighlight)return;
const sets=bucket.spanLongOptionSets||[];
const selected=sets.find(opt=>String(opt.value)===String(spanSetSelect.value))||null;
const best=sets[0]||null;
if(!selected){
const baseOption=bucket.spanBaseOptions.find(opt=>opt.value===spanLongSelect.value)||bucket.spanBaseOptions[0]||{base_label:'no se requiere'};
spanSetHighlight.className='span-set-highlight is-custom';
spanSetHighlight.innerHTML=`<span class="rank-pill">Personalizada</span> Base actual: <strong>${baseOption.base_label}</strong>.`;
return;
}
const delta=(best&&Number(best.total_longitudinal_weight_kg)>0)?((Number(selected.total_longitudinal_weight_kg)-Number(best.total_longitudinal_weight_kg))/Number(best.total_longitudinal_weight_kg))*100:0;
spanSetHighlight.className='span-set-highlight is-ranked';
spanSetHighlight.innerHTML=`<span class="rank-pill">#${selected.rank}</span> Seleccion actual: <strong>${selected.base_label}</strong> | Peso long: <strong>${fmtKg(selected.total_longitudinal_weight_kg)}</strong> | Peso total ref.: <strong>${fmtKg(selected.total_weight_kg)}</strong> | Delta vs #1: <strong>${fmtPct(delta)}</strong>`;
};

bucket.regions.forEach(region=>{
const card=document.createElement('div');
card.className='region-opt-card';
if(bucket.isSpanCoupled){
card.innerHTML=`<div class="region-opt-head"><strong>Region ${region.regionId}</strong><span>Opcion optima base: ${region.bestOption}</span></div><div class="region-opt-two"><div class="field"><label>Refuerzo transversal</label><select class="region-opt-transverse"></select></div><div class="field"><label>Refuerzo longitudinal adicional</label><select class="region-opt-additional"></select></div></div><p class="help region-opt-region-weight"></p>`;
}else if(bucket.hasCommonLong){
card.innerHTML=`<div class="region-opt-head"><strong>Region ${region.regionId}</strong><span>Opcion optima base: ${region.bestOption}</span></div><div class="field"><label>Refuerzo transversal</label><select class="region-opt-transverse"></select></div><p class="help region-opt-region-weight"></p>`;
}else{
card.innerHTML=`<div class="region-opt-head"><strong>Region ${region.regionId}</strong><span>Opcion optima base: ${region.bestOption}</span></div><div class="region-opt-two"><div class="field"><label>Refuerzo transversal</label><select class="region-opt-transverse"></select></div><div class="field"><label>Refuerzo longitudinal</label><select class="region-opt-longitudinal"></select></div></div><p class="help region-opt-region-weight"></p>`;
}

const transSelect=card.querySelector('.region-opt-transverse');
const addSelect=bucket.isSpanCoupled?card.querySelector('.region-opt-additional'):null;
const longSelect=(bucket.isSpanCoupled||bucket.hasCommonLong)?null:card.querySelector('.region-opt-longitudinal');
const weightLine=card.querySelector('.region-opt-region-weight');

region.transOptions.forEach(opt=>{const el=document.createElement('option');el.value=opt.label;el.textContent=formatTransverseOptionText(opt);transSelect.appendChild(el);});
if(longSelect){region.longOptions.forEach(opt=>{const el=document.createElement('option');el.value=opt.label;el.textContent=`${opt.label} | ${fmtKg(opt.weight_kg)}`;longSelect.appendChild(el);});}

const saved=regionOptionSelections[region.key]||{};
const initialTrans=region.transOptions.some(opt=>opt.label===saved.transverse_label)?saved.transverse_label:region.defaultTrans;
transSelect.value=initialTrans;
if(longSelect){const initialLong=region.longOptions.some(opt=>opt.label===saved.longitudinal_label)?saved.longitudinal_label:region.longOptions[0].label;longSelect.value=initialLong;}

const state={best:Number(region.referenceBestWeight)||Number(region.bestWeight)||0,selected:0};
states.push(state);
let cachedAdditionalOptions=[];

const refreshAdditionalChoices=()=>{
if(!bucket.isSpanCoupled||!addSelect)return[];
const selectedBase=bucket.spanBaseOptions.find(opt=>opt.value===spanLongSelect.value)||bucket.spanBaseOptions[0];
const baseValue=String((selectedBase&&selectedBase.value)||'').trim();
if(card.dataset.baseValue!==baseValue||!cachedAdditionalOptions.length){
cachedAdditionalOptions=getAdditionalOptionsByBaseValue(region,baseValue);
const savedSelection=regionOptionSelections[region.key]||{};
const keep=savedSelection.additional_value||addSelect.value;
addSelect.innerHTML='';
if(!cachedAdditionalOptions.length){const el=document.createElement('option');el.value='';el.textContent='Sin opcion adicional viable para esta base (backend)';addSelect.appendChild(el);addSelect.value='';addSelect.disabled=true;card.dataset.baseValue=baseValue;return cachedAdditionalOptions;}
addSelect.disabled=false;
cachedAdditionalOptions.forEach(opt=>{const el=document.createElement('option');el.value=opt.value;el.textContent=`${opt.label} | ${fmtKg(opt.weight_kg)}`;addSelect.appendChild(el);});
const preferredAdditional=cachedAdditionalOptions.find(opt=>normalizeAdditionalLabel(opt.label)===normalizeAdditionalLabel(region.defaultAdditionalLong));
const selectedValue=cachedAdditionalOptions.some(opt=>opt.value===keep)?keep:((preferredAdditional&&preferredAdditional.value)||cachedAdditionalOptions[0].value);
addSelect.value=selectedValue;
card.dataset.baseValue=baseValue;
}
return cachedAdditionalOptions;
};

const syncRegion=()=>{
const trans=region.transOptions.find(opt=>opt.label===transSelect.value)||region.transOptions[0];
let selectedLongLabel='';
let selectedLongWeight=0;
let selectedAdditionalLabel='no se requiere';
let selectedAdditionalValue='';
let selectedBaseLabel='';
let reference='region';
let activeAdditionalOptions=[];

if(bucket.isSpanCoupled){
const setValue=spanSetSelect?String(spanSetSelect.value||'').trim():'__custom__';
const isCustom=setValue==='__custom__';
const activeSet=!isCustom?(bucket.spanLongOptionSets||[]).find(opt=>opt.value===setValue):null;
let forcedBaseOption=null;
if(activeSet){forcedBaseOption=bucket.spanBaseOptions.find(opt=>opt.value===activeSet.base_value)||bucket.spanBaseOptions.find(opt=>opt.base_label===activeSet.base_label)||null;if(forcedBaseOption&&spanLongSelect&&spanLongSelect.value!==forcedBaseOption.value){spanLongSelect.value=forcedBaseOption.value;}}
const selectedBase=forcedBaseOption||bucket.spanBaseOptions.find(opt=>opt.value===spanLongSelect.value)||bucket.spanBaseOptions[0]||{base_label:'no se requiere',weight_kg:0};
const baseLabel=String(selectedBase.base_label||'').trim();
selectedBaseLabel=baseLabel;
const addOptions=refreshAdditionalChoices();
activeAdditionalOptions=addOptions;
let selectedAdd=null;
if(activeSet&&activeSet.region_map&&activeSet.region_map[region.regionId]){
const preset=activeSet.region_map[region.regionId];
selectedAdd=addOptions.find(opt=>normalizeAdditionalLabel(opt.label)===normalizeAdditionalLabel(preset.additional_label))||addOptions.find(opt=>String(opt.longitudinal_label||'').trim()===String(preset.longitudinal_label||'').trim())||addOptions[0]||null;
if(selectedAdd&&addSelect&&addSelect.value!==selectedAdd.value)addSelect.value=selectedAdd.value;
if(addSelect)addSelect.disabled=false;
}else{
if(addSelect)addSelect.disabled=false;
selectedAdd=addOptions.find(opt=>opt.value===addSelect.value)||addOptions[0]||null;
}

if(selectedAdd){selectedAdditionalLabel=selectedAdd.label;selectedAdditionalValue=selectedAdd.value;selectedLongLabel=String(selectedAdd.longitudinal_label||region.defaultLong).trim()||region.defaultLong;selectedLongWeight=Number(selectedAdd.longitudinal_total_weight_kg);if(!Number.isFinite(selectedLongWeight))selectedLongWeight=Number(selectedAdd.weight_kg)||0;}
else{selectedAdditionalLabel='sin opcion viable';selectedAdditionalValue='';selectedLongLabel=String(region.defaultLong||'').trim()||'no se requiere';selectedLongWeight=0;}

reference='GA top';
if(isCustom){spanLongSelections[bucket.spanId]={mode:'custom',value:selectedBase.value,label:baseLabel,option:selectedBase.option};}
else{spanLongSelections[bucket.spanId]={mode:'set',value:setValue,option:activeSet&&Number.isFinite(Number(activeSet.option))?Number(activeSet.option):null};}

}else if(bucket.hasCommonLong){
const currentLongLabel=spanLongSelect.value;
const long=region.longLookup[currentLongLabel]||region.longOptions[0];
selectedLongLabel=String(long.label||'').trim();
selectedLongWeight=Number(long.weight_kg)||0;
reference='vano';
}else{
const currentLongLabel=longSelect&&longSelect.value?longSelect.value:region.longOptions[0].label;
const long=region.longLookup[currentLongLabel]||region.longOptions[0];
selectedLongLabel=String(long.label||'').trim();
selectedLongWeight=Number(long.weight_kg)||0;
}

const selectedTransLabel=String(trans&&trans.label||'').trim();
const selectedTransNorm=normalizeMatchLabel(selectedTransLabel);
const selectedLongNorm=normalizeMatchLabel(String(selectedLongLabel||'').trim());
const selectedBaseNorm=selectedBaseLabel?normalizeMatchLabel(selectedBaseLabel):'';
const selectedAdditionalNorm=normalizeAdditionalLabel(selectedAdditionalLabel);
const exactRows=(region.options||[]).filter(row=>{
if(normalizeMatchLabel(row&&row.longitudinal_label)!==selectedLongNorm)return false;
if(selectedBaseNorm){
const rowBase=normalizeMatchLabel(row&&row.base_longitudinal_label);
if(rowBase!==selectedBaseNorm)return false;
}
if(selectedAdditionalNorm){
const rowAdditional=normalizeAdditionalLabel(row&&row.additional_longitudinal_label);
if(rowAdditional!==selectedAdditionalNorm)return false;
}
return true;
});
if(!exactRows.length){
state.selected=Number.NaN;
weightLine.textContent='Seleccion inconsistente: la combinacion elegida no existe en backend para esta region.';
return;
}
const byWeight=(a,b)=>{const aw=Number(a&&a.weight_total_kg);const bw=Number(b&&b.weight_total_kg);if(Number.isFinite(aw)&&Number.isFinite(bw)&&aw!==bw)return aw-bw;return Number(a&&a.option||0)-Number(b&&b.option||0);};
const currentRows=exactRows.filter(row=>normalizeMatchLabel(row&&row.transverse_label)===selectedTransNorm).sort(byWeight);
const resolvedRow=(currentRows[0]||[...exactRows].sort(byWeight)[0]);
const resolvedTransLabel=String(resolvedRow&&resolvedRow.transverse_label||selectedTransLabel).trim();
if(transSelect&&transSelect.value!==resolvedTransLabel)transSelect.value=resolvedTransLabel;
const resolvedLongLabel=String(resolvedRow&&resolvedRow.longitudinal_label||selectedLongLabel).trim()||selectedLongLabel;
const resolvedBaseLabel=String(resolvedRow&&resolvedRow.base_longitudinal_label||selectedBaseLabel||'').trim();
const resolvedAdditionalLabel=normalizeAdditionalLabel(resolvedRow&&resolvedRow.additional_longitudinal_label||selectedAdditionalLabel);
let resolvedAdditionalValue=selectedAdditionalValue;
if(bucket.isSpanCoupled&&activeAdditionalOptions.length){
const foundAdd=activeAdditionalOptions.find(opt=>normalizeAdditionalLabel(opt.label)===normalizeAdditionalLabel(resolvedAdditionalLabel)&&normalizeMatchLabel(opt.longitudinal_label)===normalizeMatchLabel(resolvedLongLabel))||activeAdditionalOptions.find(opt=>normalizeAdditionalLabel(opt.label)===normalizeAdditionalLabel(resolvedAdditionalLabel))||null;
if(foundAdd)resolvedAdditionalValue=foundAdd.value;
}
const selectedWeight=Number.isFinite(Number(resolvedRow&&resolvedRow.weight_total_kg))?Number(resolvedRow.weight_total_kg):((Number(resolvedRow&&resolvedRow.weight_transverse_kg)||0)+(Number(resolvedRow&&resolvedRow.weight_longitudinal_kg)||0));
if(Number.isFinite(Number(resolvedRow&&resolvedRow.weight_longitudinal_kg)))selectedLongWeight=Number(resolvedRow.weight_longitudinal_kg);
if(bucket.isSpanCoupled){
regionOptionSelections[region.key]={transverse_label:resolvedTransLabel,longitudinal_label:resolvedLongLabel,base_longitudinal_label:resolvedBaseLabel,additional_longitudinal_label:resolvedAdditionalLabel,additional_value:resolvedAdditionalValue};
}else{
regionOptionSelections[region.key]={transverse_label:resolvedTransLabel,longitudinal_label:resolvedLongLabel,base_longitudinal_label:resolvedBaseLabel,additional_longitudinal_label:resolvedAdditionalLabel,additional_value:''};
}
const bestWeight=Number.isFinite(Number(state.best))?Number(state.best):(Number(region.bestWeight)||0);
const deltaPct=bestWeight>0?((selectedWeight-bestWeight)/bestWeight)*100:null;
state.selected=selectedWeight;
weightLine.textContent=`Peso total region seleccionado: ${fmtKg(selectedWeight)} | Peso total region optimo (${reference}): ${fmtKg(bestWeight)} | Delta: ${fmtPct(deltaPct)}`;
};

transSelect.addEventListener('change',()=>{syncRegion();updateSummary();syncBeamPreviewWithSelections();});
if(addSelect){addSelect.addEventListener('change',()=>{if(spanSetSelect&&spanSetSelect.value!=='__custom__'){spanSetSelect.value='__custom__';}syncRegion();updateSpanSetHighlight();updateSummary();syncBeamPreviewWithSelections();});}
if(longSelect){longSelect.addEventListener('change',()=>{syncRegion();updateSummary();syncBeamPreviewWithSelections();});}
regionSyncFns.push(syncRegion);
syncRegion();
body.appendChild(card);
});

if(bucket.isSpanCoupled){
if(spanSetSelect){spanSetSelect.addEventListener('change',()=>{regionSyncFns.forEach(fn=>fn());updateSpanSetHighlight();updateSummary();syncBeamPreviewWithSelections();});}
if(spanLongSelect){spanLongSelect.addEventListener('change',()=>{if(spanSetSelect&&spanSetSelect.value!=='__custom__'){spanSetSelect.value='__custom__';}const selectedBase=bucket.spanBaseOptions.find(opt=>opt.value===spanLongSelect.value)||bucket.spanBaseOptions[0];spanLongSelections[bucket.spanId]={mode:'custom',value:selectedBase.value,label:selectedBase.base_label,option:selectedBase.option};regionSyncFns.forEach(fn=>fn());updateSpanSetHighlight();updateSummary();syncBeamPreviewWithSelections();});}
}else if(bucket.hasCommonLong){
spanLongSelect.addEventListener('change',()=>{spanLongSelections[bucket.spanId]={mode:'label',label:spanLongSelect.value};regionSyncFns.forEach(fn=>fn());updateSummary();syncBeamPreviewWithSelections();});
}

regionSyncFns.forEach(fn=>fn());
updateSpanSetHighlight();
updateSummary();
regionOptionsEl.appendChild(details);
});

if(saveSelectionBtn)saveSelectionBtn.disabled=!currentJobId;
updateSummary();
syncBeamPreviewWithSelections();
}

function buildSelectionPayload(previewPayload){
const spans=previewPayload&&Array.isArray(previewPayload.spans)?previewPayload.spans:[];
const selections=[];
const spanSelections=[];
spans.forEach((sp,sIndex)=>{
const spanId=sp.span_id||`S${sIndex+1}`;
const regions=Array.isArray(sp.regions)?sp.regions:[];
const isSpanCoupled=regions.some(r=>String(r&&r.longitudinal_mode||'').trim().toLowerCase()==='span_coupled');
regions.forEach((rg,rIndex)=>{
const regionId=rg.region_id||`R${rIndex+1}`;
const options=Array.isArray(rg.options)?rg.options:[];
if(!options.length)return;
const fallback=options[0]||{};
const key=`${spanId}__${regionId}`;
const saved=regionOptionSelections[key]||{};
const transverse_label=saved.transverse_label||String(fallback.transverse_label||'');
const row={span_id:spanId,region_id:regionId,transverse_label};
row.longitudinal_label=saved.longitudinal_label||String(fallback.longitudinal_label||'');
row.base_longitudinal_label=saved.base_longitudinal_label||String(fallback.base_longitudinal_label||'');
row.additional_longitudinal_label=saved.additional_longitudinal_label||String(fallback.additional_longitudinal_label||'');
selections.push(row);
});
const savedSpan=spanLongSelections[spanId];
if(isSpanCoupled){
if(savedSpan&&savedSpan.mode==='set'&&Number.isFinite(Number(savedSpan.option))){
spanSelections.push({span_id:spanId,option:Number(savedSpan.option)});
}else if(savedSpan&&savedSpan.mode==='custom'&&savedSpan.label){
spanSelections.push({span_id:spanId,longitudinal_label:String(savedSpan.label)});
}
}else if(savedSpan&&savedSpan.mode==='label'&&savedSpan.label){
spanSelections.push({span_id:spanId,longitudinal_label:String(savedSpan.label)});
}
});
return{selections,span_selections:spanSelections};
}

function renderSummary(data,st){if(statusModule.renderSummaryHtml){summaryListEl.innerHTML=statusModule.renderSummaryHtml(data,st);return}summaryListEl.innerHTML=[`<li><strong>Viga:</strong> ${data.beamId} | Detallado ${data.detailing}</li>`,`<li><strong>Material:</strong> f'c ${Math.round(data.fcMpa)} MPa | fy ${Math.round(data.fyMpa)} MPa</li>`,`<li><strong>Vanos:</strong> ${Array.isArray(data.spans)?data.spans.length:0}</li>`,`<li><strong>Longitud neta vanos:</strong> ${Math.round(data.totalSpanMm)} mm${data.totalSpanEstimated?' (estimado)':''}</li>`,`<li><strong>Longitud apoyos:</strong> ${Math.round(data.totalSupportMm||0)} mm</li>`,`<li><strong>Longitud total sistema:</strong> ${Math.round(data.totalSystemMm||data.totalSpanMm)} mm</li>`,`<li><strong>Estado job:</strong> ${(st&&st.status)||'sin job'}</li>`].join('')}
function renderChecks(st){const rows=statusModule.buildCheckRows?statusModule.buildCheckRows(st):(()=>{const localRows=[],s=st&&st.status?st.status:'idle';if(s==='completed')localRows.push({c:'ok',m:'Job completado correctamente.'});else if(s==='failed')localRows.push({c:'err',m:'Job finalizo en estado failed.'});else if(s==='running'||s==='queued')localRows.push({c:'warn',m:`Job en progreso: ${s}.`});else localRows.push({c:'warn',m:'Aun no se ha ejecutado un job en esta sesion.'});localRows.push({c:'ok',m:'Contratos API preservados (/v1/jobs*).'});localRows.push({c:'ok',m:'Preview SVG soporta vanos multiples, apoyos y regiones por vano.'});return localRows})();checksListEl.innerHTML=rows.map(r=>`<li class="${r.c}">${r.m}</li>`).join('')}
async function saveSelectionReport(){if(!currentJobId||!currentPreviewPayload){if(selectionSaveMsg)selectionSaveMsg.textContent='Primero ejecuta un job y espera el preview.';return}if(saveSelectionBtn)saveSelectionBtn.disabled=true;if(selectionSaveMsg)selectionSaveMsg.textContent='Guardando seleccion y generando reporte...';try{const response=await fetch(`/v1/jobs/${currentJobId}/selection`,{method:'POST',headers:{'Content-Type':'application/json',...headersWithApiKey()},body:JSON.stringify(buildSelectionPayload(currentPreviewPayload))});const payload=await response.json().catch(()=>({}));if(!response.ok){if(selectionSaveMsg)selectionSaveMsg.textContent=payload&&payload.message?`No se pudo guardar: ${payload.message}`:'No se pudo guardar la seleccion.';if(saveSelectionBtn)saveSelectionBtn.disabled=false;return}if(selectionSaveMsg)selectionSaveMsg.textContent=`Seleccion guardada. Reporte generado: ${payload.artifact_name}`;await refreshStatus(currentJobId)}catch(error){if(selectionSaveMsg)selectionSaveMsg.textContent=error&&error.message?`No se pudo guardar: ${error.message}`:'No se pudo guardar la seleccion.';if(saveSelectionBtn)saveSelectionBtn.disabled=false}}
async function refreshPreviewFromJob(jobId,statusPayload){let preview=null;try{const r=await fetch(`/v1/jobs/${jobId}/preview`,{headers:headersWithApiKey()});if(r.ok){preview=await r.json();currentPreviewPayload=preview}}catch(e){preview=null}const data=buildBeamData({previewPayload:preview});renderBeam(beamElevationContainer,data);renderSummary(data,statusPayload);renderChecks(statusPayload);renderRegionOptions(currentPreviewPayload)}
function refreshPreview(statusPayload=null){const data=buildBeamData({previewPayload:currentPreviewPayload});renderBeam(beamElevationContainer,data);renderSummary(data,statusPayload);renderChecks(statusPayload);renderRegionOptions(currentPreviewPayload)}
async function refreshStatus(jobId){const response=await fetch(`/v1/jobs/${jobId}`,{headers:headersWithApiKey()}),payload=await response.json().catch(()=>({}));if(!response.ok){renderError(normalizeErrorPayload(payload,response.status));stopPolling();setSubmitting(false);return}showStatusPayload(payload);renderArtifacts(payload.artifacts);refreshPreview(payload);if(payload.status==='completed'){setStatus('Job completado. Puedes descargar resultados.','ok');await refreshPreviewFromJob(jobId,payload);stopPolling();setSubmitting(false);switchView('view-results');return}if(payload.status==='failed'){renderError({error:'job_failed',message:`El job termino en estado failed${payload.error?`: ${payload.error}`:''}`,details:[]});stopPolling();setSubmitting(false);return}setStatus(`Job en progreso: ${payload.status}`,'running')}
addSpanBtn.addEventListener('click',()=>{spanLayoutList.appendChild(createSpanRow({}));currentPreviewPayload=null;refreshPreview()});enableSpanLayout.addEventListener('change',()=>{syncAdvancedSections();currentPreviewPayload=null;refreshPreview()});enableOptimizationOverrides.addEventListener('change',syncAdvancedSections);spanLayoutList.addEventListener('input',()=>{currentPreviewPayload=null;refreshPreview()});spanLayoutList.addEventListener('change',()=>{currentPreviewPayload=null;refreshPreview()});['beam_id','detailing','fc_mpa','fy_mpa','db_bar'].forEach(id=>{const el=document.getElementById(id);if(el)el.addEventListener('input',()=>{currentPreviewPayload=null;refreshPreview()})});syncAdvancedSections();
form.addEventListener('submit',async(event)=>{event.preventDefault();if(isSubmitting)return;stopPolling();clearErrorBox();clearFieldErrors();detailsEl.classList.add('hidden');detailsEl.textContent='';setSubmitting(true);setStatus('Validando datos y creando job...','running');switchView('view-results');if(!buildAdvancedPayload()){setSubmitting(false);return}const formData=new FormData(form);if(!formData.get('frame_pairs_json'))formData.delete('frame_pairs_json');if(!formData.get('optimization_overrides_json'))formData.delete('optimization_overrides_json');if(!formData.get('span_layout_json'))formData.delete('span_layout_json');try{const response=await fetch('/v1/jobs/from-form',{method:'POST',body:formData,headers:headersWithApiKey()}),payload=await response.json().catch(()=>({}));if(!response.ok){renderError(normalizeErrorPayload(payload,response.status));setSubmitting(false);return}currentJobId=payload.job_id;currentPreviewPayload=null;regionOptionSelections={};spanLongSelections={};setLinks(currentJobId,payload);renderArtifacts([]);setStatus(`Job ${currentJobId} creado. Iniciando monitoreo...`,'running');await refreshStatus(currentJobId);if(!pollTimer&&isSubmitting){pollTimer=setInterval(()=>{refreshStatus(currentJobId).catch((error)=>{renderError({error:'network_error',message:error?.message||'No fue posible consultar el estado del job',details:[]});stopPolling();setSubmitting(false)})},2500)}}catch(error){renderError({error:'network_error',message:error?.message||'No fue posible enviar la solicitud',details:[]});setSubmitting(false)}});
clearBtn.addEventListener('click',()=>{stopPolling();currentJobId=null;currentPreviewPayload=null;regionOptionSelections={};spanLongSelections={};if(saveSelectionBtn)saveSelectionBtn.disabled=true;if(selectionSaveMsg)selectionSaveMsg.textContent='';setSubmitting(false);setStatus('Esperando ejecucion');resultsLinksEl.innerHTML='';detailsEl.textContent='';detailsEl.classList.add('hidden');clearErrorBox();clearFieldErrors();renderArtifacts([]);refreshPreview()});
if(saveSelectionBtn)saveSelectionBtn.addEventListener('click',saveSelectionReport);renderArtifacts([]);refreshPreview();
})();






