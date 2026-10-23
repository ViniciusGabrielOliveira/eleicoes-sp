import { Area } from './models';

/** Compara votos selecionados com o máximo calculado antes do filtro de candidatos. */
export function hiddenNonLeadingAreas(areas:readonly Area[],selected:readonly string[]):Set<string>{
 if(!selected.length)return new Set();
 return new Set(areas.filter(area=>{
  const leader=area.leader_votes??area.winner?.votes;
  return leader===undefined||leader<=0||!selected.some(id=>(area.votes[id]||0)===leader);
 }).map(area=>area.key));
}
