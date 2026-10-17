const $ = id => document.getElementById(id);
const groups = ['stand', 'ball', 'motion', 'setup'];
const defaults = {stand:'pitaya_v08', ball:'full', motion:'knitting', setup:'desk_side'};
const controls = ['mass', 'radius', 'distance', 'height', 'angle', 'drag', 'exit'];
let presets = {}, current, lastResult, requestSequence = 0, controlBaseline = {};
const dirtyControls = new Set();

function labels() {
  $('dragValue').textContent = $('drag').value;
  $('angleValue').textContent = $('angle').value;
}

function writeControls(c) {
  dirtyControls.clear();
  const values = {mass:(c.stand.mass_kg*1000).toFixed(1), radius:c.stand.support_radius_m*1000,
    distance:c.setup.distance_m*100, height:c.setup.hand_height_m*100,
    angle:c.setup.azimuth_deg, drag:c.stand.start_torque_Nm*1000, exit:c.ball.exit_height_fraction};
  for (const id of controls) {
    if (id === 'drag' || id === 'angle') {
      $(id).step='any';
      $(id).min=Math.min(id==='drag' ? .1 : 0,values[id]);
      $(id).max=Math.max(id==='drag' ? 4 : 345,values[id]);
    }
    if (id === 'exit' && ![0, -.65, .65].includes(values.exit)) {
      let option = $('exit').querySelector('option[data-custom]');
      if (!option) { option = document.createElement('option'); option.dataset.custom = 'true'; $('exit').appendChild(option); }
      option.value = String(values.exit); option.textContent = `Своя высота: ${values.exit}`;
    }
    $(id).value = values[id];
    // Number/range controls may round or clamp the displayed value. Preserve
    // the exact validated JSON unless the user actually changes that control.
    controlBaseline[id] = $(id).value;
  }
  for (const group of groups) {
    const match = Object.entries(presets).find(([key, value]) => key.split('/').length === 4 && value[group].name === c[group].name);
    $(group).value = match ? match[0].split('/')[groups.indexOf(group)] : 'custom';
  }
  labels();
}

function config() {
  const c = structuredClone(current);
  const changed = id => dirtyControls.has(id) || $(id).value !== controlBaseline[id];
  if (changed('mass')) c.stand.mass_kg = +$('mass').value/1000;
  if (changed('radius')) c.stand.support_radius_m = +$('radius').value/1000;
  if (changed('distance')) c.setup.distance_m = +$('distance').value/100;
  if (changed('height')) c.setup.hand_height_m = +$('height').value/100;
  if (changed('angle')) c.setup.azimuth_deg = +$('angle').value;
  if (changed('exit')) c.ball.exit_height_fraction = +$('exit').value;
  if (changed('drag')) {
    c.stand.start_torque_Nm = +$('drag').value/1000;
    c.stand.running_torque_Nm = +$('drag').value/2000;
  }
  return c;
}

function syncPreset(changed) {
  const key = groups.map(group => $(group).value === 'custom' ? defaults[group] : $(group).value).join('/');
  const next = structuredClone(presets[key]);
  if (current && changed) {
    const previous = config();
    for (const group of groups) if (group !== changed) next[group] = previous[group];
  }
  current = next; writeControls(current);
  $('json').value = JSON.stringify(current, null, 2);
}

function number(value, digits=3) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '—';
}

function setBusy(busy) {
  for (const id of [...groups,...controls,'json','run','runJson']) $(id).disabled=busy;
}

function chart(id, rows, key, color, height, units, mult=1) {
  const valid = rows.filter(row => typeof row[key] === 'number' && Number.isFinite(row[key]));
  if (!valid.length) { $(id).innerHTML = ''; return; }
  const max = Math.max(...valid.map(row => row[key]*mult), .001)*1.1;
  const end = Math.max(rows.at(-1).t_s, .000001);
  const path = valid.map((row, i) => (i?'L':'M')+(42+row.t_s/end*816).toFixed(2)+','+(height-30-row[key]*mult/max*(height-55)).toFixed(2)).join(' ');
  $(id).innerHTML = `<path d="M42 20V${height-30}H858" fill="none" stroke="#b7c8bc"/><path d="${path}" fill="none" stroke="${color}" stroke-width="2"/><text x="5" y="20" fill="#61736a" font-size="13">${max.toFixed(2)} ${units}</text><text x="42" y="${height-8}" fill="#61736a" font-size="13">0 с</text><text x="824" y="${height-8}" fill="#61736a" font-size="13">${number(end, 2)} с</text>`;
}

function scene(c) {
  const base=155, d=c.setup.distance_m, hh=c.setup.hand_height_m, br=c.ball.radius_z_m, z=c.stand.platform_height_m;
  const high=Math.max(hh,z+2*br,z+.123), low=Math.min(hh,0);
  const scale=Math.min(600/(d+.1),170/(high-low+.02)), ground=30+high*scale;
  const hx=base+d*scale, hy=ground-hh*scale, cy=ground-(z+br)*scale;
  const exit=ground-(z+br*(1+c.ball.exit_height_fraction))*scale;
  const section=c.ball.radius_x_m*c.ball.unwind_radius_ratio*Math.sqrt(1-c.ball.exit_height_fraction**2);
  $('scene').innerHTML = `<line x1="30" y1="${ground}" x2="860" y2="${ground}" stroke="#bac7bc"/><rect x="${base-.060*scale}" y="${ground-z*scale}" width="${.120*scale}" height="${z*scale}" rx="8" fill="#db3682"/><ellipse cx="${base}" cy="${cy}" rx="${c.ball.radius_x_m*scale}" ry="${br*scale}" fill="#cfb99d" stroke="#9a8064" stroke-width="2"/><line x1="${base}" y1="${ground-z*scale}" x2="${base}" y2="${ground-(z+.123)*scale}" stroke="#aaa89b" stroke-width="5"/><line x1="${base+section*scale}" y1="${exit}" x2="${hx}" y2="${hy}" stroke="#b52d6c" stroke-width="2"/><circle cx="${hx}" cy="${hy}" r="8" fill="#216148"/><text x="${hx+14}" y="${hy+5}" font-size="14" fill="#216148">Рабочая рука</text><text x="30" y="230" font-size="13" fill="#61736a">Боковая схема · ${Math.round(d*100)} см по горизонтали · высота руки ${Math.round(hh*100)} см</text>`;
}

