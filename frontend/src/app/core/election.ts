import { Service,inject } from '@angular/core';
import { HttpElectionRepository,ElectionRepository } from './election.repository';
import { MapFilters } from './models';

@Service()
export class Election {
 private readonly repository:ElectionRepository=inject(HttpElectionRepository);
 async bootstrap(){
  const [catalog,cities,neighborhoods]=await Promise.all([this.repository.catalog(),this.repository.geometry('municipality'),this.repository.geometry('neighborhood')]);
  return {catalog,cities,neighborhoods};
 }
 data(filters:MapFilters,signal:AbortSignal){return this.repository.data(filters,signal);}
 areaCandidates(filters:MapFilters,key:string,signal:AbortSignal){return this.repository.areaCandidates(filters,key,signal);}
 candidates(office:string,round:string){return this.repository.candidates(office,round);}
}
