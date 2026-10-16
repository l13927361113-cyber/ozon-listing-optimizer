const $=id=>document.getElementById(id);
function show(id,data){const el=$(id);el.classList.remove("hidden");el.innerHTML="<div class='json'>"+escapeHtml(typeof data==="string"?data:JSON.stringify(data,null,2))+"</div>";}
function escapeHtml(s){return String(s).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");}
async function post(url,data){const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});const j=await r.json();if(!r.ok)throw new Error(j.error||"请求失败");return j;}

let productType="machine",brandMode="with_brand";
document.querySelectorAll("[data-type]").forEach(b=>b.onclick=()=>{document.querySelectorAll("[data-type]").forEach(x=>x.classList.remove("active"));b.classList.add("active");productType=b.dataset.type;});
if($("withBrand")) $("withBrand").onclick=()=>{brandMode="with_brand";$("withBrand").classList.add("active");$("noBrand").classList.remove("active")};
if($("noBrand")) $("noBrand").onclick=()=>{brandMode="no_brand";$("noBrand").classList.add("active");$("withBrand").classList.remove("active")};

let configs=[];
function renderConfigs(){if(!$("configList"))return;$("configList").innerHTML=configs.map((x,i)=>`<div class="config"><input value="${escapeHtml(x)}" data-i="${i}"><button onclick="removeConfig(${i})">删除</button></div>`).join("");document.querySelectorAll("#configList input").forEach(e=>e.oninput=()=>configs[e.dataset.i]=e.value);}
window.removeConfig=i=>{configs.splice(i,1);renderConfigs()};
if($("addConfig")) $("addConfig").onclick=()=>{configs.push("");renderConfigs()};

if(false && $("analyzeBtn")) $("analyzeBtn").onclick=async()=>{
 try{
  const data={product_type:productType,brand:$("brand").value,model:$("model").value,product_name:$("product_name").value,info:$("info").value,brand_mode:brandMode,configurations:configs,use_web:$("useWeb").checked};
  $("analyzeBtn").disabled=true;$("analyzeBtn").textContent="AI分析中…";
  const result=await post("/api/analyze",data);window.analysis=result;show("analysis",result);$("generateBtn").disabled=false;
 }catch(e){alert(e.message)}finally{$("analyzeBtn").disabled=false;$("analyzeBtn").textContent="① AI分析商品"}
};
if(false && $("generateBtn")) $("generateBtn").onclick=async()=>{
 try{
  const data={product_type:productType,brand:$("brand").value,model:$("model").value,product_name:$("product_name").value,info:$("info").value,brand_mode:brandMode,configurations:configs,analysis:window.analysis,use_web:$("useWeb").checked};
  $("generateBtn").disabled=true;$("generateBtn").textContent="生成中…";show("output","AI正在生成…");const result=await post("/api/generate",data);show("output",result);
 }catch(e){alert(e.message)}finally{$("generateBtn").disabled=false;$("generateBtn").textContent="② 生成 Listing"}
};
if(false && $("lookupBtn")) $("lookupBtn").onclick=async()=>{try{const j=await post("/api/part-lookup",{part_number:$("partNumber").value,notes:$("partNotes").value});show("output",j)}catch(e){alert(e.message)}};
if(false && $("optimizeBtn")) $("optimizeBtn").onclick=async()=>{try{const j=await post("/api/optimize",{meta:$("meta").value,brand_mode:brandMode,title:$("oldTitle").value,description:$("oldDesc").value,hashtags:$("oldTags").value,notes:$("notes").value});show("output",j)}catch(e){alert(e.message)}};

// ChatGPT Plus assisted mode: all prompts generated locally on server, no paid API calls.
function collectPlusData(){
 if($("partNumber")) return {mode:"part_lookup",data:{part_number:$("partNumber").value,notes:$("partNotes").value}};
 if($("oldTitle")) return {mode:"optimize",data:{meta:$("meta").value,brand_mode:brandMode,title:$("oldTitle").value,description:$("oldDesc").value,hashtags:$("oldTags").value,notes:$("notes").value}};
 return {mode:"generate",data:{product_type:productType,brand:$("brand").value,model:$("model").value,product_name:$("product_name").value,info:$("info").value,brand_mode:brandMode,configurations:configs,use_web:$("useWeb").checked}};
}
async function preparePlusPrompt(){const v=collectPlusData();const r=await post('/api/chatgpt-prompt',{mode:v.mode,...v.data});$('promptPreview').value=r.prompt;return r.prompt;}
async function copyPlus(){try{const txt=await preparePlusPrompt();await navigator.clipboard.writeText(txt);alert('指令已复制，请粘贴到 ChatGPT');}catch(e){alert('复制失败：'+e.message+'。可手动复制预览框中的文字。');}}
if($('copyPromptBtn')) $('copyPromptBtn').onclick=copyPlus;
if($('openChatBtn')) $('openChatBtn').onclick=()=>window.open('https://chatgpt.com/','_blank','noopener,noreferrer');
if($('importBtn')) $('importBtn').onclick=async()=>{try{const v=collectPlusData();const result=await post('/api/import-listing',{mode:v.mode,input_data:v.data,output:$('importText').value});$('importStatus').textContent='已保存，文案编号：'+result.listing_id+'。前往文案库查看。';}catch(e){alert(e.message)}};
if($('analyzeBtn')) {$('analyzeBtn').textContent='① 生成 ChatGPT 分析指令';$('analyzeBtn').onclick=async()=>{try{const v=collectPlusData();const r=await post('/api/chatgpt-prompt',{mode:'analyze',...v.data});$('promptPreview').value=r.prompt;await navigator.clipboard.writeText(r.prompt);alert('分析指令已复制，请到 ChatGPT 核验商品资料。');}catch(e){alert(e.message)}};}
if($('generateBtn')) {$('generateBtn').disabled=false;$('generateBtn').textContent='② 生成 Listing 指令';$('generateBtn').onclick=copyPlus;}
if($('lookupBtn')) {$('lookupBtn').textContent='生成零件号核验指令';$('lookupBtn').onclick=copyPlus;}
if($('optimizeBtn')) {$('optimizeBtn').textContent='生成 ChatGPT 优化指令';$('optimizeBtn').onclick=copyPlus;}
document.querySelectorAll('.viewListing').forEach(btn=>btn.onclick=async()=>{try{const r=await fetch('/api/listings/'+btn.dataset.id);if(!r.ok)throw Error('获取失败');const j=await r.json();$('libraryDetail').classList.remove('hidden');$('libraryOutput').textContent=j.output_data.raw_output||JSON.stringify(j.output_data,null,2);$('libraryDetail').scrollIntoView({behavior:'smooth'});}catch(e){alert(e.message)}});
if($('copyLibrary')) $('copyLibrary').onclick=async()=>{try{await navigator.clipboard.writeText($('libraryOutput').textContent);alert('已复制');}catch(e){alert(e.message)}};
