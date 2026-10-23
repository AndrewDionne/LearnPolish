import {useEffect,useRef,useState} from 'react';
import {FAMILY_API,FamilyRequestError,familyRequest} from './api';
import type {FamilyConnection,FamilyGroup,FamilySummary} from './api';
import {rankFamily,recognitionLabel,RECOGNITION_CATEGORIES} from './recognition';
import FamilyPrivacyControls from './FamilyPrivacyControls';
import type {RecognitionCategory} from './recognition';

type Props={onConnection:(connection:FamilyConnection|null)=>void;
            onSummary:(summary:FamilySummary|null)=>void;
            syncMessage:string; syncVersion:number};

export default function FamilyPanel({onConnection,onSummary,syncMessage,syncVersion}:Props){
  const [token,setToken]=useState(()=>{try{return sessionStorage.getItem('ptp-v2-family-session')||'';}catch{return '';}});
  const [group,setGroup]=useState(()=>{try{return Number(sessionStorage.getItem('ptp-v2-family-group'))||0;}catch{return 0;}});
  const [enabled,setEnabled]=useState(()=>{try{return sessionStorage.getItem('ptp-v2-family-sharing')==='yes';}catch{return false;}});
  const [groups,setGroups]=useState<FamilyGroup[]>([]);
  const [userId,setUserId]=useState(0);
  const [summary,setSummary]=useState<FamilySummary|null>(null);
  const [name,setName]=useState('');
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [recoveryAvailable,setRecoveryAvailable]=useState(false);
  const [verificationAvailable,setVerificationAvailable]=useState(false);
  const [pendingVerification,setPendingVerification]=useState(false);
  const [authMode,setAuthMode]=useState<'sign-in'|'create'>('create');
  const [verificationCode,setVerificationCode]=useState('');
  const [recoveryMode,setRecoveryMode]=useState(false);
  const [recoveryRequested,setRecoveryRequested]=useState(false);
  const [recoveryCode,setRecoveryCode]=useState('');
  const [recoveryPassword,setRecoveryPassword]=useState('');
  const [familyName,setFamilyName]=useState('');
  const [invite,setInvite]=useState('');
  const [newInvite,setNewInvite]=useState('');
  const [inviteCopied,setInviteCopied]=useState(false);
  const [error,setError]=useState('');
  const [status,setStatus]=useState('');
  const [busy,setBusy]=useState(false);
  const [recognitionCategory,setRecognitionCategory]=useState<RecognitionCategory>('effort');
  // Ignore earlier summary fetches that finish after a refresh or group change.
  const summaryRequestId=useRef(0);
  // Prevent a late invite response from appearing under a different family group.
  const inviteRequestId=useRef(0);
  const initialSync=useRef(syncVersion);
  // Mutable identity/scope invalidates network replies synchronously, before React
  // renders the new group. A request ID alone cannot distinguish account changes.
  const scope=useRef({token,group});
  const operationId=useRef(0);
  const isCurrent=(t:string,g:number)=>scope.current.token===t&&scope.current.group===g;
  useEffect(()=>()=>{summaryRequestId.current++;inviteRequestId.current++;operationId.current++;},[]);

  useEffect(()=>{
    onConnection(enabled&&token&&group&&FAMILY_API?{token,groupId:group}:null);
  },[enabled,token,group,onConnection]);
  useEffect(()=>{
    if(!FAMILY_API||token)return;
    let active=true;
    void familyRequest<{password_recovery_available:boolean;email_verification_available:boolean}>('/api/v2/family/health')
      .then(data=>{if(active){setRecoveryAvailable(data.password_recovery_available===true);
        setVerificationAvailable(data.email_verification_available===true);}})
      .catch(()=>{if(active){setRecoveryAvailable(false);setVerificationAvailable(false);}});
    return ()=>{active=false;};
  },[token]);
  useEffect(()=>{
    if(!token||!FAMILY_API)return;
    let active=true;
    void familyRequest<{families:FamilyGroup[];user:{id:number}}>('/api/v2/family/me','GET',undefined,token)
      .then(data=>{if(active){setGroups(data.families);setUserId(data.user.id);}})
      .catch(e=>{if(!active)return;
        if(e instanceof FamilyRequestError&&e.status===401){
          clearAccountSession();setError('Session expired — sign in again.');
        }else{
          // Service failure must not leave an old membership/opt-in visible.
          pickGroup(0);setGroups([]);setUserId(0);
          setError('Unable to verify your account. Refresh the page or sign in again.');
        }
      });
    return ()=>{active=false;};
  },[token]);

  const dropInaccessibleGroup=(inaccessibleId:number)=>{
    setGroups(current=>current.filter(item=>item.id!==inaccessibleId));
    // Clear the live request scope together with the visible selection. Otherwise
    // an older API response can resurrect a revoked group's data.
    pickGroup(0);
  };
  const refresh=async(t=token,g=group)=>{
    if(!t||!g)return;
    const id=++summaryRequestId.current;
    try{
      const data=await familyRequest<FamilySummary>('/api/v2/family/groups/'+g+'/summary','GET',undefined,t);
      if(id===summaryRequestId.current&&isCurrent(t,g)){
        setSummary(data);onSummary(data);
      }
    }catch(e){
      if(id!==summaryRequestId.current||!isCurrent(t,g))return;
      if(e instanceof FamilyRequestError&&e.status===401){
        clearAccountSession();setError('Session expired — sign in again.');
        return;
      }
      if(e instanceof FamilyRequestError&&e.status===404){
        dropInaccessibleGroup(g);setError('Family access has ended. Choose another group.');
        return;
      }
      setSummary(null);onSummary(null);setEnabled(false);
      setNewInvite('');inviteRequestId.current++;
      throw e;
    }
  };
  useEffect(()=>{
    if(!token||!group||!FAMILY_API)return;
    let active=true;
    const id=++summaryRequestId.current;
    void familyRequest<FamilySummary>('/api/v2/family/groups/'+group+'/summary','GET',undefined,token)
      .then(data=>{if(active&&id===summaryRequestId.current&&isCurrent(token,group)){
        setSummary(data);onSummary(data);
      }})
      .catch(error=>{if(active&&id===summaryRequestId.current&&isCurrent(token,group)){
        if(error instanceof FamilyRequestError&&error.status===401){
          clearAccountSession();setError('Session expired — sign in again.');
        }else if(error instanceof FamilyRequestError&&error.status===404){
          dropInaccessibleGroup(group);setError('Family access has ended. Choose another group.');
        }else{
          setSummary(null);onSummary(null);setError('Unable to load this private family group.');
          setNewInvite('');inviteRequestId.current++;setEnabled(false);
        }
      }});
    return ()=>{active=false;summaryRequestId.current++;};
  },[token,group]);
  useEffect(()=>{
    // The parent increments only AFTER the server acknowledges a contributed activity.
    if(syncVersion>initialSync.current&&token&&group&&FAMILY_API){
      initialSync.current=syncVersion;
      const expectedToken=token,expectedGroup=group;
      void refresh().catch(()=>{
        if(isCurrent(expectedToken,expectedGroup))
          setError('Unable to refresh family results; try Refresh rankings.');
      });
    }
  },[syncVersion,token,group]);

  const run=async(action:()=>Promise<void>)=>{
    const id=++operationId.current;
    setBusy(true);setError('');setStatus('');
    try{await action();}catch(e){
      if(id===operationId.current)setError(e instanceof Error?e.message:'Family request failed');
    }finally{if(id===operationId.current)setBusy(false);}
  };
  const saveSession=(value:string)=>{
    if(scope.current.token!==value){
      operationId.current++;summaryRequestId.current++;inviteRequestId.current++;
      scope.current.token=value;
      setSummary(null);onSummary(null);
    }
    setToken(value);try{
      if(value)sessionStorage.setItem('ptp-v2-family-session',value);
      else sessionStorage.removeItem('ptp-v2-family-session');
    }catch{/* private browsing */}
  };
  const pickGroup=(id:number)=>{
    operationId.current++;
    summaryRequestId.current++;
    inviteRequestId.current++;
    scope.current.group=id;
    setBusy(false);
    setNewInvite('');setInviteCopied(false);
    setGroup(id);setSummary(null);onSummary(null);setEnabled(false);
    try{
      if(id)sessionStorage.setItem('ptp-v2-family-group',String(id));
      else sessionStorage.removeItem('ptp-v2-family-group');
      sessionStorage.removeItem('ptp-v2-family-sharing');
    }catch{}
  };
  const toggle=(next:boolean)=>{
    setEnabled(next);try{sessionStorage.setItem('ptp-v2-family-sharing',next?'yes':'no');}catch{}
  };
  const login=async()=>{
    let data:{token:string};
    try{
      data=await familyRequest<{token:string}>('/api/v2/family/login','POST',{email,password});
    }catch(e){
      if(e instanceof Error&&e.message==='email verification required'){
        setPendingVerification(true);
        setStatus('Confirm your email address to activate this family account.');
        return;
      }
      throw e;
    }
    saveSession(data.token);pickGroup(0);setPassword('');setPendingVerification(false);setAuthMode('sign-in');
    setStatus('Signed in. Choose or create a family.');
  };
  const signUp=async()=>{
    await familyRequest('/api/v2/family/signup','POST',{email,name,password});
    setPendingVerification(true);
    setVerificationCode('');
    setStatus('Check your email for a one-time verification code.');
  };
  const verifyEmail=async()=>{
    await familyRequest('/api/v2/family/verification/confirm','POST',
      {email,code:verificationCode.trim()});
    setVerificationCode('');setPendingVerification(false);
    await login();
  };
  const resendVerification=async()=>{
    await familyRequest('/api/v2/family/verification/resend','POST',{email,password});
    setStatus('If these are the pending account credentials, a new code has been emailed.');
  };
  const requestRecovery=async()=>{
    await familyRequest('/api/v2/family/recovery/request','POST',{email});
    setRecoveryRequested(true);
    setStatus('If an account exists for this email, a one-use recovery code has been sent.');
  };
  const completeRecovery=async()=>{
    await familyRequest('/api/v2/family/recovery/complete','POST',
      {code:recoveryCode.trim(),new_password:recoveryPassword});
    setRecoveryCode('');setRecoveryPassword('');setRecoveryMode(false);setRecoveryRequested(false);
    setPassword('');setStatus('Password reset. Sign in with your new password.');
  };
  const clearAccountSession=()=>{
    saveSession('');pickGroup(0);setGroups([]);setSummary(null);onSummary(null);toggle(false);
    setNewInvite('');setUserId(0);setStatus('Signed out of the private family service.');
  };
  const logout=async()=>{
    try{await familyRequest('/api/v2/family/logout','POST',undefined,token);}
    finally{clearAccountSession();}
  };
  const leaveFamily=()=>{
    setGroups(previous=>previous.filter(value=>value.id!==group));
    pickGroup(0);setNewInvite('');
    setStatus('Left family. Previously contributed shared activity was erased.');
  };
  const revoked=()=>{setNewInvite('');};

  const create=async()=>{
    const t=token,g=group,id=operationId.current;
    const data=await familyRequest<FamilyGroup>('/api/v2/family/groups','POST',{name:familyName},t);
    if(id!==operationId.current||!isCurrent(t,g))return;
    setGroups(current=>[...current,data]);pickGroup(data.id);setFamilyName('');
    await refresh(t,data.id);
  };
  const redeem=async()=>{
    const t=token,g=group,id=operationId.current;
    const data=await familyRequest<{group_id:number}>('/api/v2/family/invites/redeem','POST',{code:invite.trim()},t);
    if(id!==operationId.current||!isCurrent(t,g))return;
    const me=await familyRequest<{families:FamilyGroup[]}>('/api/v2/family/me','GET',undefined,t);
    if(id!==operationId.current||!isCurrent(t,g))return;
    setGroups(me.families);pickGroup(data.group_id);setInvite('');
    await refresh(t,data.group_id);
  };
  const inviteMember=async()=>{
    const id=++inviteRequestId.current;
    const chosenGroup=group,chosenToken=token;
    const data=await familyRequest<{code:string}>('/api/v2/family/groups/'+chosenGroup+'/invite','POST',{},chosenToken);
    if(id===inviteRequestId.current&&isCurrent(chosenToken,chosenGroup)){
      setNewInvite(data.code);setInviteCopied(false);
    }
  };

  const copyInvite=async()=>{
    if(!newInvite)return;
    const chosenToken=token,chosenGroup=group;
    try{
      if(!navigator.clipboard?.writeText)throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(newInvite);
      if(isCurrent(chosenToken,chosenGroup))setInviteCopied(true);
    }catch{
      if(!isCurrent(chosenToken,chosenGroup))return;
      setInviteCopied(false);
      setStatus('Select the invitation code below and copy it manually.');
    }
  };

  if(!FAMILY_API)return <section className="family-panel" aria-label="Family expedition">
    <span className="eyebrow">FAMILY EXPEDITION</span><h2>Grow your expedition together</h2>
    <p>The private family service is not configured yet. The map and XP work offline for one learner;
      shared progress, invitations and rankings will activate when a secured family service is deployed.</p>
    <p className="family-note">No pretend family accounts or rankings are shown.</p>
  </section>;
  return <section className="family-panel" aria-label="Family expedition">
    <div className="family-heading"><div><h2>Family account</h2></div>
      {token&&<button type="button" onClick={()=>void run(logout)} disabled={busy}>Sign out</button>}</div>
    {!token ? <div className="family-auth">
      {pendingVerification?<div className="family-verification">
        <h3>Verify your email</h3>
        <p>Enter the code sent to your mailbox within 30 minutes. Family invitations,
          shared XP and account access require verified email.</p>
        <label>Email<input type="email" value={email} autoComplete="email"
          onChange={e=>setEmail(e.target.value)}/></label>
        <label>Verification code<input value={verificationCode} autoComplete="off"
          onChange={e=>setVerificationCode(e.target.value.trim())}/></label>
        <div className="family-actions">
          <button type="button" disabled={busy||!verificationCode.trim()}
            onClick={()=>void run(verifyEmail)}>Verify email</button>
          <button type="button" disabled={busy||!email.trim()||!password}
            onClick={()=>void run(resendVerification)}>Resend code</button>
        </div>
        <button type="button" disabled={busy} onClick={()=>{
          setPendingVerification(false);setAuthMode('sign-in');setVerificationCode('');setError('');setStatus('');
        }}>Back to sign in</button>
      </div>:recoveryMode?<div className="family-recovery">
        <h3>Recover family account</h3>
        <p>Request a private email code. Codes expire in 15 minutes and can be used only once.</p>
        <label>Email<input type="email" autoComplete="email" value={email}
          onChange={e=>setEmail(e.target.value)}/></label>
        <button type="button" disabled={busy||!email.trim()}
          onClick={()=>void run(requestRecovery)}>Email recovery code</button>
        {recoveryRequested&&<>
          <label>Recovery code<input value={recoveryCode} autoComplete="off"
            onChange={e=>setRecoveryCode(e.target.value.trim())}/></label>
          <label>New password<input type="password" autoComplete="new-password"
            value={recoveryPassword} onChange={e=>setRecoveryPassword(e.target.value)}/></label>
          <button type="button" disabled={busy||!recoveryCode||recoveryPassword.length<12}
            onClick={()=>void run(completeRecovery)}>Set new password</button>
        </>}
        <button type="button" disabled={busy} onClick={()=>{setRecoveryMode(false);setRecoveryCode('');
          setRecoveryPassword('');setRecoveryRequested(false);setError('');setStatus('');}}>Back to sign in</button>
      </div>:<>
        <div className="family-auth-heading">
          <p>{authMode==='create'?'A private learner account lets you join or create a family expedition.':'Sign in to continue your family expedition.'}</p>
          <div className="family-auth-switch" role="group" aria-label="Family account access">
            <button type="button" aria-pressed={authMode==='sign-in'} disabled={busy}
              onClick={()=>{setAuthMode('sign-in');setError('');setStatus('');}}>Sign in</button>
            {authMode==='create'
              ? <span className="family-auth-current" aria-current="step">Create account</span>
              : <button type="button" aria-pressed={false} disabled={busy||!verificationAvailable}
                  onClick={()=>{setAuthMode('create');setError('');setStatus('');}}>Create account</button>}
          </div>
        </div>
        {authMode==='create'&&<label>Display name<input value={name} onChange={e=>setName(e.target.value)}
          autoComplete="nickname" maxLength={48}/></label>}
        <label>Email<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)}/></label>
        <label>Password<input type="password" autoComplete={authMode==='create'?'new-password':'current-password'}
          value={password} onChange={e=>setPassword(e.target.value)}/></label>
        <div className="family-actions">
          {authMode==='create'
            ? <button type="button" disabled={busy||!verificationAvailable||name.trim().length<2||!email.trim()||password.length<12}
                onClick={()=>void run(signUp)}>Create account</button>
            : <button type="button" disabled={busy||!email.trim()||!password}
                onClick={()=>void run(login)}>Sign in to family</button>}
        </div>
        {authMode==='create'&&<small>Use a password of at least 12 characters. Verify the code in your email before joining a family.</small>}
        {!verificationAvailable&&<p className="family-note">New family accounts are unavailable until secure verification email delivery is configured.</p>}
        {recoveryAvailable&&<button type="button" className="family-recovery-link" disabled={busy} onClick={()=>{
          setRecoveryMode(true);setError('');setStatus('');}}>Forgot password?</button>}
      </>}
    </div> : <div className="family-connected">
      <div className="family-group-actions">
        <label>Active learning group<select aria-label="Choose family group" value={group} onChange={e=>pickGroup(Number(e.target.value))}>
          <option value={0}>Choose a group</option>{groups.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}
        </select></label>
        <button type="button" disabled={!group||busy} onClick={()=>void run(()=>refresh())}>Refresh rankings</button>
      </div>
      <details className="family-management" open={!group}>
        <summary>{group?'Manage learning groups and invitations':'Create or join a learning group'}</summary>
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
        <p className="family-group-context">Group scoreboards · {summary.members.length} {summary.members.length===1?'learner':'learners'} · current group only</p>
        <div className="family-totals"><span>{summary.totals.weekly_xp} weekly family XP</span>
          <span>{summary.totals.regions_unlocked}/16 regions opened</span></div>
        <div className="family-recognition" aria-label="Family weekly recognition">
          <h4>Weekly leaderboard</h4>
          <div className="family-board-filters" role="group" aria-label="Weekly recognition category">
            {RECOGNITION_CATEGORIES.map(category=><button key={category.id} type="button"
              aria-pressed={recognitionCategory===category.id}
              onClick={()=>setRecognitionCategory(category.id)}>{category.label}</button>)}
          </div>
          {recognitionCategory==='improvement'
            ? <p role="status" className="family-recognition-pending">Most-improved recognition will use verified change from each learner's previous comparable performance. This family has no validated improvement measurements yet; no ranking is assigned.</p>
            : <ol aria-label={RECOGNITION_CATEGORIES.find(x=>x.id===recognitionCategory)?.label+' leaderboard'}>
                {rankFamily(summary.members,recognitionCategory).map(({member,score,rank})=>
                  <li key={member.id} className={member.id===userId?'family-current-learner':''}>
                    <strong>{rank===null?'—':rank+'.'} {member.name}{member.id===userId?' (you)':''}</strong>
                    <span>{recognitionLabel(recognitionCategory,score)}</span>
                  </li>)}
              </ol>}
          <p className="family-note">Friendly comparisons, based on member-declared completed practice validated against the built-in catalog. Difficulty indicates material attempted, not demonstrated mastery.</p>
        </div>
        <h4>Regions funded together</h4>
        <div className="family-regions">{summary.regions.length?summary.regions.map(r=>
          <div key={r.region}><span>{r.region}</span><strong>{r.earned}/{r.target} XP {r.unlocked?'✓':''}</strong></div>
        ):<p>No team XP yet. Complete a lesson to start exploring.</p>}</div>
        {summary.group.can_invite&&<button type="button" disabled={busy} onClick={()=>void run(inviteMember)}>Create one-use family invite</button>}
        {newInvite&&<div className="family-invite" aria-label="New private family invitation">
          <p>Invitation expires in 48 hours, can be used only once, and should be shared privately.</p>
          <code>{newInvite}</code>
          <button type="button" disabled={busy} onClick={()=>void copyInvite()}>
            {inviteCopied?'Copied invitation code':'Copy invitation code'}
          </button>
        </div>}
      </div>}
      <FamilyPrivacyControls token={token} groupId={group} canInvite={!!summary?.group.can_invite}
        userId={userId} members={summary?.members??[]}
        onLeave={leaveFamily}
        onTransfer={()=>{void refresh().catch(()=>setError('Unable to refresh ownership status.'));}}
        onRemoved={()=>{setNewInvite('');setInviteCopied(false);
          void refresh().catch(()=>setError('Unable to refresh member list.'));}}
        onRevoke={revoked} onSignedOut={clearAccountSession}/>
    </div>}
    {error&&<p role="alert" className="family-error">{error}</p>}
    {status&&<p role="status">{status}</p>}
  </section>;
}
