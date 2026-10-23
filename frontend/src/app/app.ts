import { Component,computed,inject,resource,signal,viewChild } from '@angular/core';
import { form,FormField,min,max } from '@angular/forms/signals';
import { Election } from './core/election';
import { MapView } from './map-view/map-view';
import { TerritoryTable } from './territory-table/territory-table';
import { MultiSelect } from './multi-select/multi-select';
import { AreaProperties,LegendEntry,MapFilters,Option,Shapes,TerritoryRow } from './core/models';
import {runtimeConfig} from './core/runtime-config';
import { candidateColors } from './core/colors';
import { displayedVotes } from './map-view/symbols';
import { hiddenNonLeadingAreas } from './core/leader-filter';

@Component({selector:'app-root',imports:[FormField,MapView,MultiSelect,TerritoryTable],templateUrl:'./app.html',styleUrl:'./app.css'})
export class App {
 readonly apiHealthUrl=runtimeConfig.apiBaseUrl+'/health';
 private readonly service=inject(Election);
 readonly boot=resource({loader:()=>this.service.bootstrap()});
 readonly controls=signal({office:'1',round:'1',detail:'auto',style:'pizza',pixel:6,estimated:true});
 readonly form=form(this.controls,p=>{min(p.pixel,3);max(p.pixel,12);});
 readonly regions=signal<string[]>([]);
 readonly immediateRegions=signal<string[]>([]);
 readonly cities=signal<string[]>([]);
 readonly neighborhoods=signal<string[]>([]);
 readonly candidates=signal<string[]>([]);
 readonly onlyLeaders=signal(false);
 readonly leaderFilterActive=computed(()=>this.onlyLeaders()&&!this.winnerView()&&this.level()==='neighborhood'&&this.candidates().length>0);
 readonly hiddenAreaKeys=computed(()=>this.leaderFilterActive()?hiddenNonLeadingAreas(this.result.value()?.areas||[],this.candidates()):new Set<string>());
 readonly zoom=signal(6);
 readonly votesPerCell=signal(54000);
 readonly visibleKeys=signal<string[]>([]);
 readonly inspected=signal<AreaProperties|null>(null);
 readonly colorOverrides=signal<Record<string,string>>({});
 readonly map=viewChild(MapView);
 readonly catalog=computed(()=>this.boot.value()?.catalog);
 readonly allowedCities=computed(()=>this.catalog()?.municipalities.filter(c=>
  (!this.regions().length||this.regions().includes(c.region))&&
  (!this.immediateRegions().length||this.immediateRegions().includes(c.immediate)))||[]);
 readonly effectiveCities=computed(()=>this.allowedCities().filter(c=>!this.cities().length||this.cities().includes(String(c.municipality))));
 readonly effectiveCityIds=computed(()=>new Set(this.effectiveCities().map(c=>c.municipality)));
 readonly regionOptions=computed<Option[]>(()=>this.catalog()?.regions.map(r=>({id:r.id,label:r.name}))||[]);
 readonly immediateOptions=computed<Option[]>(()=>this.catalog()?.immediate_regions.map(r=>({id:r.id,label:r.name}))||[]);
 readonly cityOptions=computed<Option[]>(()=>this.allowedCities().map(c=>({id:String(c.municipality),label:c.name})));
 readonly neighborhoodOptions=computed<Option[]>(()=>this.catalog()?.neighborhoods.filter(n=>this.effectiveCityIds().has(n.municipality)).map(n=>({id:n.key,label:n.name+' · '+(this.catalog()?.municipalities.find(c=>c.municipality===n.municipality)?.name||'')}))||[]);
 readonly winnerView=computed(()=>this.controls().office==='1'&&this.controls().style==='winner');
 readonly level=computed(()=>this.neighborhoods().length||this.controls().detail==='neighborhood'||(this.controls().detail==='auto'&&this.zoom()>=9.5)?'neighborhood':'municipality');
 readonly filters=computed<MapFilters|undefined>(()=>this.catalog()?{
  office:this.controls().office,round:this.controls().round,level:this.level(),
  municipalities:this.cities(),regions:this.regions(),immediate_regions:this.immediateRegions(),
  neighborhoods:this.neighborhoods(),candidate_ids:this.winnerView()?[]:this.candidates()
 }:undefined);
 readonly result=resource({params:()=>this.filters(),loader:({params,abortSignal})=>this.service.data(params,abortSignal)});
 readonly candidateList=resource({params:()=>({office:this.controls().office,round:this.controls().round}),loader:({params})=>this.service.candidates(params.office,params.round)});
 readonly candidateOptions=computed(()=>this.candidateList.value()||[]);
 readonly shapes=computed<Shapes>(()=>{
  const boot=this.boot.value();if(!boot)return {type:'FeatureCollection',features:[]};
  const source=this.level()==='municipality'?boot.cities:boot.neighborhoods;
  const ids=this.effectiveCityIds(),selected=this.neighborhoods();
  return {...source,features:source.features.filter(f=>ids.has(f.properties.municipality)&&
   (this.level()==='municipality'||!selected.length||selected.includes(f.properties.key))&&
   (this.controls().estimated||f.properties.kind!=='estimated'))};
 });
 readonly fitKey=computed(()=>JSON.stringify([this.regions(),this.immediateRegions(),this.cities(),this.neighborhoods()]));
 readonly focusKeys=computed(()=>this.neighborhoods().length?this.neighborhoods():this.cities().length||this.regions().length||this.immediateRegions().length?this.shapes().features.map(f=>f.properties.key):[]);
 readonly legend=computed<LegendEntry[]>(()=>{
  const result=this.result.value();if(!result)return [];
  const colors=candidateColors(result.candidates,this.controls().office,this.colorOverrides());
  const entries=result.candidates.map(c=>{
   const color=(this.winnerView()?this.winnerColors():colors)[String(c.candidate_id)];
   return {id:String(c.candidate_id),name:c.name,party:c.party,color,votes:c.votes};
  });
  if(this.candidates().length||this.winnerView())return entries;
  return [...entries,{id:'others',name:'Outros candidatos',party:'',color:'#78877e',votes:Math.max(0,result.total-entries.reduce((s,c)=>s+c.votes,0))}];
 });
 readonly winnerColors=computed(()=>{
  const candidates=new Map(this.result.value()?.candidates.map(c=>[c.candidate_id,c]));
  for(const area of this.result.value()?.areas||[]){const w=area.winner;if(w&&!candidates.has(w.candidate_id))candidates.set(w.candidate_id,{candidate_id:w.candidate_id,name:w.name,party:w.party,number:0,votes:0});}
  return candidateColors([...candidates.values()],this.controls().office,this.colorOverrides());
 });
 readonly displayedTotal=computed(()=>this.winnerView()?(this.result.value()?.total||0):this.legend().reduce((sum,c)=>sum+c.votes,0));
 readonly selectedArea=computed(()=>this.result.value()?.areas.find(a=>a.key===this.inspected()?.key));
 readonly selectedAreaVotes=computed(()=>{const area=this.selectedArea();return area?(this.winnerView()?area.total:displayedVotes(area,this.legend())):0;});
 readonly ranking=computed(()=>this.legend().map(c=>({...c,share:this.result.value()?.total?100*c.votes/this.result.value()!.total:0})));
 readonly shownVotes=computed(()=>{
  const keys=new Set(this.shapes().features.map(f=>f.properties.key));
  return this.result.value()?.areas.filter(a=>keys.has(a.key)).reduce((s,a)=>s+(this.winnerView()?a.total:displayedVotes(a,this.legend())),0)||0;
 });
 readonly territoryRows=computed<TerritoryRow[]>(()=>{
  const keys=new Set(this.visibleKeys()),data=new Map(this.result.value()?.areas.map(a=>[a.key,a]));
  return this.shapes().features.filter(f=>keys.has(f.properties.key)).flatMap(f=>{
   const a=data.get(f.properties.key);if(!a)return [];
   const votes=this.winnerView()?a.total:displayedVotes(a,this.legend());if(!votes)return [];
   return [{key:a.key,name:f.properties.name,city:f.properties.municipality_name||this.catalog()?.municipalities.find(c=>c.municipality===f.properties.municipality)?.name||f.properties.name,kind:f.properties.kind,votes,total:a.total}];
  }).sort((a,b)=>b.votes-a.votes||a.key.localeCompare(b.key));
 });
 format(n:number){return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:0}).format(n);}
 pct(n:number){return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:1,minimumFractionDigits:1}).format(n)+'%';}
 changeColor(id:string,event:Event){this.colorOverrides.update(v=>({...v,[id]:(event.target as HTMLInputElement).value}));}
 clear(){this.regions.set([]);this.immediateRegions.set([]);this.cities.set([]);this.neighborhoods.set([]);this.candidates.set([]);this.onlyLeaders.set(false);this.inspected.set(null);}
 styleChanged(){if(this.winnerView())this.candidates.set([]);}
 officeChanged(){if(this.controls().office!=='1')this.controls.update(v=>({...v,style:'pizza'}));this.candidates.set([]);this.onlyLeaders.set(false);this.inspected.set(null);}
 regionChanged(){this.cities.set([]);this.neighborhoods.set([]);this.inspected.set(null);}
 cityChanged(){this.neighborhoods.set([]);this.inspected.set(null);}
 exportCsv(){
  const data=this.result.value();if(!data)return;
  const lines=[['territorio','candidato','votos','percentual_nominal']];
  const names=new Map(this.shapes().features.map(f=>[f.properties.key,f.properties.name]));
  for(const a of data.areas)for(const c of this.legend()){
   const votes=c.id==='others'?a.others:(a.votes[c.id]||0);
   lines.push([names.get(a.key)||a.key,c.name,String(votes),String(a.total?100*votes/a.total:0)]);
  }
  const csv='\uFEFF'+lines.map(row=>row.map(v=>'"'+v.replaceAll('"','""')+'"').join(';')).join('\n');
  const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=url;a.download='atlas-eleitoral-sp-2026.csv';a.click();URL.revokeObjectURL(url);
 }
}
