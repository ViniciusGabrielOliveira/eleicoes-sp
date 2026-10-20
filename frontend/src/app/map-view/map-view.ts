import { Component,ElementRef,afterRenderEffect,computed,input,output,viewChild,DestroyRef,inject } from '@angular/core';
import * as L from 'leaflet';
import { Shapes,MapData,LegendEntry,AreaProperties } from '../core/models';
import { PixelLayer } from './pixel-layer';

@Component({selector:'app-map-view',imports:[],templateUrl:'./map-view.html',styleUrl:'./map-view.css'})
export class MapView {
 readonly shapes=input.required<Shapes>();
 readonly cities=input.required<Shapes>();
 readonly data=input<MapData>();
 readonly legend=input<LegendEntry[]>([]);
 readonly pixel=input(6);
 readonly winnerView=input(false);
 readonly winnerColors=input<Record<string,string>>({});
 readonly fitKey=input('');
 readonly focusKeys=input<string[]>([]);
 readonly zoomChanged=output<number>();
 readonly visibleChanged=output<string[]>();
 readonly inspected=output<AreaProperties>();
 readonly scaleChanged=output<number>();
 private readonly host=viewChild.required<ElementRef<HTMLDivElement>>('map');
 private readonly destroyRef=inject(DestroyRef);
 private map?:L.Map;
 private pixels?:PixelLayer;
 private boundaries?:L.GeoJSON;
 private lastFit='__initial__';
 private lastShapes?:Shapes;
 private observer?:ResizeObserver;
 constructor(){
  afterRenderEffect(()=>{
   const shapes=this.shapes(),data=this.data(),legend=this.legend(),pixel=this.pixel(),fitKey=this.fitKey(),focus=this.focusKeys(),winner=this.winnerView(),colors=this.winnerColors();
   if(!this.map){
    this.map=L.map(this.host().nativeElement,{zoomControl:false,minZoom:5,maxZoom:17,preferCanvas:true,zoomSnap:.25}).setView([-22.5,-48.5],6.5);
    L.control.zoom({position:'bottomright'}).addTo(this.map);
    L.control.scale({imperial:false,position:'bottomleft'}).addTo(this.map);
    this.map.attributionControl.setPrefix(false);
    this.map.attributionControl.addAttribution('Malhas © IBGE · Votos © TSE');
    this.map.on('zoomend',()=>this.zoomChanged.emit(this.map!.getZoom()));
    this.pixels=new PixelLayer(p=>this.tooltip(p),p=>this.inspected.emit(p),n=>this.scaleChanged.emit(n),keys=>this.visibleChanged.emit(keys)).addTo(this.map);
    this.observer=new ResizeObserver(()=>this.map?.invalidateSize());
    this.observer.observe(this.host().nativeElement);
   }
   if(this.lastShapes!==shapes){
    this.boundaries?.remove();
    this.boundaries=L.geoJSON(shapes,{
     style:f=>({color:'#7d9186',weight:f?.properties.kind==='municipality'?.7:.7,opacity:.8,fillColor:'#f5f7f3',fillOpacity:1,dashArray:f?.properties.kind==='estimated'?'3 3':undefined}),
     onEachFeature:(feature,layer)=>{
      layer.on('click',()=>this.inspected.emit(feature.properties));
     }
    }).addTo(this.map);
    this.lastShapes=shapes;
   }
   const areas=new Map(data?.areas.map(a=>[a.key,a]));
   this.boundaries?.setStyle(feature=>{
    const w=areas.get(feature?.properties.key)?.winner;
    return {fillColor:winner?(w?(w.tied?'#78877e':colors[String(w.candidate_id)]||'#78877e'):'#e7ede6'):'#f5f7f3',fillOpacity:winner?.78:1};
   });
   this.pixels!.setData(shapes,data?.areas||[],legend,pixel,winner);
   if(this.lastFit!==fitKey){
    const geometry=focus.length?{...shapes,features:shapes.features.filter(f=>focus.includes(f.properties.key))}:this.cities();
    const bounds=L.geoJSON(geometry as Shapes).getBounds();
    if(bounds.isValid())this.map.fitBounds(bounds,{padding:[35,35],maxZoom:13,animate:this.lastFit!=='__initial__'});
    this.lastFit=fitKey;
   }
  });
  this.destroyRef.onDestroy(()=>{this.observer?.disconnect();this.map?.remove();});
 }
 private tooltip(properties:AreaProperties):HTMLElement{
  const root=document.createElement('div');
  const title=document.createElement('strong');title.textContent=properties.name;root.append(title);
  const caption=document.createElement('small');caption.textContent=(properties.municipality_name||'')+
   (properties.kind==='estimated'?' · área aproximada':'');root.append(caption);
  const area=this.data()?.areas.find(a=>a.key===properties.key);
  const heading=document.createElement('p');heading.textContent='5 mais votados · % do total nacional do candidato';root.append(heading);
  const format=(n:number)=>new Intl.NumberFormat('pt-BR').format(n);
  for(const candidate of area?.top_five||[]){
   const line=document.createElement('div');line.className='tooltip-candidate';
   const name=document.createElement('span');name.textContent=candidate.position+'. '+candidate.name;
   const votes=document.createElement('b');
   const percent=candidate.national_share_pct===null?'% indisponível':new Intl.NumberFormat('pt-BR',{maximumFractionDigits:6}).format(candidate.national_share_pct)+'%';
   votes.textContent=format(candidate.votes)+' votos — '+percent;
   line.append(name,votes);root.append(line);
  }
  if(!area?.top_five?.length){const empty=document.createElement('p');empty.textContent='Sem votos neste recorte';root.append(empty);}
  return root;
 }
 reset(){const bounds=L.geoJSON(this.cities()).getBounds();this.map?.fitBounds(bounds,{padding:[30,30]});}
}
