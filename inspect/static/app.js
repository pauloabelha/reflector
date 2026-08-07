const ARC_COLORS = {
  0: '#000000', 1: '#0074D9', 2: '#FF4136', 3: '#2ECC40', 4: '#FFDC00',
  5: '#AAAAAA', 6: '#F012BE', 7: '#FF851B', 8: '#7FDBFF', 9: '#870C25',
  10: '#62c6d8', 11: '#d8eef2'
};

const state = { grid: null, palette: {}, analysis: null, assignment: null, overlay: 'schemas', selected: null, hovered: null, graphTransform: {x:0,y:0,k:1} };
const $ = selector => document.querySelector(selector);
const fixturesEl = $('#fixtures');
const gridCanvas = $('#grid-canvas');
const overlayCanvas = $('#overlay-canvas');
const dropZone = $('#drop-zone');
const statusEl = $('#status');
const svg = $('#concept-graph');

function showStatus(message, error=false) {
  statusEl.textContent = message;
  statusEl.classList.toggle('error', error);
  statusEl.classList.remove('hidden');
}
function hideStatus() { statusEl.classList.add('hidden'); }
function colorFor(value) { return state.palette[String(value)] || ARC_COLORS[value] || hslColor(value); }
function hslColor(value) { return `hsl(${(Number(value) * 67 + 196) % 360} 58% 56%)`; }
function generatedAssignment(node) {
  if (node.depth===0) return null;
  const regions=node.region_ids.map(id=>state.analysis?.regions.find(region=>region.id===id)).filter(Boolean);
  const heads=[...node.heads].sort();
  const key=heads.join('+');
  const relationLabels={
    'DifferentInteriorContrast':'same-outline figures with different internal contrast',
    'Enclosed+Inside':'enclosed area and owning figure',
    'Inside+Kind':'inside-object relation',
    'SameInteriorContrast':'same-outline figures with matching internal contrast',
    'SameOutline':'same-outline figure pair'
  };
  let label=relationLabels[key];
  if (!label && heads.includes('Form') && heads.includes('Kind')) {
    const areas=new Set(regions.map(region=>region.area));
    const sizes=new Set(regions.map(region=>`${region.bbox[2]-region.bbox[0]+1}×${region.bbox[3]-region.bbox[1]+1}`));
    if (regions.length>1 && areas.size===1 && sizes.size===1) label=`repeated ${[...sizes][0]} form object`;
    else if (regions.length===1) label=`${[...sizes][0]||'specific'} form object`;
    else label='specific form object';
  }
  label ||= `compound: ${heads.join(' + ')}`;
  return {label, author:'Codex external assignment template', rationale:'Generated outside Reflector from this displayed canonical body and its bound frame regions.'};
}
function assignedLabel(node) { return state.assignment?.labels?.[node.hash] || generatedAssignment(node); }
function displayName(node) { return assignedLabel(node)?.label || node.name; }

async function jsonFetch(url, options={}) {
  const response = await fetch(url, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || `${response.status}`);
  return value;
}

async function loadFixtures() {
  try {
    const {fixtures} = await jsonFetch('/api/fixtures');
    fixturesEl.innerHTML = '';
    for (const fixture of fixtures) {
      const button = document.createElement('button');
      button.className = 'fixture-button';
      button.dataset.id = fixture.id;
      const preview = document.createElement('canvas'); preview.width = 32; preview.height = 32;
      const label = document.createElement('div');
      label.innerHTML = `<strong>${escapeHtml(fixture.label)}</strong><small>${fixture.group} · ${fixture.shape.join('×')}</small>`;
      button.append(preview, label);
      button.addEventListener('click', () => loadFixture(fixture.id, button));
      fixturesEl.append(button);
      jsonFetch(`/api/fixture?id=${encodeURIComponent(fixture.id)}`).then(data => drawPreview(preview, data.grid));
    }
  } catch (error) { showStatus(`Could not load fixtures: ${error.message}`, true); }
}

