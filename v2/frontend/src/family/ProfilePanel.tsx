import {useEffect,useState} from 'react';
import {FAMILY_API,familyRequest} from './api';
import type {FamilyGroup} from './api';

type Identity={id:number;name:string;email:string};
type PrivateProfile={user:Identity;families:FamilyGroup[]};

/** Account information is private service data; browser XP stays on this device. */
export default function ProfilePanel({onOpenGroups}:{onOpenGroups:()=>void}){
  const [token]=useState(()=>{
    try{return sessionStorage.getItem('ptp-v2-family-session')||'';}catch{return '';}
  });
  const [data,setData]=useState<PrivateProfile|null>(null);
  const [displayName,setDisplayName]=useState('');
  const [loading,setLoading]=useState(!!(FAMILY_API&&token));
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [message,setMessage]=useState('');

  useEffect(()=>{
    if(!FAMILY_API||!token)return;
    let active=true;
    void familyRequest<PrivateProfile>('/api/v2/family/me','GET',undefined,token)
      .then(result=>{
        if(!active)return;
        setData(result);setDisplayName(result.user.name);setLoading(false);
      })
      .catch(()=>{
        if(!active)return;
        setLoading(false);setError('Your private account session expired. Sign in from Learning groups.');
      });
    return ()=>{active=false;};
  },[token]);

  const saveName=async()=>{
    const name=displayName.trim();
    if(!data||!name||name.length>48||name===data.user.name||busy)return;
    setBusy(true);setError('');setMessage('');
    try{
      const result=await familyRequest<{user:Identity}>(
        '/api/v2/family/account/profile','POST',{name},token);
      setData(current=>current?{...current,user:result.user}:current);
      setDisplayName(result.user.name);
      setMessage('Display name updated for your learning groups.');
    }catch(e){setError(e instanceof Error?e.message:'Profile could not be saved.');}
    finally{setBusy(false);}
  };

  return <section className="learner-profile" aria-label="Learner account">
    <div className="learner-profile-heading"><div>
      <h2>Account</h2>
    </div><button type="button" className="secondary-action" onClick={onOpenGroups}>Learning groups & scoreboards →</button></div>
    {!FAMILY_API?<p>Private groups are unavailable. Your local learning remains available.</p>
      : !token?<p>Not signed in. Open Learning groups to join or create a group.</p>
      : loading?<p role="status">Loading private account…</p>
      : data?<div className="learner-account-details">
        <div className="learner-account-mark" aria-hidden="true">{data.user.name.slice(0,1).toLocaleUpperCase()}</div>
        <div className="learner-account-fields">
          <label>Display name<input value={displayName} maxLength={48}
            autoComplete="nickname" onChange={e=>setDisplayName(e.target.value)}/></label>
          <label>Account email<input readOnly value={data.user.email}/></label>
          <div className="learner-account-actions">
            <button type="button" disabled={busy||!displayName.trim()||displayName.trim()===data.user.name}
              onClick={()=>void saveName()}>Save display name</button>
            <span>{data.families.length} {data.families.length===1?'learning group':'learning groups'}</span>
          </div>
          {data.families.length>0&&<div className="learner-joined-groups">
            <h3>Your learning groups</h3>
            <ul aria-label="Joined learning groups">{data.families.map(group=>
              <li key={group.id}>{group.name}</li>)}</ul>
          </div>}
        </div>
      </div>
      :<p>No verified private account is available in this session.</p>}
    {error&&<p role="alert" className="family-error">{error}</p>}
    {message&&<p role="status">{message}</p>}
    <p className="learner-profile-footnote">Learning progress on this page stays in this browser. Shared family XP is separate.</p>
  </section>;
}
