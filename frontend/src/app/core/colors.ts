/** Paleta discreta; evita tons vizinhos gerados por hash nas pizzas. */
const PALETTE=['#d62728','#1764c0','#ffbd00','#008754','#8b43b5','#ff7900','#00bfd1','#d64b99','#55351d','#202737','#a2c83a','#f3a6be'];
const PRESIDENT:Record<string,string>={PT:'#d62728',PL:'#1764c0'};

/** Distância perceptual em OKLab, incluindo diferenças de luminosidade. */
function perceptual(color:string):number[]{
 const rgb=[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)/255)
  .map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
 const [r,g,b]=rgb;
 const l=Math.cbrt(.4122214708*r+.5363325363*g+.0514459929*b);
 const m=Math.cbrt(.2119034982*r+.6806995451*g+.1073969566*b);
 const s=Math.cbrt(.0883024619*r+.2817188376*g+.6299787005*b);
 return [.2104542553*l+.793617785*m-.0040720468*s,1.9779984951*l-2.428592205*m+.4505937099*s,.0259040371*l+.7827717662*m-.808675766*s];
}
const distance=(a:number[],b:number[])=>a.reduce((sum,v,i)=>sum+(v-b[i])**2,0);

/** Reserva cores personalizadas e escolhe a cor mais distante das já usadas.
 * Ordem por ID mantém as cores ao reordenar o ranking do mesmo grupo.
 */
export function candidateColors(candidates:readonly {candidate_id:number;party:string}[],office:string,
 overrides:Readonly<Record<string,string>>={}):Record<string,string>{
 const colors:Record<string,string>={};
 const used=['#78877e']; // Categoria Outros também precisa se distinguir.
 const ordered=[...candidates].sort((a,b)=>a.candidate_id-b.candidate_id);
 for(const c of ordered){
  const fixed=overrides[String(c.candidate_id)]||(office==='1'?PRESIDENT[c.party]:undefined);
  if(fixed){colors[String(c.candidate_id)]=fixed;used.push(fixed);}
 }
 for(const c of ordered){
  const id=String(c.candidate_id);if(colors[id])continue;
  const references=used.map(perceptual);
  let best=PALETTE[0],score=-1;
  for(const color of PALETTE){
   if(used.includes(color))continue;
   const point=perceptual(color),separation=Math.min(...references.map(p=>distance(point,p)));
   if(separation>score){best=color;score=separation;}
  }
  colors[id]=best;used.push(best);
 }
 return colors;
}
