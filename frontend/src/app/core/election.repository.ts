import { Service,inject } from '@angular/core';
import { HttpClient,HttpParams } from '@angular/common/http';
import { firstValueFrom,fromEvent,takeUntil,timer,switchMap,retry,throwError } from 'rxjs';
import { Catalog,Shapes,MapData,MapFilters,Option,TerritoryCandidate } from './models';
export interface ElectionRepository {
 catalog():Promise<Catalog>;geometry(level:string):Promise<Shapes>;
 data(filters:MapFilters,signal:AbortSignal):Promise<MapData>;
 candidates(office:string,round:string):Promise<Option[]>;
 areaCandidates(filters:MapFilters,key:string,signal:AbortSignal):Promise<TerritoryCandidate[]>;
}
@Service()
export class HttpElectionRepository implements ElectionRepository {
 private readonly http=inject(HttpClient);
 catalog(){return firstValueFrom(this.http.get<Catalog>('/map/catalog'));}
 geometry(level:string){return firstValueFrom(this.http.get<Shapes>('/map/geometry/'+level));}
 data(filters:MapFilters,signal:AbortSignal){
  let params=new HttpParams();
  for(const [key,value] of Object.entries(filters)){
   if(Array.isArray(value)){for(const item of value)params=params.append(key,item);}
   else params=params.set(key,value);
  }
  return firstValueFrom(timer(150).pipe(
   switchMap(()=>this.http.get<MapData>('/map/data',{params})),
   retry({count:3,delay:(error,count)=>error.status===429?timer(200*count):throwError(()=>error)}),
   takeUntil(fromEvent(signal,'abort'))));
 }
 areaCandidates(filters:MapFilters,key:string,signal:AbortSignal){
  let params=new HttpParams({fromObject:{office:filters.office,round:filters.round,level:filters.level,key}});
  for(const neighborhood of filters.neighborhoods)params=params.append('neighborhoods',neighborhood);
  for(const candidate of filters.candidate_ids)params=params.append('candidate_ids',candidate);
  return firstValueFrom(this.http.get<TerritoryCandidate[]>('/map/area-candidates',{params}).pipe(
   retry({count:3,delay:(error,count)=>error.status===429?timer(200*count):throwError(()=>error)}),
   takeUntil(fromEvent(signal,'abort'))));
 }
 async candidates(office:string,round:string){
  const all:Option[]=[];
  for(let offset=0;offset<5000;offset+=500){
   const page=await firstValueFrom(this.http.get<{candidate_id:number;candidate_name:string;number:number;party:string}[]>('/candidates',{params:{office,round,limit:500,offset}}));
   all.push(...page.map(c=>({id:String(c.candidate_id),label:`${c.candidate_name} · ${c.number} · ${c.party??'—'}`})));
   if(page.length<500)break;
  }
  return all;
 }
}
