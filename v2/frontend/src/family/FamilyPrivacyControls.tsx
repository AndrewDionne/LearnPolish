import {useEffect,useState} from 'react';
import {familyRequest} from './api';
import type {FamilyMember} from './api';

type Props = {
 token:string; groupId:number; canInvite:boolean; userId:number;
 members:FamilyMember[];
 onLeave:()=>void; onTransfer:()=>void; onRemoved:()=>void; onRevoke:()=>void; onSignedOut:()=>void;
};

/** Explicit, authenticated, private-data operations. Never affects local/offline lessons. */
export default function FamilyPrivacyControls({token,groupId,canInvite,userId,members,
 onLeave,onTransfer,onRemoved,onRevoke,onSignedOut}:Props){
 const [target,setTarget]=useState('');
 const [removeTarget,setRemoveTarget]=useState('');
 useEffect(()=>{setTarget('');setRemoveTarget('');},[groupId]);
 const [currentPassword,setCurrentPassword]=useState('');
 const [newPassword,setNewPassword]=useState('');
 const [deletePassword,setDeletePassword]=useState('');
 const [deletePhrase,setDeletePhrase]=useState('');
 const [busy,setBusy]=useState(false);
 const [feedback,setFeedback]=useState('');
 const [error,setError]=useState('');
 const run=async(action:()=>Promise<void>)=>{
   setBusy(true);setError('');setFeedback('');
   try{await action();}catch(e){setError(e instanceof Error?e.message:'Request failed');}
   finally{setBusy(false);}
 };
 const leave=async()=>{
   if(!window.confirm('Leave this family? Your family-shared XP and practice records will be deleted. This may reduce shared map progress. Personal offline XP is unaffected.'))return;
   await familyRequest('/api/v2/family/groups/'+groupId+'/leave','POST',{},token);
   onLeave();
 };
 const revoke=async()=>{
   if(!window.confirm('Revoke every unused family invitation code? Already-used invitations remain spent.'))return;
   const result=await familyRequest<{revoked:number}>(
      '/api/v2/family/groups/'+groupId+'/invites/revoke','POST',{},token);
   onRevoke();
   setFeedback(result.revoked+' unused invitations revoked.');
 };
 const transfer=async()=>{
   const id=Number(target);
   if(!Number.isSafeInteger(id)||id===userId||!members.some(member=>member.id===id))return;
   if(!window.confirm('Make the selected member the new family owner? You will lose ownership controls.'))return;
   await familyRequest('/api/v2/family/groups/'+groupId+'/transfer','POST',
      {new_owner_id:id},token);
   setFeedback('Ownership transferred.');
   setTarget('');
   onTransfer();
 };
 const removeMember=async()=>{
   const id=Number(removeTarget);
   const member=members.find(person=>person.id===id&&person.id!==userId);
   if(!member||!Number.isSafeInteger(id))return;
   if(!window.confirm('Remove '+member.name+' from this family? Their family-shared XP and practice records will be erased, and this may reduce map progress. Their account and personal/offline lessons are unaffected.'))return;
   const response=await familyRequest<{removed:boolean;removed_activities:number}>(
     '/api/v2/family/groups/'+groupId+'/members/remove','POST',{member_id:id},token);
   setRemoveTarget('');
   onRemoved();
   setFeedback(member.name+' removed from this family. '+response.removed_activities+' shared activities erased.');
 };
 const exportData=async()=>{
   const data=await familyRequest<Record<string,unknown>>('/api/v2/family/account/export',
     'GET',undefined,token);
   const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'}));
   try{
     const a=document.createElement('a');
     a.href=url;a.download='path-to-polish-family-account.json';
     document.body.appendChild(a);a.click();a.remove();
   }finally{window.setTimeout(()=>URL.revokeObjectURL(url),0);}
   setFeedback('Private account export prepared. Keep the downloaded file secure.');
 };
 const changePassword=async()=>{
   await familyRequest('/api/v2/family/account/password','POST',
     {current_password:currentPassword,new_password:newPassword},token);
   setCurrentPassword('');setNewPassword('');
   onSignedOut();
 };
 const deleteAccount=async()=>{
   if(deletePhrase!=='DELETE MY ACCOUNT')return;
   if(!window.confirm('Permanently delete your family service account and its shared practice? This cannot be undone. Groups you own must first be transferred to another member or emptied. Your local/offline lessons and XP will remain on this device.'))return;
   await familyRequest('/api/v2/family/account/delete','POST',
     {password:deletePassword,confirmation:deletePhrase},token);
   setDeletePassword('');setDeletePhrase('');
   onSignedOut();
 };
 return <details className="family-privacy" data-testid="family-privacy">
   <summary>Family privacy and account controls</summary>
   <p>This private family service stores your display name, email, group membership and
     eligible practice activity. It does not store recordings. Your local practice data is separate.</p>
   <div className="family-privacy-actions">
     <button type="button" disabled={busy} onClick={()=>void run(exportData)}>Download my family account data</button>
     {groupId>0&&<button type="button" disabled={busy} onClick={()=>void run(leave)}>
       {canInvite?'Close or leave this family':'Leave this family'}</button>}
     {groupId>0&&canInvite&&<>
       <button type="button" disabled={busy} onClick={()=>void run(revoke)}>
         Revoke unused invitations</button>
       <label>Transfer ownership
         <select aria-label="New family owner" value={target} onChange={e=>setTarget(e.target.value)}>
           <option value="">Choose a family member</option>
           {members.filter(m=>m.id!==userId).map(m=>
             <option key={m.id} value={m.id}>{m.name}</option>)}
         </select>
       </label>
       <button type="button" disabled={busy||!target} onClick={()=>void run(transfer)}>
         Transfer ownership</button>
       <label>Remove a family member
         <select aria-label="Member to remove" value={removeTarget} onChange={e=>setRemoveTarget(e.target.value)}>
           <option value="">Choose a family member</option>
           {members.filter(m=>m.id!==userId).map(m=>
             <option key={m.id} value={m.id}>{m.name}</option>)}
         </select>
       </label>
       <button type="button" className="family-danger" disabled={busy||!removeTarget}
         onClick={()=>void run(removeMember)}>Remove member and erase shared XP</button>
     </>}
   </div>
   <fieldset className="family-private-fieldset">
     <legend>Change password</legend>
     <label>Current password
       <input type="password" autoComplete="current-password" value={currentPassword}
         onChange={e=>setCurrentPassword(e.target.value)}/></label>
     <label>New password (12+ characters)
       <input type="password" autoComplete="new-password" value={newPassword}
         onChange={e=>setNewPassword(e.target.value)}/></label>
     <button type="button" disabled={busy||!currentPassword||newPassword.length<12}
       onClick={()=>void run(changePassword)}>Update password and sign out everywhere</button>
   </fieldset>
   <fieldset className="family-private-fieldset">
     <legend>Delete family service account</legend>
     <p>Deletes family-service membership and contributed activity. If you own a group with other
       members, transfer ownership first. Removing activity can reduce team unlock totals.
       This never deletes your separately stored personal/offline lessons or XP.</p>
     <label>Account password
       <input type="password" autoComplete="off" value={deletePassword}
         onChange={e=>setDeletePassword(e.target.value)}/></label>
     <label>Type DELETE MY ACCOUNT
       <input autoComplete="off" spellCheck={false} value={deletePhrase}
         onChange={e=>setDeletePhrase(e.target.value)}/></label>
     <button className="family-danger" type="button" disabled={busy||!deletePassword||deletePhrase!=='DELETE MY ACCOUNT'}
       onClick={()=>void run(deleteAccount)}>Permanently delete family account</button>
   </fieldset>
   {error&&<p role="alert" className="family-error">{error}</p>}
   {feedback&&<p role="status">{feedback}</p>}
 </details>;
}
