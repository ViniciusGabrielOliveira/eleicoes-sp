import {describe,it,expect} from 'vitest';
import {hiddenNonLeadingAreas} from './leader-filter';
import {Area} from './models';

const area=(key:string,votes:Record<string,number>,leader_votes?:number):Area=>({key,votes,leader_votes,total:200,others:100,top_five:[]});
describe('Filtro de liderança por bairro',()=>{
 const areas=[area('lider',{'1':80},80),area('perde',{'1':20},100),area('empate',{'1':50,'2':50},50),area('outro',{'2':90},90),area('sem-votos',{},0)];
 it('não transforma o único selecionado em líder quando outro candidato tem mais votos',()=>{
  expect([...hiddenNonLeadingAreas(areas,['1'])]).toEqual(['perde','outro','sem-votos']);
 });
 it('inclui empates e a liderança de qualquer candidato selecionado',()=>{
  expect([...hiddenNonLeadingAreas(areas,['1','2'])]).toEqual(['perde','sem-votos']);
 });
 it('não filtra sem seleção e não presume liderança sem dados',()=>{
  expect(hiddenNonLeadingAreas(areas,[]).size).toBe(0);
  expect([...hiddenNonLeadingAreas([area('desconhecido',{'1':20})],['1'])]).toEqual(['desconhecido']);
 });
});
