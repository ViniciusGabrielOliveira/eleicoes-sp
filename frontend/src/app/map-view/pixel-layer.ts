import * as L from 'leaflet';
import { Area,AreaProperties,LegendEntry,Shapes } from '../core/models';
import { packSymbols,symbolDiameter,displayedVotes,votesPerSquarePixel,VoteSymbol } from './symbols';
import { bindVoteTooltip } from './tooltip';

export class PixelLayer extends L.Layer {
 private canvas=document.createElement('canvas');
 private mapRef!:L.Map;
 private shapes:Shapes={type:'FeatureCollection',features:[]};
 private data=new Map<string,Area>();
 private legend:LegendEntry[]=[];
 private pixel=6;
 private winner=false;
 private hiddenAreaKeys:ReadonlySet<string>=new Set();
 private frame=0;
 private targets=L.layerGroup();
 private renderer?:L.SVG;
 constructor(private tooltip:(p:AreaProperties)=>HTMLElement,private inspect:(p:AreaProperties)=>void,private scaleChanged:(n:number)=>void,private visibleChanged:(keys:string[])=>void){super();}
 override onAdd(map:L.Map){
  this.mapRef=map;this.canvas.className='leaflet-layer electoral-pixels';
  this.canvas.style.pointerEvents='none';this.canvas.style.position='absolute';
  const pane=map.getPane('votePixels')||map.createPane('votePixels');
  pane.style.zIndex='450';pane.style.pointerEvents='none';pane.appendChild(this.canvas);
  const hitPane=map.getPane('voteTargets')||map.createPane('voteTargets');hitPane.style.zIndex='449';
  this.renderer=L.svg({pane:'voteTargets',padding:0});
  this.targets.addTo(map);
  map.on('moveend resize',this.schedule,this);
  map.on('zoomstart',this.hide,this);map.on('zoomend',this.reveal,this);
  this.schedule();return this;
 }
 override onRemove(map:L.Map){
  map.off('moveend resize',this.schedule,this);map.off('zoomstart',this.hide,this);map.off('zoomend',this.reveal,this);
  cancelAnimationFrame(this.frame);this.canvas.remove();this.targets.remove();this.renderer?.remove();return this;
 }
 private hide=()=>{this.canvas.style.visibility='hidden';};
 private reveal=()=>{this.draw();this.canvas.style.visibility='visible';};
 setData(shapes:Shapes,areas:Area[],legend:LegendEntry[],pixel:number,winner=false,hiddenAreaKeys:ReadonlySet<string>=new Set()){
  this.shapes=shapes;this.data=new Map(areas.map(a=>[a.key,a]));this.legend=legend;this.pixel=pixel;this.winner=winner;this.hiddenAreaKeys=hiddenAreaKeys;this.schedule();
 }
 private schedule=()=>{cancelAnimationFrame(this.frame);this.frame=requestAnimationFrame(()=>this.draw());};
 private draw(){
  if(!this.mapRef)return;
  const map=this.mapRef,size=map.getSize(),ratio=window.devicePixelRatio||1;
  L.DomUtil.setPosition(this.canvas,map.containerPointToLayerPoint([0,0]));
  this.canvas.width=size.x*ratio;this.canvas.height=size.y*ratio;
  this.canvas.style.width=size.x+'px';this.canvas.style.height=size.y+'px';
  const ctx=this.canvas.getContext('2d')!;ctx.scale(ratio,ratio);
  if(this.winner){this.drawWinners(ctx,size);return;}
  const features=this.shapes.features.filter(f=>{
   const area=this.data.get(f.properties.key);return !this.hiddenAreaKeys.has(f.properties.key)&&area&&displayedVotes(area,this.legend)>0;
  });
  // A escala de referência usa todos os votos e não aumenta ao esconder candidatos.
  const maxVotes=this.shapes.features.reduce((max,f)=>{
   const total=this.data.get(f.properties.key)?.total||0;
   return Math.max(max,total*4/Math.PI);
  },0);
  // Uma escala única para todos os blocos, sem normalizar por bairro ou candidato.
  const scale=Math.max(votesPerSquarePixel(map.getZoom()),maxVotes/(Math.min(size.x,size.y)*.38)**2);
  this.scaleChanged(scale*this.pixel**2);
  const symbols:VoteSymbol[]=[];
  const properties=new Map<string,AreaProperties>();
  for(const f of features){
   const area=this.data.get(f.properties.key)!;
   const anchor=f.properties.anchor;
   const latlng=anchor?L.latLng(anchor[1],anchor[0]):L.geoJSON(f).getBounds().getCenter();
   const point=map.latLngToContainerPoint(latlng);
   if(point.x<0||point.y<0||point.x>size.x||point.y>size.y)continue;
   properties.set(f.properties.key,f.properties);
   const votes=displayedVotes(area,this.legend);
   const side=symbolDiameter(votes,scale);
   symbols.push({key:f.properties.key,x:point.x,y:point.y,anchorX:point.x,anchorY:point.y,side});
  }
  this.targets.clearLayers();
  const packed=packSymbols(symbols,size.x,size.y);
  this.visibleChanged(packed.map(s=>s.key));
  for(const symbol of packed){
   const area=this.data.get(symbol.key)!,side=symbol.side,x=symbol.x-side/2,y=symbol.y-side/2;
   const props=properties.get(symbol.key)!;
   const total=displayedVotes(area,this.legend),radius=side/2;
   if(Math.hypot(symbol.x-symbol.anchorX,symbol.y-symbol.anchorY)>2){
    ctx.strokeStyle='#52684f88';ctx.lineWidth=.65;ctx.beginPath();
    ctx.moveTo(symbol.anchorX,symbol.anchorY);ctx.lineTo(symbol.x,symbol.y);ctx.stroke();
    ctx.fillStyle='#52684f';ctx.fillRect(symbol.anchorX-1,symbol.anchorY-1,2,2);
   }
   let angle=-Math.PI/2;
   // Fatias de cidades e bairros preservam a mesma área por voto.
   for(const entry of this.legend){
    const votes=entry.id==='others'?area.others:(area.votes[entry.id]||0);
    if(votes<=0)continue;
    ctx.fillStyle=entry.color;
     const next=angle+2*Math.PI*votes/total;
     ctx.beginPath();ctx.moveTo(symbol.x,symbol.y);ctx.arc(symbol.x,symbol.y,radius,angle,next);ctx.closePath();ctx.fill();angle=next;
   }
   ctx.save();ctx.beginPath();
   ctx.arc(symbol.x,symbol.y,radius,0,2*Math.PI);
   ctx.clip();
   ctx.strokeStyle='#ffffff66';ctx.lineWidth=.45;
   if(side>=this.pixel)for(let at=this.pixel;at<side;at+=this.pixel){
    ctx.beginPath();ctx.moveTo(x+at,y);ctx.lineTo(x+at,y+side);ctx.moveTo(x,y+at);ctx.lineTo(x+side,y+at);ctx.stroke();
   }
   ctx.restore();ctx.strokeStyle='#ffffff';ctx.lineWidth=.65;
   ctx.beginPath();ctx.arc(symbol.x,symbol.y,radius+.35,0,2*Math.PI);ctx.stroke();
   // Alvo inclui apenas o bloco real: não amplia símbolos pequenos nem altera sua área.
   const options={renderer:this.renderer,pane:'voteTargets',stroke:false,fill:true,fillOpacity:0};
   const target=L.circleMarker(map.containerPointToLatLng([symbol.x,symbol.y]),{...options,radius})
    .on('click',()=>this.inspect(props)).addTo(this.targets);
   bindVoteTooltip(target,map,()=>this.tooltip(props));
   target.getElement()?.setAttribute('data-area-key',props.key);
   target.getElement()?.setAttribute('data-symbol-shape','circle');
  }
  // Nomes permanentes no mapa, sem abrir hover sobre polígonos.
  // O halo claro preserva a leitura; omitir colisões em vistas muito densas.
  ctx.font='600 11px Inter, Segoe UI, Arial';ctx.textAlign='center';ctx.textBaseline='middle';
  const occupied:{x:number;y:number;w:number;h:number}[]=[];
  for(const symbol of packed){
   const props=properties.get(symbol.key)!;
   const text=props.name,w=ctx.measureText(text).width+8,h=17;
   const x=symbol.anchorX,y=symbol.anchorY-symbol.side/2-12;
   if(x-w/2<4||x+w/2>size.x-4||y-h/2<4||y+h/2>size.y-4)continue;
   if(occupied.some(b=>Math.abs(b.x-x)<(b.w+w)/2&&Math.abs(b.y-y)<(b.h+h)/2))continue;
   occupied.push({x,y,w,h});ctx.lineWidth=3;ctx.strokeStyle='#fffffff2';ctx.strokeText(text,x,y);
   ctx.fillStyle=props.kind==='municipality'?'#203d31':'#405140';ctx.fillText(text,x,y);
  }
 }
 private drawWinners(ctx:CanvasRenderingContext2D,size:L.Point){
  this.targets.clearLayers();
  const visible:string[]=[],occupied:{x:number;y:number;w:number}[]=[];
  ctx.textAlign='center';ctx.textBaseline='middle';
  for(const feature of this.shapes.features){
   const p=feature.properties,area=this.data.get(p.key),winner=area?.winner;
   if(!winner)continue;
   const anchor=p.anchor;
   const latlng=anchor?L.latLng(anchor[1],anchor[0]):L.geoJSON(feature).getBounds().getCenter();
   // A tabela acompanha também polígonos parcialmente visíveis.
   if(!this.mapRef.getBounds().intersects(L.geoJSON(feature).getBounds()))continue;
   visible.push(p.key);
   const point=this.mapRef.latLngToContainerPoint(latlng),x=point.x,y=point.y;
   if(x<5||y<20||x>size.x-5||y>size.y-25)continue;
   const margin=winner.tied?'Empate':(winner.runner_up?'+':'Único · +')+new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2,minimumFractionDigits:2}).format(winner.margin_pp)+' p.p.';
   ctx.font='600 11px Inter, Segoe UI, Arial';
   const w=Math.max(ctx.measureText(p.name).width,ctx.measureText(margin).width)+10;
   if(occupied.some(b=>Math.abs(b.x-x)<(b.w+w)/2&&Math.abs(b.y-y)<36))continue;
   occupied.push({x,y,w});ctx.lineWidth=4;ctx.strokeStyle='#fffffff2';ctx.fillStyle='#203d31';
   ctx.strokeText(p.name,x,y-8);ctx.fillText(p.name,x,y-8);
   ctx.font='700 12px Inter, Segoe UI, Arial';ctx.strokeText(margin,x,y+9);ctx.fillText(margin,x,y+9);
  }
  this.visibleChanged(visible);
 }

}
