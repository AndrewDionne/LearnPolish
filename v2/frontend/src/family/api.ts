/** V2 family service: deliberately disabled until explicitly configured and deployed. */
export type FamilyConnection={token:string;groupId:number};
export type FamilyGroup={id:number;name:string;can_invite?:boolean};
export type FamilyMember={id:number;name:string;weekly_xp:number;active_days:number;highest_tier:number;team_xp:number};
export type FamilySummary={
  group:FamilyGroup; members:FamilyMember[];
  regions:{region:string;earned:number;target:number;unlocked:boolean}[];
  totals:{weekly_xp:number;regions_unlocked:number};
  recognition:{improvement:string};
};

export function familyServiceUrl(value:string|undefined):string|null{
  if(!value)return null;
  try{
    const uri=new URL(value);
    const local=uri.hostname==='localhost'||uri.hostname==='127.0.0.1';
    if(!uri.hostname.includes('*') && (uri.protocol==='https:'||(local&&uri.protocol==='http:')) &&
        !uri.username&&!uri.password&&!uri.search&&!uri.hash&&uri.pathname==='/'){
      return uri.origin;
    }
  }catch{/* unavailable or invalid */}
  return null;
}
export const FAMILY_API=familyServiceUrl(import.meta.env.VITE_FAMILY_API_URL);

export async function familyRequest<T>(path:string,method:'GET'|'POST'='GET',
                                     body?:Record<string,unknown>,token?:string):Promise<T>{
  if(!FAMILY_API)throw new Error('Family service has not been connected.');
  if(!/^\/api\/v2\/family\/[a-zA-Z0-9/_-]+$/.test(path))throw new Error('Invalid family API path');
  const response=await fetch(FAMILY_API+path,{
    method,headers:{...(body?{'Content-Type':'application/json'}:{}),
      ...(token?{'Authorization':'Bearer '+token}:{})},
    ...(body?{body:JSON.stringify(body)}:{}),
    cache:'no-store',
  });
  const data:unknown=await response.json().catch(()=>null);
  if(!response.ok){
    const error=data&&typeof data==='object'&&'error' in data ? String(data.error) : 'request_failed';
    throw new Error(error.replace(/_/g,' '));
  }
  return data as T;
}
export async function shareFamilyActivity(connection:FamilyConnection, itemId:string,
    mode:'learn'|'read'|'listen'|'speak',region:string):Promise<boolean>{
  const result=await familyRequest<{accepted:boolean}>(
    '/api/v2/family/groups/'+connection.groupId+'/activity','POST',
    {item_id:itemId,mode,region},connection.token);
  return result.accepted;
}
