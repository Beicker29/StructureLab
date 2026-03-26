(() => {
const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
const defaultSpacing=regionType=>String(regionType||'').toUpperCase()==='C'?100:200;

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

window.StructureLabSvg = {
  buildBeamElevationSvg,
};
})();