async function loadFixture(id, button) {
  document.querySelectorAll('.fixture-button').forEach(item => item.classList.toggle('active', item === button));
  showStatus('Reading fixture and activating the sparse workspace…');
  try {
    const fixture = await jsonFetch(`/api/fixture?id=${encodeURIComponent(id)}`);
    state.palette = {};
    state.assignment = fixture.assignment || null;
    await analyze(fixture.grid, fixture.background, fixture.label);
  } catch (error) { showStatus(error.message, true); }
}

async function analyze(grid, background=null, label='Uploaded image') {
  state.analysis = null;
  state.selected = null;
  state.grid = grid;
  drawGrid(grid);
  $('#empty-state').classList.add('hidden');
  $('#canvas-badge').textContent = `${label} · ${grid.length}×${grid[0].length}`;
  $('#canvas-badge').classList.remove('hidden');
  try {
    const analysis = await jsonFetch('/api/analyze', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({grid, background, palette: state.palette})
    });
    state.analysis = analysis;
    state.palette = analysis.palette || state.palette;
    renderAll();
    hideStatus();
  } catch (error) { showStatus(`Analysis failed: ${error.message}`, true); }
}

function drawPreview(canvas, grid) {
  const ctx = canvas.getContext('2d'); ctx.imageSmoothingEnabled = false;
  const h = grid.length, w = grid[0].length, scale = Math.min(canvas.width/w,canvas.height/h);
  const ox = (canvas.width-w*scale)/2, oy=(canvas.height-h*scale)/2;
  ctx.fillStyle='#020609';ctx.fillRect(0,0,canvas.width,canvas.height);
  grid.forEach((row,y)=>row.forEach((v,x)=>{ctx.fillStyle=ARC_COLORS[v]||hslColor(v);ctx.fillRect(ox+x*scale,oy+y*scale,Math.ceil(scale),Math.ceil(scale));}));
}

function drawGrid(grid) {
  const stage = dropZone.getBoundingClientRect();
  const maxW = Math.max(200, stage.width-44), maxH=Math.max(200,stage.height-44);
  const h=grid.length,w=grid[0].length, scale=Math.max(1,Math.floor(Math.min(maxW/w,maxH/h)));
  const cssW=w*scale,cssH=h*scale, pixelRatio=window.devicePixelRatio||1;
  for (const canvas of [gridCanvas,overlayCanvas]) {
    canvas.width=cssW*pixelRatio;canvas.height=cssH*pixelRatio;
    canvas.style.width=`${cssW}px`;canvas.style.height=`${cssH}px`;
  }
  const ctx=gridCanvas.getContext('2d');ctx.scale(pixelRatio,pixelRatio);ctx.imageSmoothingEnabled=false;
  grid.forEach((row,y)=>row.forEach((v,x)=>{ctx.fillStyle=colorFor(v);ctx.fillRect(x*scale,y*scale,scale+.4,scale+.4);}));
  state.cellScale=scale; state.pixelRatio=pixelRatio;
  drawOverlay();
}

function drawOverlay() {
  const ctx=overlayCanvas.getContext('2d');ctx.clearRect(0,0,overlayCanvas.width,overlayCanvas.height);
  if (!state.analysis || state.overlay==='none' || state.hovered===null) return;
  const node=state.analysis.nodes.find(item=>item.id===state.hovered);
  if (!node || !node.region_ids.length) return;
  const regionIds=new Set(node.region_ids);
  const scale=state.cellScale, pr=state.pixelRatio;ctx.save();ctx.scale(pr,pr);
  for (const region of state.analysis.regions.filter(item=>regionIds.has(item.id))) {
    const [x0,y0,x1,y1]=region.bbox;
    ctx.strokeStyle='#78f0c2';ctx.lineWidth=Math.max(1.5,Math.min(3,scale*.19));
    ctx.setLineDash([]);
    ctx.strokeRect(x0*scale+.8,y0*scale+.8,(x1-x0+1)*scale-1.6,(y1-y0+1)*scale-1.6);
    if (scale>=4) {const label=shortName(displayName(node));ctx.font=`${Math.max(7,Math.min(10,scale*.52))}px DM Mono`;const labelWidth=Math.min((x1-x0+1)*scale-4,ctx.measureText(label).width+8);ctx.fillStyle='rgba(2,9,13,.88)';ctx.fillRect(x0*scale+2,y0*scale+2,labelWidth,Math.min(16,scale*1.25));ctx.fillStyle='#bdf8dd';ctx.fillText(label,x0*scale+5,y0*scale+Math.min(12,scale*.9));}
  }
  ctx.restore();
}

