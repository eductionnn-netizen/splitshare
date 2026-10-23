'use strict';
const $ = (id) => document.getElementById(id);
let groups = [], group = null, deleting = null, expenseRequestId = null;
let selectionVersion = 0;
const money = (value) => new Intl.NumberFormat('ru-RU', {style:'currency', currency:'RUB', minimumFractionDigits:value % 100 ? 2 : 0, maximumFractionDigits:2}).format(value / 100);
const today = () => {const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;};
const dateLabel = (value) => new Intl.DateTimeFormat('ru-RU', {day:'numeric',month:'short'}).format(new Date(value+'T12:00:00'));
function node(tag, className, content) {const el=document.createElement(tag); if(className) el.className=className; if(content!==undefined) el.textContent=content; return el;}
function avatar(name) {return node('span', 'avatar tone-'+(group ? group.members.indexOf(name)%5 : 0), name.slice(0,1).toLocaleUpperCase());}
function showError(message) {$('alert').textContent=message; $('alert').hidden=!message;}
async function api(path, options={}) {
 const result=await fetch(path,{...options,headers:{'Content-Type':'application/json',...options.headers}});
 let data; try {data=await result.json();} catch {throw new Error('Сервер вернул неожиданный ответ. Попробуйте ещё раз.');}
 if(!result.ok) throw new Error(data.error || 'Не удалось выполнить запрос'); return data;
}
async function formAction(form, action) {
 const button=form.querySelector('[type=submit]'), error=form.querySelector('.form-error');
 if(button.disabled) return; button.disabled=true; error.hidden=true;
 try {await action();} catch(e) {error.textContent=e.message || 'Не удалось сохранить данные';error.hidden=false;} finally {button.disabled=false;}
}
function renderGroups() {
 const list=$('group-list');list.replaceChildren();
 for(const item of groups){const b=node('button','group-button'+(group?.id===item.id?' active':''));b.type='button';b.append(node('span','',item.name));b.setAttribute('aria-pressed',String(group?.id===item.id));b.addEventListener('click',()=>selectGroup(item.id));list.append(b);}
}
async function selectGroup(id) {
 const version=++selectionVersion;
 try {const data=await api('/api/groups/'+encodeURIComponent(id));if(version!==selectionVersion)return;group=data;showError('');render();} catch(e){if(version===selectionVersion)showError(e.message);}
}
function render() {
 renderGroups();$('welcome').hidden=!!group;$('workspace').hidden=!group;
 if(!group) return;
 $('breadcrumb').textContent=group.name;$('group-name').textContent=group.name;
 $('member-avatars').replaceChildren(...group.members.slice(0,5).map(avatar));
 $('member-summary').textContent=group.members.length+' '+plural(group.members.length,['участник','участника','участников']);
 $('total').textContent=money(group.total_kopecks);$('expense-count').textContent=group.expenses.length;$('tab-count').textContent=group.expenses.length;
 const sorted=[...group.expenses].sort((a,b)=>b.date.localeCompare(a.date));
 $('last-expense').textContent=sorted.length?'Последний расход — '+dateLabel(sorted[0].date):'Пока нет расходов';
 const transfers=group.result.transfers;
 $('debt-total').textContent=money(transfers.reduce((sum,t)=>sum+t.amount_kopecks,0));
 $('transfer-count').textContent=transfers.length?transfers.length+' '+plural(transfers.length,['перевод между участниками','перевода между участниками','переводов между участниками']):'Нет задолженности';
 const expenses=$('expenses');expenses.replaceChildren();
 if(!sorted.length){const empty=node('div','empty');empty.append(node('strong','','Расходов пока нет'),node('span','','Нажмите «Добавить расход», чтобы записать покупку.'));expenses.append(empty);}
 for(const e of sorted){
  const row=node('article','expense-row'),info=node('div','expense-info'),amount=node('div','expense-money',money(e.amount_kopecks));
  info.append(node('div','expense-title',e.title),node('div','expense-subtitle',dateLabel(e.date)+' · Оплата: '+e.payer));
  amount.append(node('small','',e.participants.length+' '+plural(e.participants.length,['участник','участника','участников'])));
  const remove=node('button','delete-expense','×');remove.setAttribute('aria-label','Удалить расход «'+e.title+'»');remove.addEventListener('click',()=>{deleting=e;$('delete-description').textContent='«'+e.title+'» · '+money(e.amount_kopecks);openDialog('delete-dialog');});
  row.append(info,amount,remove);expenses.append(row);
 }
 const balances=$('balances');balances.replaceChildren();
 for(const name of group.members){const balance=group.result.balances_kopecks[name],row=node('div','balance-row'),info=node('div','balance-name',name),result=node('div','balance-result'+(balance<0?' negative':''),money(Math.abs(balance)));info.append(node('small','','Оплачено '+money(group.result.paid_kopecks[name])+' · Доля '+money(group.result.shares_kopecks[name])));result.append(node('small','',balance>0?'получит':balance<0?'вернёт':'ничего не должен'));row.append(avatar(name),info,result);balances.append(row);}
 const list=$('transfers');list.replaceChildren();
 if(!transfers.length){const empty=node('div','empty');empty.append(node('strong','','Нет задолженности'),node('span','','Переводы не нужны'));list.append(empty);}
 for(const t of transfers){const row=node('div','transfer'),people=node('div','transfer-person');people.append(avatar(t.from),node('span','',t.from),node('span','transfer-arrow','→'),node('span','',t.to));row.append(people,node('strong','',money(t.amount_kopecks)));list.append(row);}
}
function plural(n, forms){return forms[n%10===1&&n%100!==11?0:n%10>=2&&n%10<=4&&(n%100<12||n%100>14)?1:2];}
function openDialog(id){const dialog=$(id);dialog.querySelector('.form-error').hidden=true;dialog.showModal();}
function createGroup(){ $('group-form').reset();openDialog('group-dialog'); }
$('new-group').addEventListener('click',createGroup);$('welcome-create').addEventListener('click',createGroup);
for(const button of document.querySelectorAll('.close-dialog'))button.addEventListener('click',()=>button.closest('dialog').close());
$('group-form').addEventListener('submit',event=>{event.preventDefault();formAction(event.currentTarget,async()=>{
 const members=$('group-members').value.split('\n').map(s=>s.trim()).filter(Boolean);
 const created=await api('/api/groups',{method:'POST',body:JSON.stringify({name:$('group-title').value,members})});
 selectionVersion++;group=created;groups.push(created);$('group-dialog').close();render();showError('');
});});
$('add-expense').addEventListener('click',()=>{
 $('expense-form').reset();expenseRequestId=crypto.randomUUID();$('expense-date').value=today();
 $('expense-payer').replaceChildren(...group.members.map(name=>{const option=node('option','',name);option.value=name;return option;}));
 $('participant-options').replaceChildren(...group.members.map(name=>{const label=node('label'),input=node('input');input.type='checkbox';input.value=name;input.checked=true;label.append(input,document.createTextNode(name));return label;}));openDialog('expense-dialog');
});
$('expense-form').addEventListener('submit',event=>{event.preventDefault();formAction(event.currentTarget,async()=>{
 const raw=$('expense-amount').value.trim().replace(',','.');
 if(!/^\d{1,10}(\.\d{1,2})?$/.test(raw))throw new Error('Введите сумму в рублях, например 1250,50. Не более двух знаков после запятой.');
 const [whole,cents='']=raw.split('.'),amount=Number(whole)*100+Number(cents.padEnd(2,'0'));
 if(amount<=0||amount>100000000000)throw new Error('Сумма должна быть больше нуля и не превышать 1 млрд рублей');
 const participants=[...$('participant-options').querySelectorAll('input:checked')].map(e=>e.value);
 if(!participants.length)throw new Error('Выберите хотя бы одного участника расхода');
 group=await api('/api/groups/'+group.id+'/expenses',{method:'POST',body:JSON.stringify({id:expenseRequestId,title:$('expense-title').value,date:$('expense-date').value,payer:$('expense-payer').value,amount_kopecks:amount,participants})});
 $('expense-dialog').close();render();showError('');
});});
$('delete-form').addEventListener('submit',event=>{event.preventDefault();formAction(event.currentTarget,async()=>{
 group=await api('/api/groups/'+group.id+'/expenses/'+encodeURIComponent(deleting.id),{method:'DELETE'});$('delete-dialog').close();deleting=null;render();
});});
function selectTab(name){for(const key of ['expenses','balances']){const selected=key===name;$(key+'-tab').classList.toggle('active',selected);$(key+'-tab').setAttribute('aria-selected',String(selected));$(key+'-tab').tabIndex=selected?0:-1;$(key+'-panel').hidden=!selected;}}
for(const name of ['expenses','balances']){$(name+'-tab').addEventListener('click',()=>selectTab(name));$(name+'-tab').addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const other=event.key==='Home'?'expenses':event.key==='End'?'balances':name==='expenses'?'balances':'expenses';selectTab(other);$(other+'-tab').focus();}});}
$('export').addEventListener('click',()=>{const payload={name:group.name,members:group.members,expenses:group.expenses};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='splitshare-'+group.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('load-example').addEventListener('click',async()=>{const button=$('load-example');if(button.disabled)return;button.disabled=true;
 try {let created=await api('/api/groups',{method:'POST',body:JSON.stringify({name:'Выходные в Петербурге',members:['Аня','Борис','Вика']})});groups.push(created);group=created;selectionVersion++;
 const examples=[{title:'Ужин в кафе',payer:'Аня',amount_kopecks:300000},{title:'Такси до дома',payer:'Борис',amount_kopecks:90000}];
 for(const expense of examples){group=await api('/api/groups/'+group.id+'/expenses',{method:'POST',body:JSON.stringify({...expense,id:crypto.randomUUID(),date:today(),participants:group.members})});}render();showError('');
 }catch(e){showError(e.message);if(group)render();}finally{button.disabled=false;}
});
(async()=>{try{groups=await api('/api/groups');if(groups.length)await selectGroup(groups[0].id);else render();}catch(e){render();showError('Не удалось загрузить группы. Проверьте, что сервер запущен, и обновите страницу.');}})();
