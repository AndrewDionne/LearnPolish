import {useEffect,useState} from 'react';
import {FAMILY_API,familyRequest} from './api';
import type {FamilyConnection,FamilyGroup,FamilySummary} from './api';

type Props={onConnection:(connection:FamilyConnection|null)=>void;
            onSummary:(summary:FamilySummary|null)=>void;
            syncMessage:string};

export default function FamilyPanel({onConnection,onSummary,syncMessage}:Props){
  const [token,setToken]=useState(()=>{try{return sessionStorage.getItem('ptp-v2-family-session')||'';}catch{return '';}});
  const [group,setGroup]=useState(()=>{try{return Number(sessionStorage.getItem('ptp-v2-family-group'))||0;}catch{return 0;}});
  const [enabled,setEnabled]=useState(()=>{try{return sessionStorage.getItem('ptp-v2-family-sharing')==='yes';}catch{return false;}});
  const [groups,setGroups]=useState<FamilyGroup[]>([]);
  const [summary,setSummary]=useState<FamilySummary|null>(null);
  const [name,setName]=useState('');
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [familyName,setFamilyName]=useState('');
  const [invite,setInvite]=useState('');
  const [newInvite,setNewInvite]=useState('');
  const [error,setError]=useState('');
  const [status,setStatus]=useState('');
  const [busy,setBusy]=useState(false);

  useEffect(()=>{
    onConnection(enabled&&token&&group&&FAMILY_API?{token,groupId:group}:null);
  },[enabled,token,group,onConnection]);
  useEffect(()=>{
    if(!token||!FAMILY_API)return;
    let active=true;
    void familyRequest<{families:FamilyGroup[]}>('/api/v2/family/me','GET',undefined,token)
      .then(data=>{if(active)setGroups(data.families);})
      .catch(()=>{if(active){setError('Session expired — sign in again.');setEnabled(false);}});
    return ()=>{active=false;};
  },[token]);

  const refresh=async(t=token,g=group)=>{
    if(!t||!g)return;
    const data=await familyRequest<FamilySummary>('/api/v2/family/groups/'+g+'/summary','GET',undefined,t);
    setSummary(data);onSummary(data);
  };
  useEffect(()=>{
    if(!token||!group||!FAMILY_API)return;
    let active=true;
    void familyRequest<FamilySummary>('/api/v2/family/groups/'+group+'/summary','GET',undefined,token)
      .then(data=>{if(active)setSummary(data);onSummary(data);})
      .catch(()=>{if(active){setError('Unable to load this private family group.');setEnabled(false);}});
    return ()=>{active=false;};
  },[token,group]);

  const run=async(action:()=>Promise<void>)=>{
    setBusy(true);setError('');setStatus('');
    try{await action();}catch(e){setError(e instanceof Error?e.message:'Family request failed');}
    finally{setBusy(false);}
  };
  const saveSession=(value:string)=>{
    setToken(value);try{sessionStorage.setItem('ptp-v2-family-session',value);}catch{/* private browsing */}
  };
  const pickGroup=(id:number)=>{
    setGroup(id);setSummary(null);onSummary(null);setEnabled(false);
    try{sessionStorage.setItem('ptp-v2-family-group',String(id));sessionStorage.removeItem('ptp-v2-family-sharing');}catch{}
  };
  const toggle=(next:boolean)=>{
    setEnabled(next);try{sessionStorage.setItem('ptp-v2-family-sharing',next?'yes':'no');}catch{}
  };
  const login=async()=>{
    const data=await familyRequest<{token:string}>('/api/v2/family/login','POST',{email,password});
    saveSession(data.token);setPassword('');setStatus('Signed in. Choose or create a family.');
  };
  const signUp=async()=>{
    await familyRequest('/api/v2/family/signup','POST',{email,name,password});
    await login();
  };
  const logout=async()=>{
    try{await familyRequest('/api/v2/family/logout','POST',undefined,token);}finally{
      saveSession('');pickGroup(0);setGroups([]);setSummary(null);onSummary(null);toggle(false);setNewInvite('');
    }
  };
  const create=async()=>{
    const data=await familyRequest<FamilyGroup>('/api/v2/family/groups','POST',{name:familyName},token);
    setGroups(current=>[...current,data]);pickGroup(data.id);setFamilyName('');
    await refresh(token,data.id);
  };
  const redeem=async()=>{
    const data=await familyRequest<{group_id:number}>('/api/v2/family/invites/redeem','POST',{code:invite.trim()},token);
    const me=await familyRequest<{families:FamilyGroup[]}>('/api/v2/family/me','GET',undefined,token);
    setGroups(me.families);pickGroup(data.group_id);setInvite('');
    await refresh(token,data.group_id);
  };
  const inviteMember=async()=>{
    const data=await familyRequest<{code:string}>('/api/v2/family/groups/'+group+'/invite','POST',{},token);
    setNewInvite(data.code);
  };

  if(!FAMILY_API)return <section className="family-panel" aria-label="Family expedition">
    <span className="eyebrow">FAMILY EXPEDITION</span><h2>Grow your expedition together</h2>
    <p>The private family service is not configured yet. The map and XP work offline for one learner;
      shared progress, invitations and rankings will activate when a secured family service is deployed.</p>
    <p className="family-note">No pretend family accounts or rankings are shown.</p>
  </section>;
  return <section className="family-panel" aria-label="Family expedition">
    <div className="family-heading"><div><span className="eyebrow">PRIVATE FAMILY EXPEDITION</span><h2>Learn together</h2></div>
      {token&&<button type="button" onClick={()=>void run(logout)} disabled={busy}>Sign out</button>}</div>
    {!token ? <div className="family-auth">
      <p>Use your own private account to create or join your family's Poland expedition.</p>
      <label>Display name<input value={name} onChange={e=>setName(e.target.value)} autoComplete="nickname" maxLength={48}/></label>
      <label>Email<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></label>
      <label>Password<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)}/></label>
      <div className="family-actions"><button type="button" disabled={busy} onClick={()=>void run(login)}>Sign in</button>
        <button type="button" disabled={busy} onClick={()=>void run(signUp)}>Create account</button></div>
      <small>New passwords require at least 12 characters. Your account is private to this service.</small>
    </div> : <div className="family-connected">
      <div className="family-group-actions">
        <label>Your family group<select aria-label="Choose family group" value={group} onChange={e=>pickGroup(Number(e.target.value))}>
          <option value={0}>Choose a group</option>{groups.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}
        </select></label>
        <button type="button" disabled={!group||busy} onClick={()=>void run(()=>refresh())}>Refresh rankings</button>
      </div>
      <div className="family-setup">
        <div><label>New family group<input value={familyName} maxLength={50} onChange={e=>setFamilyName(e.target.value)}/></label>
          <button type="button" disabled={busy||familyName.trim().length<3} onClick={()=>void run(create)}>Create group</button></div>
        <div><label>Private invitation code<input value={invite} onChange={e=>setInvite(e.target.value)} autoComplete="off"/></label>
          <button type="button" disabled={busy||!invite.trim()} onClick={()=>void run(redeem)}>Join family</button></div>
      </div>
      {group>0&&<div className="family-contribute">
        <label><input type="checkbox" checked={enabled} onChange={e=>toggle(e.target.checked)}/>
          Contribute my <strong>future completed practice</strong> to this family</label>
        <p>Only activity IDs, mode and selected region are shared. No voice recordings or lesson text;
          previously earned local XP is not automatically uploaded.</p>
        {syncMessage&&<p role="status">{syncMessage}</p>}
      </div>}
      {summary&&<div className="family-scoreboard">
        <h3>{summary.group.name}</h3>
        <div className="family-totals"><span>{summary.totals.weekly_xp} weekly family XP</span>
          <span>{summary.totals.regions_unlocked}/16 regions opened</span></div>
        <h4>Friendly weekly effort board</h4>
        <ol>{summary.members.map(m=><li key={m.id}><strong>{m.name}</strong><span>{m.weekly_xp} XP</span>
          <small>{m.active_days} active days · highest tier {m.highest_tier || '—'}</small></li>)}</ol>
        <p className="family-note">Improvement recognition will appear only when verified learning evidence is available.
          Rankings reflect declared completed activities, not independently observed study sessions.</p>
        <h4>Regions funded together</h4>
        <div className="family-regions">{summary.regions.length?summary.regions.map(r=>
          <div key={r.region}><span>{r.region}</span><strong>{r.earned}/{r.target} XP {r.unlocked?'✓':''}</strong></div>
        ):<p>No team XP yet. Complete a lesson to start exploring.</p>}</div>
        <button type="button" disabled={busy} onClick={()=>void run(inviteMember)}>Create one-use family invite</button>
        {newInvite&&<p className="family-invite">Invitation expires in 48 hours, can be used only once, and should be shared privately.
          <code>{newInvite}</code></p>}
      </div>}
    </div>}
    {error&&<p role="alert" className="family-error">{error}</p>}
    {status&&<p role="status">{status}</p>}
  </section>;
}
