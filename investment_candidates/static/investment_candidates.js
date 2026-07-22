"use strict";

const labels = {
  priority_candidate:"重点候选", watch_candidate:"跟踪候选", awaiting_verification:"等待验证",
  pricing_demanding:"定价偏贵", evidence_insufficient:"证据不足", not_current_candidate:"暂非候选",
  industry_opportunity:"产业机会", beneficiary_strength:"受益强度", earnings_conversion:"业绩兑现",
  expectation_gap:"预期差", valuation_context:"估值语境", catalyst_readiness:"催化准备",
  evidence_quality:"证据质量", risk_penalty:"风险惩罚"
};
const form=document.querySelector("#snapshot-form");
const statusNode=document.querySelector("#status");
const sections=[document.querySelector("#summary"),document.querySelector("#top-section"),document.querySelector("#universe-section")];
function text(value){return value===null||value===undefined||value===""?"—":String(value);}
function label(value){return labels[value]||text(value);}
function node(tag,value,className){const el=document.createElement(tag);if(className)el.className=className;el.textContent=text(value);return el;}
function clear(el){while(el.firstChild)el.removeChild(el.firstChild);}
function renderSummary(data){
  const grid=document.querySelector("#summary-grid");clear(grid);
  [["快照修订",data.snapshot_revision_id],["候选池修订",data.candidate_pool_revision_id],["规则版本",data.rule_version],["信息截止日",data.information_cutoff_date],["记录时间",data.recorded_at_utc],["完整成员数",data.member_count]].forEach(([key,value])=>{const wrap=node("div","");wrap.append(node("dt",key),node("dd",value));grid.appendChild(wrap);});
  sections[0].classList.remove("hidden");
}
function renderTop(members){
  const target=document.querySelector("#top-candidates");clear(target);
  const top=members.filter(item=>item.priority_ordinal!==null&&item.priority_ordinal!==undefined).sort((a,b)=>a.priority_ordinal-b.priority_ordinal).slice(0,3);
  if(!top.length)target.appendChild(node("p","当前快照没有重点或跟踪候选。","muted"));
  top.forEach(item=>{const card=node("article","","card");card.append(node("span",`#${item.priority_ordinal}`,"badge"),node("h3",item.stock_name||item.stock_code||item.beneficiary_id),node("p",label(item.candidate_status)),node("p",`最终分：${text(item.final_score)} · 业务质量：${text(item.business_quality_score)}`));target.appendChild(card);});
  sections[1].classList.remove("hidden");
}
function renderDetail(member){
  const target=document.querySelector("#member-details");clear(target);
  const section=node("section","","member-detail");
  section.append(node("h3",member.stock_name||member.stock_code||member.beneficiary_id),node("p",`候选状态：${label(member.candidate_status)}；产业受益：${text(member.beneficiary_kind)}`));
  const components=node("div","","components");
  (member.components||[]).forEach(component=>{const card=node("article","","component");card.append(node("strong",label(component.component_code)),node("p",`状态：${text(component.assessment_state)} / 验证：${text(component.verification_state)}`),node("p",`分值：${text(component.score_value)} · 权重：${text(component.rule_weight)} · 贡献：${text(component.contribution_amount)}`),node("p",`修订：${text(component.component_revision_id)}`,"muted"));components.appendChild(card);});
  section.appendChild(components);target.appendChild(section);
}
function renderUniverse(members){
  const body=document.querySelector("#universe-body");clear(body);clear(document.querySelector("#member-details"));
  members.forEach(member=>{const row=document.createElement("tr");[member.priority_ordinal,member.stock_name||member.stock_code||member.beneficiary_id,member.beneficiary_kind,label(member.candidate_status),member.final_score,member.business_quality_score,member.risk_penalty_points,(member.reason_codes||[]).join("、")].forEach(value=>row.appendChild(node("td",value)));row.tabIndex=0;row.addEventListener("click",()=>renderDetail(member));row.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();renderDetail(member);}});body.appendChild(row);});
  sections[2].classList.remove("hidden");
}
form.addEventListener("submit",async event=>{
  event.preventDefault();sections.forEach(section=>section.classList.add("hidden"));statusNode.className="";statusNode.textContent="正在读取固定快照……";
  const id=document.querySelector("#snapshot-id").value.trim();const cutoff=document.querySelector("#cutoff").value;const local=document.querySelector("#recorded-at").value;
  try{
    const recorded=new Date(`${local}Z`).toISOString();
    const url=`/investment-candidates/snapshot-revisions/${encodeURIComponent(id)}?as_of_cutoff=${encodeURIComponent(cutoff)}&as_of_recorded_at_utc=${encodeURIComponent(recorded)}`;
    const response=await fetch(url,{method:"GET",headers:{Accept:"application/json"}});const payload=await response.json();
    if(!response.ok)throw new Error(payload?.detail?.message||payload?.detail||"读取失败");
    renderSummary(payload);renderTop(payload.members||[]);renderUniverse(payload.members||[]);statusNode.textContent="快照已加载。完整公司池未被筛除。";
  }catch(error){statusNode.className="error";statusNode.textContent=`读取失败：${error.message}`;}
});
