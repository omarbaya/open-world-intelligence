/* OPEN WORLD V3: adapter for the unchanged Claude Dashboard page.
   Emulates only dash.data/onData/setLink etc. The private Anthropic diary is
   not copied nor public; it remains disabled unless backed by private auth. */
(function(){
const names={oggi:'./data/oggi.json',storico:'./data/storico.json'};
const state={},listeners=[];
Object.keys(names).forEach(id=>state[id]={status:'loading',data:[],message:'',refreshing:false,meta:[]});
function notify(){listeners.forEach(fn=>{try{fn()}catch(e){console.error('dashboard listener',e)}})}
window.dash={
  data:id=>state[id]||{status:'missing',data:[],message:'Unknown dataset',refreshing:false,meta:[]},
  onData:fn=>{listeners.push(fn);try{fn()}catch(e){console.error(e)}},
  setLink:name=>{try{history.replaceState(null,'','#'+name)}catch(e){}},
  refresh:()=>{Object.keys(names).forEach(load)}, params:()=>({}),setParams:()=>{},resetParams:()=>{},
  calc:()=>{},loader:()=>{},colors:['#1f6fd1','#c98f00','#2e9e6a','#8a5cd1','#d14f6f','#3a9fb5','#7a8a2e','#9a6b4a']};
function load(id){const url=names[id];fetch(url+'?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(rows=>{
 const data=Array.isArray(rows)?rows:(rows.rows||rows.data||[]);
 state[id]={status:'ok',data,columns:data.length?Object.keys(data[0]):[],message:'',refreshing:false,meta:[]};notify();
}).catch(e=>{state[id]={status:'error',data:[],message:String(e),refreshing:false,meta:[]};notify()})}
Object.keys(names).forEach(load);
let timer;window.addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(notify,100)});
})();
