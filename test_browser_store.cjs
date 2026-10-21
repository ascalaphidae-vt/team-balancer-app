// Pure protocol tests: no browser, server, packages, or network required.
const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const code = readFileSync(__dirname + '/browser_store/index.html', 'utf8').split('<script>')[1].split('</script>')[0];
function fixture(raw=null, fail=null) {
  let data=raw, writes=0;
  const events={}, messages=[], status={textContent:'',className:''};
  const parent={postMessage:m=>messages.push(m)};
  const window={parent,addEventListener:(type,fn)=>events[type]=fn,localStorage:{
    getItem:()=>{if(fail==='read')throw Error('blocked');return data},
    setItem:(_,value)=>{if(fail==='write')throw Error('quota');data=value;writes++}
  }};
  vm.runInNewContext(code,{window,document:{getElementById:()=>status}});
  return {render:args=>events.message({source:parent,data:{type:'streamlit:render',args}}),
    external:raw=>{data=raw;events.storage({key:'splatoon-team-balancer:v2',newValue:raw})},
    replace:raw=>{data=raw},read:()=>data,writes:()=>writes,status,messages};
}
const payload=JSON.stringify({updated_at:'2026-10-21T20:00:00+09:00',revision:1});
let cases=0;
{
  const f=fixture('old data');
  f.render({token:'a',payload});
  assert.equal(f.read(),'old data'); // Never overwrite during hydration.
  assert.equal(f.messages.at(-1).value.raw,'old data');
  f.render({token:'a',payload});
  assert.equal(f.read(),payload);
  f.render({token:'a',payload});
  assert.equal(f.writes(),1); // A render is not another write.
  assert.match(f.status.textContent,/保存済み/); cases++;
}
{
  const f=fixture(payload);
  f.render({token:'a',payload:null});
  f.render({token:'b',payload:null}); // A new server session rehydrates.
  assert.equal(f.messages.at(-1).value.token,'b');
  assert.equal(f.messages.at(-1).value.raw,payload);
  assert.equal(f.writes(),0); cases++;
}
{
  const f=fixture(payload);
  f.render({token:'a',payload:null});
  f.external('newer data from another tab');
  f.render({token:'a',payload:'outdated edit'});
  assert.equal(f.writes(),0);
  assert.match(f.status.textContent,/別のタブ/); cases++;
}
{
  const f=fixture(payload);
  f.render({token:'a',payload:null});
  f.replace('missed storage event');
  f.render({token:'a',payload:'outdated edit'});
  assert.equal(f.writes(),0);
  assert.match(f.status.textContent,/自動保存を停止/); cases++;
}
{
  const f=fixture(null,'read');
  f.render({token:'a',payload:null});
  assert.equal(f.messages.at(-1).value.error,'storage_unavailable');
  f.render({token:'a',payload});
  assert.equal(f.writes(),0); cases++;
}
{
  const f=fixture(null,'write');
  f.render({token:'a',payload:null});
  f.render({token:'a',payload});
  assert.equal(f.read(),null);
  assert.match(f.status.textContent,/自動保存に失敗/); cases++;
}
console.log(`${cases} browser storage protocol tests passed.`);
