import type {FamilyMember} from './api';

export type RecognitionCategory='effort'|'consistency'|'difficulty'|'team'|'improvement';
export const RECOGNITION_CATEGORIES: {id:RecognitionCategory;label:string;description:string}[]=[
  {id:'effort',label:'Effort',description:'Eligible XP earned this week, regardless of whether every answer was correct.'},
  {id:'consistency',label:'Consistency',description:'Number of separate days with qualifying practice this week.'},
  {id:'difficulty',label:'Trailblazer',description:'Highest catalog difficulty tier practised this week. This is not a mastery grade.'},
  {id:'team',label:'Team contribution',description:'Eligible expedition XP contributed to your family map this week.'},
  {id:'improvement',label:'Most improved',description:'Reserved for measured change from each learner’s own validated baseline.'},
];
type Supported=Exclude<RecognitionCategory,'improvement'>;
export function recognitionScore(member:FamilyMember,category:Supported):number{
  switch(category){
    case 'effort':return member.weekly_xp;
    case 'consistency':return member.active_days;
    case 'difficulty':return member.highest_tier;
    case 'team':return member.team_xp;
  }
}
export function recognitionLabel(category:Supported,score:number):string{
  if(category==='consistency')return score+' '+(score===1?'day':'days');
  if(category==='difficulty')return score>0?'Tier '+score:'—';
  return score+(category==='team'?' map XP':' XP');
}
export function rankFamily(members:FamilyMember[],category:Supported){
  const sorted=members.slice().sort((a,b)=>
    recognitionScore(b,category)-recognitionScore(a,category) ||
    a.name.localeCompare(b.name)||a.id-b.id);
  return sorted.map(member=>{
    const score=recognitionScore(member,category);
    const rank=score===0?null:
      sorted.findIndex(other=>recognitionScore(other,category)===score)+1;
    return {member,score,rank};
  });
}