function renderAll() { drawGrid(state.analysis.grid); renderPalette(); renderRegionSummary(); renderMetrics(); renderConcepts(); renderGraph(); }

function renderPalette() {
  const el=$('#palette');el.innerHTML='';
  for (const [value,count] of Object.entries(state.analysis.value_counts)) {
    const item=document.createElement('span');item.className=`swatch ${Number(value)===state.analysis.background?'background':''}`;
    item.innerHTML=`<i style="background:${colorFor(value)}"></i><span>${value} · ${count}</span>`;el.append(item);
  }
}
function renderRegionSummary() {
  $('#region-summary').textContent=`${state.analysis.regions.length} foreground regions · ${state.analysis.forms.length} form signatures · background ${state.analysis.background} · ${state.analysis.fact_sample.length}/${Object.values(state.analysis.fact_counts).reduce((a,b)=>a+b,0)} facts sampled`;
}

const metricSpec = [
  ['active_schemas','Active schemas','active_nodes','accent'],['active_edges','Active edges','active_edges',''],
  ['reusable_composite_candidates','Reusable candidates',null,'accent'],
  ['candidates_retrieved','Retrieved','binding_candidates',''],['candidates_verified','Verified',null,''],
  ['compositions_proposed','Proposed','composition_proposals',''],['compositions_retained','Retained',null,'accent'],
  ['work_items_processed','Work items',null,''],['peak_workspace','Peak workspace','active_nodes',''],
  ['truncations','Budget truncations',null,''],['matching_time_s','Match time',null,'time'],
  ['activation_time_s','Activation time',null,'time'],['composition_time_s','Compose time',null,'time']
];
function renderMetrics() {
  const el=$('#metrics');el.innerHTML='';
  for (const [key,label,limitKey,kind] of metricSpec) {
    const value=state.analysis.metrics[key];const card=document.createElement('div');card.className=`metric-card ${kind==='accent'?'accent':''}`;
    const shown=kind==='time'?`${(value*1000).toFixed(2)} ms`:Number(value).toLocaleString();
    const reasons=Object.entries(state.analysis.truncation_reasons||{}).map(([name,count])=>`${count} ${name.replaceAll('-',' ')}`).join(' · ');
    const limit=limitKey?`budget ${state.analysis.limits[limitKey].toLocaleString()}`:(key==='truncations'?(reasons||'no budget events'):'this cycle');
    card.innerHTML=`<span>${label}</span><strong>${shown}</strong><small>${limit}</small>`;el.append(card);
  }
}

function filteredNodes() {
  const query=$('#search').value.trim().toLowerCase();
  return state.analysis.nodes.filter(node=>!query||displayName(node).toLowerCase().includes(query)||node.name.toLowerCase().includes(query)||node.body.some(atom=>atom.toLowerCase().includes(query)));
}
function renderConcepts() {
  const nodes=filteredNodes();const el=$('#concepts');el.innerHTML='';$('#concept-count').textContent=`${nodes.length} active`;
  for (const node of nodes.slice(0,80)) {
    const card=document.createElement('article');card.className='concept-card';card.dataset.id=node.id;
    const assignment=assignedLabel(node);const assignmentHtml=assignment?`<div class="concept-assignment">External label assigned by ${escapeHtml(assignment.author || state.assignment?.author || 'Codex')}</div>`:'';
    card.innerHTML=`<div class="concept-card-header"><h4>${escapeHtml(displayName(node))}</h4><span class="depth-pill">${node.reusable_candidate?'reusable · ':''}${node.state} · depth ${node.depth}</span></div>${assignmentHtml}<div class="activation-bar"><i style="width:${Math.max(3,node.activation*100)}%"></i></div>${node.body.slice(0,4).map(atom=>`<code class="atom">${escapeHtml(atom)}</code>`).join('')}<div class="concept-meta"><span>${node.bindings} binding${node.bindings===1?'':'s'}</span><span>a=${node.activation.toFixed(2)}</span><span>${node.provenance[0]||'unknown'}</span></div>`;
    card.addEventListener('click',()=>openNode(node));el.append(card);
  }
}

