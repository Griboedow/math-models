// Controller regression tests. Real browser smoke checks cover DOM rendering.
// Run: node --test tests/test_ui.js (Node 18+).
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const base = JSON.parse(fs.readFileSync(path.join(root,'examples/peach_v13.json'),'utf8'));

function harness() {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) {
      let value='';
      const e={textContent:'',innerHTML:'',disabled:false,dataset:{},
        querySelector(){return this.customOption || null;},
        appendChild(option){this.customOption=option;},click(){}};
      Object.defineProperty(e,'value',{get(){return value;},set(v){
        if (id==='drag' && e.step!=='any') v=Math.max(.1,Math.min(4,Math.round(Number(v)*10)/10));
        if (id==='angle' && e.step!=='any') v=Math.max(0,Math.min(345,Math.round(Number(v)/15)*15));
        value=String(v);
      }});
      elements.set(id,e);
    }
    return elements.get(id);
  }
  const context=vm.createContext({document:{getElementById:element,createElement:()=>({dataset:{},click(){}})},
    structuredClone,URLSearchParams,location:{search:''},fetch:()=>new Promise(()=>{})});
  vm.runInContext(fs.readFileSync(path.join(root,'yarnstand/ui.js'),'utf8'),context);
  const get=code=>vm.runInContext(code,context);
  context.fixture=structuredClone(base);
  get("presets={'peach_v13/full/knitting/desk_side':fixture}; current=structuredClone(fixture);writeControls(current)");
  return {context,element,get,json:code=>JSON.parse(get(`JSON.stringify(${code})`))};
}

function result(config) {
  return {inputs:structuredClone(config),summary:{peak_tension_N:.1,p95_tension_N:.08,max_slack_m:0,
    minimum_support_margin_m:.04,first_events_s:{},peak_tension_before_first_event_N:.1,
    static_limits:{start_tension_N:.03,critical_snag_N:1.6,elevation_deg:10},
    path_screen:{min_clearance_m:.03}},trace:[{t_s:.01,tension_N:.1,slack_m:0}]};
}

test('rounded/clamped controls do not silently change imported JSON',()=>{
  const h=harness();
  h.get('current.stand.start_torque_Nm=.00027;current.stand.running_torque_Nm=.00011;current.setup.azimuth_deg=7;current.ball.exit_height_fraction=-.8;writeControls(current)');
  const c=h.json('config()');
  assert.equal(c.stand.mass_kg,base.stand.mass_kg);
  assert.equal(c.stand.start_torque_Nm,.00027);
  assert.equal(c.stand.running_torque_Nm,.00011);
  assert.equal(c.setup.azimuth_deg,7);
  assert.equal(c.ball.exit_height_fraction,-.8);
  assert.equal(h.element('dragValue').textContent,'0.27');
  assert.equal(h.element('angleValue').textContent,'7');
});

test('explicit edit back to a displayed rounded value is applied',()=>{
  const h=harness();h.element('mass').value='400';h.element('mass').oninput();
  h.element('mass').value='300.3';h.element('mass').oninput();
  assert.equal(h.json('config()').stand.mass_kg,.3003);
});

test('editing another field preserves independent running friction',()=>{
  const h=harness();h.get('current.stand.running_torque_Nm=.00012;writeControls(current)');
  h.element('height').value='-5';
  assert.equal(h.json('config()').setup.hand_height_m,-.05);
  assert.equal(h.json('config()').stand.running_torque_Nm,.00012);
  h.element('drag').value='1.2';
  assert.equal(h.json('config()').stand.running_torque_Nm,.0006);
});

test('partial JSON uses validated server inputs and synchronizes the form',async()=>{
  const h=harness();const c=structuredClone(base);c.stand.mass_kg=.4123;c.setup.hand_height_m=-.05;
  h.context.fetch=async()=>({ok:true,json:async()=>result(c)});
  await h.get('run({stand:{mass_kg:.4123}})');
  assert.deepEqual(h.json('config()'),c);
  assert.equal(h.element('mass').value,'412.3');
  assert.equal(h.element('height').value,'-5');
  assert.equal(h.element('saveResult').disabled,false);
});

test('rejected JSON leaves valid parameters intact and stale result unavailable',async()=>{
  const h=harness();h.get('lastResult={old:true}');
  h.context.fetch=async()=>({ok:false,json:async()=>({error:'Invalid parameter'})});
  await h.get('run({stand:{mass_kg:-1}})');
  assert.deepEqual(h.json('config()'),base);
  assert.equal(h.get('lastResult'),null);
  assert.equal(h.element('saveResult').disabled,true);
  assert.match(h.element('status').textContent,/Invalid parameter/);
});

test('a late failed request cannot overwrite a newer successful run',async()=>{
  const h=harness();const requests=[];
  h.context.fetch=()=>new Promise((resolve,reject)=>requests.push({resolve,reject}));
  const first=h.get('run({})'),second=h.get('run({})');
  requests[1].resolve({ok:true,json:async()=>result(base)});await second;
  requests[0].reject(new Error('old request failed'));await first;
  assert.match(h.element('status').textContent,/Готово/);
  assert.equal(h.element('saveResult').disabled,false);
});

test('an in-flight response cannot erase edits made in an enabled editor',async()=>{
  const h=harness();let finish;
  h.context.fetch=()=>new Promise(resolve=>{finish=resolve;});
  const pending=h.get('run({})');
  assert.equal(h.element('json').disabled,true);
  assert.equal(h.element('mass').disabled,true);
  finish({ok:true,json:async()=>result(base)});await pending;
  assert.equal(h.element('json').disabled,false);
  assert.equal(h.element('mass').disabled,false);
});

test('undefined support margin renders the warning instead of throwing',()=>{
  const h=harness();const r=result(base);
  r.summary.minimum_support_margin_m=null;r.summary.static_limits.critical_snag_N=null;
  r.summary.first_events_s={stand_lifting:.1};r.summary.peak_tension_before_first_event_N=null;
  h.context.response=r;h.get('display(response)');
  assert.match(h.element('valid').textContent,/отрыв от опоры/);
  assert.match(h.element('extra').textContent,/— мм/);
});

test('switching the ball preserves custom stand values and exit height resets only for the ball',()=>{
  const h=harness();
  h.context.empty=structuredClone(base);h.context.empty.ball.name='Empty';
  h.get("presets['peach_v13/nearly_empty/knitting/desk_side']=empty;current.stand.running_torque_Nm=.00012;writeControls(current)");
  h.element('ball').value='nearly_empty';h.get("syncPreset('ball')");
  assert.equal(h.json('config()').ball.name,'Empty');
  assert.equal(h.json('config()').stand.running_torque_Nm,.00012);
});
