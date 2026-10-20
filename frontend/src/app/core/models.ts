import type { FeatureCollection, Geometry } from 'geojson';
export interface City { municipality:number;name:string;ibge:number;region:string;region_name:string;immediate:string;immediate_name:string; }
export interface Neighborhood { key:string;municipality:number;name:string;geometry:string|null; }
export interface Catalog { municipalities:City[];neighborhoods:Neighborhood[];regions:{id:string;name:string}[];immediate_regions:{id:string;name:string}[]; }
export interface AreaProperties { key:string;name:string;municipality:number;municipality_name?:string;kind:'municipality'|'official'|'estimated';anchor?:[number,number]; }
export type Shapes=FeatureCollection<Geometry,AreaProperties>;
export interface Candidate { candidate_id:number;name:string;party:string;number:number;votes:number; }
export interface AreaCandidate {candidate_id:number;name:string;party:string;votes:number;position:number;national_votes:number|null;national_share_pct:number|null;}
export interface Area { key:string;total:number;votes:Record<string,number>;others:number;top_five:AreaCandidate[];winner?:TerritoryWinner; }
export interface MapData { areas:Area[];candidates:Candidate[];total:number;mapped_total:number;unmapped_total:number;level:string; }
export interface MapFilters { office:string;round:string;level:string;municipalities:string[];regions:string[];immediate_regions:string[];neighborhoods:string[];candidate_ids:string[]; }
export interface Option { id:string;label:string; }
export interface LegendEntry { id:string;name:string;party:string;color:string;votes:number; }

export interface TerritoryCandidate {candidate_id:number;name:string;party:string;number:number;votes:number;local_share_pct:number;}
export interface TerritoryRow {key:string;name:string;city:string;kind:string;votes:number;total:number;}

export interface TerritoryWinner {candidate_id:number;name:string;party:string;votes:number;runner_up:{candidate_id:number;name:string;votes:number}|null;tied:boolean;margin_votes:number;margin_pp:number;}