function graphLayout(nodes) {
  const groups=new Map();for(const node of nodes){const d=Math.min(node.depth,4);if(!groups.has(d))groups.set(d,[]);groups.get(d).push(node);}
  const positions=new Map();const depths=[...groups.keys()].sort((a,b)=>a-b);const width=900,height=560;
  depths.forEach((depth,column)=>{const values=groups.get(depth);const x=depths.length===1?width/2:90+column*(width-180)/Math.max(1,depths.length-1);values.forEach((node,i)=>{const spacing=(height-80)/(values.length+1);const jitter=((hashNumber(node.short_hash)%17)-8)*1.3;positions.set(node.id,{x:x+jitter,y:40+(i+1)*spacing});});});
  return positions;
}
function renderGraph() {
  const nodes=state.analysis.nodes;const visible=new Set(filteredNodes().map(n=>n.id));const pos=graphLayout(nodes);
  svg.innerHTML='<g id="viewport"><g id="links"></g><g id="nodes"></g></g>';$('#graph-empty').classList.toggle('hidden',nodes.length>0);
  const linkLayer=svg.querySelector('#links'),nodeLayer=svg.querySelector('#nodes');
  for(const link of state.analysis.links){if(!pos.has(link.source)||!pos.has(link.target))continue;const a=pos.get(link.source),b=pos.get(link.target);const line=document.createElementNS('http://www.w3.org/2000/svg','line');line.setAttribute('x1',a.x);line.setAttribute('y1',a.y);line.setAttribute('x2',b.x);line.setAttribute('y2',b.y);line.setAttribute('class',`graph-link ${link.relation} ${visible.has(link.source)&&visible.has(link.target)?'':'dim'}`);linkLayer.append(line);}
  for(const node of nodes){const p=pos.get(node.id),g=document.createElementNS('http://www.w3.org/2000/svg','g');g.setAttribute('class',`graph-node ${visible.has(node.id)?'':'dim'} ${state.selected===node.id?'selected':''}`);g.setAttribute('transform',`translate(${p.x} ${p.y})`);g.dataset.id=node.id;const circle=document.createElementNS('http://www.w3.org/2000/svg','circle');const radius=5+Math.min(7,node.bindings*.35)+node.depth*1.4;circle.setAttribute('r',radius);circle.setAttribute('fill',node.depth===0?'#68d9ff':node.depth===1?'#78f0c2':'#b6a0ff');circle.setAttribute('fill-opacity',.42+node.activation*.45);const text=document.createElementNS('http://www.w3.org/2000/svg','text');text.setAttribute('y',radius+12);text.textContent=shortName(displayName(node));g.append(circle,text);g.addEventListener('mouseenter',()=>{state.hovered=node.id;drawOverlay();});g.addEventListener('mouseleave',()=>{if(state.hovered===node.id){state.hovered=null;drawOverlay();}});g.addEventListener('click',event=>{event.stopPropagation();openNode(node);});nodeLayer.append(g);}
  applyGraphTransform();
}
function shortName(name){return name.length>19?name.slice(0,17)+'…':name;}
function hashNumber(value){return [...value].reduce((n,c)=>(n*31+c.charCodeAt(0))>>>0,7);}
function applyGraphTransform(){const {x,y,k}=state.graphTransform;const viewport=svg.querySelector('#viewport');if(viewport)viewport.setAttribute('transform',`translate(${x} ${y}) scale(${k})`);}
function resetGraph(){state.graphTransform={x:0,y:0,k:1};applyGraphTransform();}

