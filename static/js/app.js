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

if($("analyzeBtn")) $("analyzeBtn").onclick=async()=>{
 try{
  const data={product_type:productType,brand:$("brand").value,model:$("model").value,product_name:$("product_name").value,info:$("info").value,brand_mode:brandMode,configurations:configs,use_web:$("useWeb").checked};
  $("analyzeBtn").disabled=true;$("analyzeBtn").textContent="AI分析中…";
  const result=await post("/api/analyze",data);window.analysis=result;show("analysis",result);$("generateBtn").disabled=false;
 }catch(e){alert(e.message)}finally{$("analyzeBtn").disabled=false;$("analyzeBtn").textContent="① AI分析商品"}
};
if($("generateBtn")) $("generateBtn").onclick=async()=>{
 try{
  const data={product_type:productType,brand:$("brand").value,model:$("model").value,product_name:$("product_name").value,info:$("info").value,brand_mode:brandMode,configurations:configs,analysis:window.analysis,use_web:$("useWeb").checked};
  $("generateBtn").disabled=true;$("generateBtn").textContent="生成中…";show("output","AI正在生成…");const result=await post("/api/generate",data);show("output",result);
 }catch(e){alert(e.message)}finally{$("generateBtn").disabled=false;$("generateBtn").textContent="② 生成 Listing"}
};
if($("lookupBtn")) $("lookupBtn").onclick=async()=>{try{const j=await post("/api/part-lookup",{part_number:$("partNumber").value,notes:$("partNotes").value});show("output",j)}catch(e){alert(e.message)}};
if($("optimizeBtn")) $("optimizeBtn").onclick=async()=>{try{const j=await post("/api/optimize",{meta:$("meta").value,brand_mode:brandMode,title:$("oldTitle").value,description:$("oldDesc").value,hashtags:$("oldTags").value,notes:$("notes").value});show("output",j)}catch(e){alert(e.message)}};
