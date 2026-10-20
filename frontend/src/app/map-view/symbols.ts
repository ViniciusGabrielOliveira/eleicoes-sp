/** A área, e não o lado, cresce linearmente com os votos. */
export function votesPerSquarePixel(zoom:number):number{
 return 1500/2**(Math.min(zoom,13)-6);
}
export function symbolSide(votes:number,scale:number):number{
 return Math.sqrt(Math.max(0,votes)/scale);
}
export function symbolDiameter(votes:number,scale:number):number{
 return 2*Math.sqrt(Math.max(0,votes)/(Math.PI*scale));
}
/** Apenas categorias presentes na legenda são desenhadas; totais e percentuais de origem ficam intactos. */
export function displayedVotes(area:Area,legend:readonly LegendEntry[]):number{
 return legend.reduce((sum,c)=>sum+(c.id==='others'?area.others:(area.votes[c.id]||0)),0);
}
export interface VoteSymbol {key:string;x:number;y:number;side:number;anchorX:number;anchorY:number;}
/** Desloca blocos para evitar sobreposição, sem alterar a área de nenhum deles. */
export function packSymbols(input:VoteSymbol[],width:number,height:number):VoteSymbol[]{
 const placed:VoteSymbol[]=[],grid=new Map<string,VoteSymbol[]>(),bucket=32;
 const keys=(s:VoteSymbol)=>{
  const result:string[]=[];
  for(let x=Math.floor((s.x-s.side/2-1)/bucket);x<=Math.floor((s.x+s.side/2+1)/bucket);x++)
   for(let y=Math.floor((s.y-s.side/2-1)/bucket);y<=Math.floor((s.y+s.side/2+1)/bucket);y++)result.push(x+','+y);
  return result;
 };
 const fits=(s:VoteSymbol)=>{
  if(s.x-s.side/2<1||s.y-s.side/2<1||s.x+s.side/2>width-1||s.y+s.side/2>height-1)return false;
  for(const key of keys(s))for(const p of grid.get(key)||[])
   if(Math.abs(p.x-s.x)<(p.side+s.side)/2+1&&Math.abs(p.y-s.y)<(p.side+s.side)/2+1)return false;
  return true;
 };
 for(const original of [...input].sort((a,b)=>b.side-a.side||a.key.localeCompare(b.key))){
  let symbol={...original},found=false;
  for(let radius=0;radius<=Math.max(width,height)&&!found;radius+=6){
   const samples=radius===0?1:24;
   for(let i=0;i<samples;i++){
    const angle=2*Math.PI*i/samples;
    const candidate={...original,x:original.x+radius*Math.cos(angle),y:original.y+radius*Math.sin(angle)};
    if(fits(candidate)){symbol=candidate;found=true;break;}
   }
  }
  // Se o recorte não comportar todos, manter a escala e a âncora; nunca reduzir votos.
  placed.push(symbol);for(const key of keys(symbol)){const values=grid.get(key)||[];values.push(symbol);grid.set(key,values);}
 }
 return placed;
}
import type {Area,LegendEntry} from '../core/models';

