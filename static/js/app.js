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
async function preparePlusPrompt(){const v=collectPlusData();if(v.mode==='generate'&&v.data.product_type==='part'){let packet=$('packetText')?.value.trim();if(!packet){const saved=await fetch('/api/data-packet?model='+encodeURIComponent(v.data.model)).then(r=>r.json());if(saved.found){packet=saved.output;if($('packetText'))$('packetText').value=packet;}}if(!packet)throw Error('请先粘贴并保存 Data Packet，再生成 Listing 指令');v.data.verified_data_packet=packet;}const r=await post('/api/chatgpt-prompt',{mode:v.mode,...v.data});$('promptPreview').value=r.prompt;return r.prompt;}
async function copyPlus(){try{const txt=await preparePlusPrompt();await navigator.clipboard.writeText(txt);alert('指令已复制，请粘贴到 ChatGPT');}catch(e){alert('复制失败：'+e.message+'。可手动复制预览框中的文字。');}}
if($('copyPromptBtn')) $('copyPromptBtn').onclick=copyPlus;
if($('openChatBtn')) $('openChatBtn').onclick=()=>window.open('https://chatgpt.com/','_blank','noopener,noreferrer');
if($('importBtn')) $('importBtn').onclick=async()=>{try{const v=collectPlusData();const result=await post('/api/import-listing',{mode:v.mode,input_data:v.data,output:$('importText').value});$('importStatus').textContent='已保存，文案编号：'+result.listing_id+'。前往文案库查看。';}catch(e){alert(e.message)}};
if($('analyzeBtn')) {$('analyzeBtn').textContent='① 生成 ChatGPT 分析指令';$('analyzeBtn').onclick=async()=>{try{const v=collectPlusData();const r=await post('/api/chatgpt-prompt',{mode:'analyze',...v.data});$('promptPreview').value=r.prompt;await navigator.clipboard.writeText(r.prompt);alert('分析指令已复制，请到 ChatGPT 核验商品资料。');}catch(e){alert(e.message)}};}
if($('generateBtn')) {$('generateBtn').disabled=false;$('generateBtn').textContent='② 生成 Listing 指令';$('generateBtn').onclick=copyPlus;}
if($('lookupBtn')) {$('lookupBtn').textContent='生成零件号核验指令';$('lookupBtn').onclick=copyPlus;}
if($('optimizeBtn')) {$('optimizeBtn').textContent='生成 ChatGPT 优化指令';$('optimizeBtn').onclick=copyPlus;}
if($('savePacketBtn')) $('savePacketBtn').onclick=async()=>{try{const v=collectPlusData();const r=await post('/api/data-packet',{input_data:v.data,output:$('packetText').value});$('packetStatus').textContent='已保存 Data Packet #'+r.id;}catch(e){alert(e.message)}};
if($('loadPacketBtn')) $('loadPacketBtn').onclick=async()=>{try{const v=collectPlusData();const r=await fetch('/api/data-packet?model='+encodeURIComponent(v.data.model)).then(x=>x.json());if(!r.found)throw Error('未找到该零件号的 Data Packet');$('packetText').value=r.output;$('packetStatus').textContent='已读取 Data Packet #'+r.id;}catch(e){alert(e.message)}};
if($('copyPacketBtn')) $('copyPacketBtn').onclick=async()=>{const t=$('packetText').value;if(!t)return alert('Data Packet 为空');await navigator.clipboard.writeText(t);alert('已复制 Data Packet')};
function librarySection(title,content,kind='text'){
 const section=document.createElement('section');section.className='listing-section';
 const top=document.createElement('div');top.className='listing-section-head';
 const heading=document.createElement('h3');heading.textContent=title;top.appendChild(heading);
 const button=document.createElement('button');button.className='secondary';button.textContent='复制此部分';button.onclick=async()=>{await navigator.clipboard.writeText(Array.isArray(content)?content.join(' '):String(content||''));button.textContent='已复制 ✓';setTimeout(()=>button.textContent='复制此部分',1300)};top.appendChild(button);section.appendChild(top);
 if(Array.isArray(content)){const wrap=document.createElement('div');wrap.className='tag-list';content.forEach(t=>{const tag=document.createElement('span');tag.className='tag';tag.textContent=t;wrap.appendChild(tag)});section.appendChild(wrap)}
 else {const body=document.createElement('div');body.className='listing-body';body.textContent=content||'暂无内容';section.appendChild(body)}
 return section;
}
function parseListingOutput(out){if(out&&typeof out.raw_output==='string'){let raw=out.raw_output.trim();raw=raw.replace(/^```(?:json)?\s*/i,'').replace(/\s*```$/,'');try{return JSON.parse(raw)}catch(e){return {unparsed:out.raw_output}}}return out||{};}
let currentLibraryText='';
document.querySelectorAll('.viewListing').forEach(btn=>btn.onclick=async()=>{try{
 const r=await fetch('/api/listings/'+btn.dataset.id);if(!r.ok)throw Error('获取失败');const j=await r.json();const out=parseListingOutput(j.output_data);const holder=$('librarySections');holder.replaceChildren();
 $('detailTitle').textContent=j.input_data.product_name||j.title;$('detailMeta').textContent='型号 / 零件号：'+(j.model||'—')+' · 记录 #'+j.id;
 currentLibraryText=JSON.stringify(out,null,2);$('libraryOutput').textContent=currentLibraryText;
 if(out.unparsed){holder.appendChild(librarySection('原始文案（无法解析为 JSON）',out.unparsed));}
 else if(Array.isArray(out.listings)&&out.listings.length){
 holder.appendChild(librarySection('Part0｜Compatibility Analysis · 事实与适配核验',out.analysis_summary||''));
 out.listings.forEach((v,i)=>{
 if(out.listings.length>1){const sub=document.createElement('h2');sub.textContent='配置 '+(i+1)+'｜'+(v.configuration||'');holder.appendChild(sub)}
 [['Part1｜俄文 SEO 标题',v.part1_title_ru],['Part2｜标题中文翻译',v.part2_title_zh],['Part3｜俄文商品描述',v.part3_description_ru],['Part4｜商品描述中文翻译',v.part4_description_zh],['Part5｜俄文 SEO 标签',v.part5_hashtags],['Part6｜标签中文说明',v.part6_hashtags_zh],['Part7｜Комплектация · 俄文包装清单',v.part7_packaging_ru],['Part8｜包装清单中文',v.part8_packaging_zh]].forEach(([name,value])=>holder.appendChild(librarySection(name,value)));
 });
 if(out.risk_check)holder.appendChild(librarySection('合规与风险检查',JSON.stringify(out.risk_check,null,2)));
 }else{holder.appendChild(librarySection('已保存内容',JSON.stringify(out,null,2)))}
 $('libraryDetail').classList.remove('hidden');$('libraryDetail').scrollIntoView({behavior:'smooth'});
 }catch(e){alert(e.message)}});
if($('copyLibrary')) $('copyLibrary').onclick=async()=>{await navigator.clipboard.writeText(currentLibraryText);alert('已复制完整 JSON')};