function display(r) {
  const c=r.inputs, s=r.summary;
  $('peak').textContent=number(s.peak_tension_N);
  $('start').textContent=number(s.static_limits.start_tension_N);
  $('snag').textContent=number(s.static_limits.critical_snag_N,2);
  const events=Object.keys(s.first_events_s);
  const names={ball_slipping:'проскальзывание клубка',stand_sliding:'сдвиг подставки',stand_tipping:'начало наклона',stand_lifting:'отрыв от опоры',ball_lifting:'вертикальный отрыв клубка'};
  $('valid').className='warning '+(events.length?'':'good');
  $('valid').textContent=events.length ? 'Допущения нарушены: '+events.map(e=>names[e]+' на '+number(s.first_events_s[e],2)+' с').join('; ')+'. Дальнейшая кривая условна. Пик до первого события: '+number(s.peak_tension_before_first_event_N)+' Н.' : 'В этом сценарии расчёт не выявил сдвига, наклона или потери сцепления клубка.';
  const margin=s.minimum_support_margin_m === null ? null : s.minimum_support_margin_m*1000;
  $('extra').textContent=`95-й процентиль: ${number(s.p95_tension_N)} Н · максимальная слабина: ${number(s.max_slack_m*1000,1)} мм · минимальный запас до края опоры: ${number(margin,1)} мм`;
  const notes=[];
  if (Math.abs(s.static_limits.elevation_deg)>60) notes.push('Крутой угол тяги: возможен сход нити через верх клубка, точность модели ниже.');
  if (s.max_slack_m>.05) notes.push('Большой условный выбег: реальная свободная нить может оборачиваться вокруг клубка или зацепляться. Это верхняя оценка слабины, а не траектория петли.');
  if (Math.max(c.ball.radius_x_m,c.ball.radius_y_m)+c.ball.eccentricity_m>c.stand.platform_radius_m) notes.push('Клубок выступает за площадку; его деформация и реальная площадь опоры не рассчитаны.');
  $('notes').textContent=notes.join(' ');
  chart('plot',r.trace,'tension_N','#bb2c70',270,'Н');
  chart('slackPlot',r.trace,'slack_m','#327c63',150,'мм',1000);
  scene(c);
  const path=s.path_screen;
  $('path').textContent=path.min_clearance_m===null ? 'Для этой слабины оценка зазора ненадёжна.' : `Упрощённая проверка пути: ${path.min_clearance_m<=0?'возможен контакт с краем или декором':'зазор в выбранной траектории'}; минимум ${number(path.min_clearance_m*1000,1)} мм. Деформация клубка и петли нити не моделируются.`;
  if (c.stand.name.startsWith('PEACH')) $('path').textContent+=' Листья персика проверяются отдельно по STL; эта схема их не учитывает.';
}

async function run(c) {
  const serial=++requestSequence;
  lastResult=null;
  setBusy(true); $('saveResult').disabled=true;
  $('status').textContent='Считаю…';
  try {
    const response=await fetch('/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)});
    const r=await response.json();
    if (serial!==requestSequence) return;
    if (!response.ok) throw Error(r.error);
    // Adopt the server's validated, fully expanded config, not a partial JSON
    // object or stale form values. A failed run leaves the previous config intact.
    current=structuredClone(r.inputs); writeControls(current);
    $('json').value=JSON.stringify(current,null,2);
    display(r); lastResult=r; $('saveResult').disabled=false;
    $('status').textContent='Готово · исходные параметры и результат можно скачать.';
  } catch(e) {
    if (serial===requestSequence) $('status').textContent='Ошибка: '+e.message;
  } finally {
    if (serial===requestSequence) setBusy(false);
  }
}

function download(value,filename) {
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));
  a.download=filename; a.click(); URL.revokeObjectURL(a.href);
}

for (const id of groups) $(id).onchange=()=>{syncPreset(id);run(config());};
for (const id of controls) $(id).oninput=()=>{dirtyControls.add(id);labels();};
$('run').onclick=()=>run(config());
$('runJson').onclick=()=>{try { run(JSON.parse($('json').value)); } catch(e) { $('status').textContent='Ошибка JSON: '+e.message; }};
$('save').onclick=()=>download(config(),'yarn-stand-config.json');
$('saveResult').onclick=()=>{if(lastResult)download(lastResult,'yarn-stand-result.json');};
setBusy(true); $('save').disabled=$('saveResult').disabled=true;
fetch('/presets').then(response=>response.json()).then(value=>{
  presets=value;
  $('save').disabled=false;
  const requested=new URLSearchParams(location.search).get('stand');
  if (['pitaya_v08','pitaya_v09','peach_v13'].includes(requested)) $('stand').value=requested;
  syncPreset(); return run(config());
}).catch(e=>$('status').textContent='Не удалось загрузить параметры: '+e.message);