function openNode(node) {
  state.selected=node.id;renderGraph();
  const assignment=assignedLabel(node);const assignmentHtml=assignment?`<div class="assignment-detail"><strong>External label assignment</strong><span>Assigned by ${escapeHtml(assignment.author || state.assignment?.author || 'Codex')}. Not learned by Reflector.</span><span>${escapeHtml(assignment.rationale)}</span></div>`:'';
  const dagHtml=node.decompositions.length?node.decompositions.map((dag,index)=>`<div class="dag-card"><div class="dag-title">derivation ${index+1} · acyclic</div>${dag.occurrences.map(occ=>{const child=state.analysis.nodes.find(item=>item.id===occ.schema);return `<div class="dag-occurrence"><strong>${escapeHtml(child?displayName(child):occ.name)}</strong><small>${escapeHtml(occ.short_hash)}</small>${occ.interface.length?`<code>${occ.interface.map(escapeHtml).join(' · ')}</code>`:''}</div>`;}).join('')}<div class="dag-provenance">${dag.provenance.map(escapeHtml).join(' · ')}</div></div>`).join(''):'<div class="drawer-muted">Atomic schema; no decomposition.</div>';
  const interfaceHtml=(node.interface||[]).map(value=>`<span class="tag">${escapeHtml(value)}</span>`).join('')||'<span class="drawer-muted">none</span>';
  const constraintHtml=(node.definition_constraints||[]).map(atom=>`<div class="drawer-atom">${escapeHtml(atom)}</div>`).join('')||'<div class="drawer-muted">No parent-level constraints.</div>';
  const bindingHtml=(node.binding_records||[]).map(binding=>`<div class="dag-occurrence"><strong>${escapeHtml(binding.status)}</strong><small>${escapeHtml(binding.carrier)} · ${escapeHtml(binding.provenance)}</small></div>`).join('')||'<div class="drawer-muted">No current realized binding.</div>';
  const shadowHtml=(node.shadows||[]).map(shadow=>`<div class="dag-occurrence"><strong>${escapeHtml(shadow.status)}</strong><small>${escapeHtml(shadow.carrier)} · ${escapeHtml(shadow.provenance)}</small>${(shadow.child_roles||[]).map(role=>`<code>child role ${role.role}: ${escapeHtml(role.status)} · ${escapeHtml(role.assignments.join(' · ')||'unbound')}</code>`).join('')}${(shadow.constraints||[]).map(constraint=>`<code>constraint ${constraint.constraint}: ${escapeHtml(constraint.status)}</code>`).join('')}<code>open roles: ${shadow.open_roles.map(escapeHtml).join(' · ')||'none'}; completed roles: ${(shadow.completed_roles||[]).join(',')||'none'}</code></div>`).join('')||'<div class="drawer-muted">No projected shadow.</div>';
  $('#drawer-content').innerHTML=`<div class="eyebrow">Reusable schema definition · ${escapeHtml(node.state)} · depth ${node.depth}${node.reusable_candidate?' · reusable candidate':''}</div><h2>${escapeHtml(displayName(node))}</h2>${assignmentHtml}<div class="drawer-hash">runtime display name: ${escapeHtml(node.name)}<br>identity hash: ${node.hash}</div><div class="drawer-section"><div class="drawer-stats"><div class="drawer-stat"><span>activation</span><strong>${node.activation.toFixed(3)}</strong></div><div class="drawer-stat"><span>bindings</span><strong>${node.bindings}</strong></div><div class="drawer-stat"><span>uses</span><strong>${node.uses}</strong></div><div class="drawer-stat"><span>support</span><strong>${node.support}</strong></div><div class="drawer-stat"><span>contradiction</span><strong>${node.contradiction}</strong></div><div class="drawer-stat"><span>depth</span><strong>${node.depth}</strong></div></div></div><div class="drawer-section"><h5>Exposed interface</h5>${interfaceHtml}</div><div class="drawer-section"><h5>Definition DAG</h5>${dagHtml}</div><div class="drawer-section"><h5>Parent-level constraints</h5>${constraintHtml}</div><div class="drawer-section"><h5>Compiled matcher expansion</h5>${node.body.map(atom=>`<div class="drawer-atom">${escapeHtml(atom)}</div>`).join('')}</div><div class="drawer-section"><h5>Reified bindings</h5>${bindingHtml}</div><div class="drawer-section"><h5>Projected shadows</h5>${shadowHtml}</div><div class="drawer-section"><h5>Relation heads</h5>${node.heads.map(tag=>`<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div><div class="drawer-section"><h5>Provenance</h5>${node.provenance.map(tag=>`<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>`;
  $('#drawer').classList.add('open');$('#drawer').setAttribute('aria-hidden','false');$('#scrim').classList.add('open');
}
function closeDrawer(){state.selected=null;$('#drawer').classList.remove('open');$('#drawer').setAttribute('aria-hidden','true');$('#scrim').classList.remove('open');if(state.analysis)renderGraph();}

async function readImage(file) {
  const url=URL.createObjectURL(file);const image=new Image();
  await new Promise((resolve,reject)=>{image.onload=resolve;image.onerror=reject;image.src=url;});
  const scale=Math.min(1,96/image.width,96/image.height);const w=Math.max(1,Math.round(image.width*scale)),h=Math.max(1,Math.round(image.height*scale));
  const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.imageSmoothingEnabled=false;ctx.drawImage(image,0,0,w,h);URL.revokeObjectURL(url);
  const data=ctx.getImageData(0,0,w,h).data;const quantized=[];const counts=new Map();
  for(let i=0;i<data.length;i+=4){const rgba=[data[i],data[i+1],data[i+2],data[i+3]];const q=rgba[3]<32?[0,0,0]:rgba.slice(0,3).map(v=>Math.min(255,Math.round(v/32)*32));const key=q.join(',');quantized.push(q);counts.set(key,(counts.get(key)||0)+1);}
  const colors=[...counts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,32).map(([key])=>key.split(',').map(Number));
  const grid=[];state.palette={};colors.forEach((c,i)=>state.palette[String(i)]=`rgb(${c.join(',')})`);
  for(let y=0;y<h;y++){const row=[];for(let x=0;x<w;x++){const c=quantized[y*w+x];let best=0,dist=Infinity;colors.forEach((p,i)=>{const d=(c[0]-p[0])**2+(c[1]-p[1])**2+(c[2]-p[2])**2;if(d<dist){dist=d;best=i;}});row.push(best);}grid.push(row);}
  return grid;
}

$('#image-input').addEventListener('change',async event=>{const file=event.target.files[0];if(!file)return;showStatus('Quantizing image and constructing evidence…');try{state.assignment=null;const grid=await readImage(file);await analyze(grid,null,file.name);}catch(error){showStatus(error.message,true);}});
['dragenter','dragover'].forEach(type=>dropZone.addEventListener(type,event=>{event.preventDefault();dropZone.classList.add('dragging');}));
['dragleave','drop'].forEach(type=>dropZone.addEventListener(type,event=>{event.preventDefault();dropZone.classList.remove('dragging');}));
dropZone.addEventListener('drop',async event=>{const file=[...event.dataTransfer.files].find(f=>f.type.startsWith('image/'));if(!file)return;showStatus('Quantizing image and constructing evidence…');try{state.assignment=null;const grid=await readImage(file);await analyze(grid,null,file.name);}catch(error){showStatus(error.message,true);}});
document.querySelectorAll('[data-overlay]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('[data-overlay]').forEach(item=>item.classList.toggle('active',item===button));state.overlay=button.dataset.overlay;drawOverlay();}));
$('#search').addEventListener('input',()=>{if(state.analysis){renderConcepts();renderGraph();}});
$('#fit-graph').addEventListener('click',resetGraph);$('#close-drawer').addEventListener('click',closeDrawer);$('#scrim').addEventListener('click',closeDrawer);

let dragging=false,last={x:0,y:0};svg.addEventListener('pointerdown',event=>{dragging=true;last={x:event.clientX,y:event.clientY};svg.setPointerCapture(event.pointerId);});svg.addEventListener('pointermove',event=>{if(!dragging)return;state.graphTransform.x+=event.clientX-last.x;state.graphTransform.y+=event.clientY-last.y;last={x:event.clientX,y:event.clientY};applyGraphTransform();});svg.addEventListener('pointerup',()=>dragging=false);svg.addEventListener('wheel',event=>{event.preventDefault();state.graphTransform.k=Math.max(.45,Math.min(2.5,state.graphTransform.k*(event.deltaY>0?.9:1.1)));applyGraphTransform();},{passive:false});
window.addEventListener('resize',()=>{if(state.grid)drawGrid(state.grid);});
function escapeHtml(value){return String(value).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}

loadFixtures();
