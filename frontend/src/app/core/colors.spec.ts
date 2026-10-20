import {describe,it,expect} from 'vitest';
import {candidateColors} from './colors';

describe('Cores das pizzas',()=>{
 const candidates=Array.from({length:10},(_,i)=>({candidate_id:i+1,party:i===0?'PT':i===1?'PL':'OUTRO'}));
 it('distingue até dez selecionados e a categoria Outros',()=>{
  const colors=candidateColors(candidates,'1');
  expect(new Set(Object.values(colors)).size).toBe(10);
  expect(Object.values(colors)).not.toContain('#78877e');
  expect(colors['1']).toBe('#d62728');expect(colors['2']).toBe('#1764c0');
 });
 it('mantém cores ao mudar a ordem do ranking',()=>{
  expect(candidateColors([...candidates].reverse(),'6')).toEqual(candidateColors(candidates,'6'));
 });
 it('respeita escolhas manuais e reserva essas cores',()=>{
  const colors=candidateColors(candidates,'1',{'1':'#008754','3':'#ffbd00'});
  expect(colors['1']).toBe('#008754');expect(colors['3']).toBe('#ffbd00');
  expect(new Set(Object.values(colors)).size).toBe(10);
 });
});
