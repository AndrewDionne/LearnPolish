import {useEffect,useRef,useState} from 'react';
import {FAMILY_API,familyRequest} from './api';
import type {FamilyConnection,FamilyGroup,FamilySummary} from './api';
import {rankFamily,recognitionLabel,RECOGNITION_CATEGORIES} from './recognition';
import type {RecognitionCategory} from './recognition';

type Props={onConnection:(connection:FamilyConnection|null)=>void;
            onSummary:(summary:FamilySummary|null)=>void;
            syncMessage:string; syncVersion:number};

export default function FamilyPanel({onConnection,onSummary,syncMessage,syncVersion}:Props){
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
  const [recognitionCategory,setRecognitionCategory]=useState<RecognitionCategory>('effort');
  // Ignore earlier summary fetches that finish after a refresh or group change.
  const summaryRequestId=useRef(0);
  const initialSync=useRef(syncVersion);

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
    const id=++summaryRequestId.current;
    const data=await familyRequest<FamilySummary>('/api/v2/family/groups/'+g+'/summary','GET',undefined,t);
    if(id===summaryRequestId.current){
      setSummary(data);onSummary(data);
    }
  };
  useEffect(()=>{
    if(!token||!group||!FAMILY_API)return;
    let active=true;
    const id=++summaryRequestId.current;
    void familyRequest<FamilySummary>('/api/v2/family/groups/'+group+'/summary','GET',undefined,token)
      .then(data=>{if(active&&id===summaryRequestId.current){setSummary(data);onSummary(data);}})
      .catch(()=>{if(active&&id===summaryRequestId.current){setError('Unable to load this private family group.');setEnabled(false);}});
    return ()=>{active=false;summaryRequestId.current++;};
  },[token,group]);
  useEffect(()=>{
    // The parent increments only AFTER the server acknowledges a contributed activity.
    if(syncVersion>initialSync.current&&token&&group&&FAMILY_API){
      initialSync.current=syncVersion;
      void refresh().catch(()=>setError('Unable to refresh family results; try Refresh rankings.'));
    }
  },[syncVersion,token,group]);

  const run=async(action:()=>Promise<void>)=>{
    setBusy(true);setError('');setStatus('');
    try{await action();}catch(e){setError(e instanceof Error?e.message:'Family request failed');}
    finally{setBusy(false);}
  };
  const saveSession=(value:string)=>{
    setToken(value);try{sessionStorage.setItem('ptp-v2-family-session',value);}catch{/* private browsing */}
  };
  const pickGroup=(id:number)=>{
    summaryRequestId.current++;
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
      <details className="family-management" open={!group}>
        <summary>{group?'Manage groups and invitations':'Create or join your family'}</summary>
        <div className="family-setup">
          <div><label>New family group<input value={familyName} maxLength={50} onChange={e=>setFamilyName(e.target.value)}/></label>
            <button type="button" disabled={busy||familyName.trim().length<3} onClick={()=>void run(create)}>Create group</button></div>
          <div><label>Private invitation code<input value={invite} onChange={e=>setInvite(e.target.value)} autoComplete="off"/></label>
            <button type="button" disabled={busy||!invite.trim()} onClick={()=>void run(redeem)}>Join family</button></div>
        </div>
      </details>
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
        <div className="family-recognition" aria-label="Family weekly recognition">
          <h4>Our family's weekly highlights</h4>
          <div className="family-board-filters" role="group" aria-label="Weekly recognition category">
            {RECOGNITION_CATEGORIES.map(category=><button key={category.id} type="button"
              aria-pressed={recognitionCategory===category.id}
              onClick={()=>setRecognitionCategory(category.id)}>{category.label}</button>)}
          </div>
          <p className="family-note">{RECOGNITION_CATEGORIES.find(x=>x.id===recognitionCategory)?.description}</p>
          {recognitionCategory==='improvement'
            ? <p role="status" className="family-recognition-pending">Most-improved recognition will use verified change from each learner's previous comparable performance. This family has no validated improvement measurements yet; no ranking is assigned.</p>
            : <ol aria-label={RECOGNITION_CATEGORIES.find(x=>x.id===recognitionCategory)?.label+' leaderboard'}>
                {rankFamily(summary.members,recognitionCategory).map(({member,score,rank})=>
                  <li key={member.id}>
                    <strong>{rank===null?'—':rank+'.'} {member.name}</strong>
                    <span>{recognitionLabel(recognitionCategory,score)}</span>
                    <small>{member.active_days} practice days · tier {member.highest_tier||'—'} attempted · {member.team_xp} map XP</small>
                  </li>)}
              </ol>}
          <p className="family-note">Friendly comparisons, based on member-declared completed practice validated against the built-in catalog. Difficulty indicates material attempted, not demonstrated mastery.</p>
        </div>
        <h4>Regions funded together</h4>
        <div className="family-regions">{summary.regions.length?summary.regions.map(r=>
          <div key={r.region}><span>{r.region}</span><strong>{r.earned}/{r.target} XP {r.unlocked?'✓':''}</strong></div>
        ):<p>No team XP yet. Complete a lesson to start exploring.</p>}</div>
        {summary.group.can_invite&&<button type="button" disabled={busy} onClick={()=>void run(inviteMember)}>Create one-use family invite</button>}
        {newInvite&&<p className="family-invite">Invitation expires in 48 hours, can be used only once, and should be shared privately.
          <code>{newInvite}</code></p>}
      </div>}
    </div>}
    {error&&<p role="alert" className="family-error">{error}</p>}
    {status&&<p role="status">{status}</p>}
  </section>;
}
