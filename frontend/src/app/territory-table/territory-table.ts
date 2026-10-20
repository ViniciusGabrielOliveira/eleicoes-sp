import {Component,computed,inject,input,linkedSignal,resource} from '@angular/core';
import {Election} from '../core/election';
import {MapFilters,TerritoryRow} from '../core/models';

@Component({selector:'app-territory-table',templateUrl:'./territory-table.html',styleUrl:'./territory-table.css'})
export class TerritoryTable {
 readonly rows=input<TerritoryRow[]>([]);
 readonly winnerView=input(false);
 readonly filters=input<MapFilters>();
 private readonly service=inject(Election);
 readonly expanded=linkedSignal({source:()=>JSON.stringify(this.filters()),computation:():string|null=>null});
 readonly active=computed(()=>this.rows().find(row=>row.key===this.expanded()));
 readonly details=resource({params:()=>{
  const filters=this.filters(),row=this.active();return filters&&row?{filters,key:row.key}:undefined;
 },loader:({params,abortSignal})=>this.service.areaCandidates(params.filters,params.key,abortSignal)});
 toggle(key:string){this.expanded.update(value=>value===key?null:key);}
 number(n:number){return new Intl.NumberFormat('pt-BR').format(n);}
 percent(n:number){return new Intl.NumberFormat('pt-BR',{maximumFractionDigits:2}).format(n)+'%';}
}
