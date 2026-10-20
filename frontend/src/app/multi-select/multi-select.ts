import { Component,computed,input,model,signal,viewChild,ElementRef } from '@angular/core';
import { form,FormField } from '@angular/forms/signals';
import { Option } from '../core/models';

@Component({
  imports: [FormField],
  selector: 'app-multi-select',
  styleUrl: './multi-select.css',
  templateUrl: './multi-select.html',
})
export class MultiSelect {
 readonly label=input.required<string>();
 readonly options=input<Option[]>([]);
 readonly selected=model<string[]>([]);
 readonly max=input(10000);
 readonly menu=viewChild<ElementRef<HTMLDetailsElement>>('menu');
 readonly inputId=computed(()=>'search-'+this.label().normalize('NFD').replace(/[^a-zA-Z0-9]/g,'').toLowerCase());
 readonly searchModel=signal({query:''});
 readonly search=form(this.searchModel);
 readonly filtered=computed(()=>{
  const normalize=(s:string)=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  return this.options().filter(o=>normalize(o.label).includes(normalize(this.searchModel().query))).slice(0,200);
 });
 toggle(id:string){this.selected.update(values=>values.includes(id)?values.filter(v=>v!==id):[...values,id]);}
 clear(){this.selected.set([]);}
 close(){const menu=this.menu();if(menu)menu.nativeElement.open=false;}
}
