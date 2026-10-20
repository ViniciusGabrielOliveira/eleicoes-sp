import {describe,it,expect} from 'vitest';
import {symbolSide,symbolDiameter,displayedVotes,votesPerSquarePixel,packSymbols,VoteSymbol} from './symbols';
import type {Area,LegendEntry} from '../core/models';

describe('Blocos com área proporcional ao número absoluto de votos',()=>{
 it('o dobro de votos ocupa o dobro da área, e não o dobro do lado',()=>{
  const small=symbolSide(1000,25),large=symbolSide(2000,25);
  expect(large*large).toBeCloseTo(2*small*small);
  expect(large).toBeCloseTo(small*Math.SQRT2);
 });
 it('2000 votos de um candidato têm a mesma área em bairros com totais diferentes',()=>{
  const scale=votesPerSquarePixel(10);
  const area=(votes:number,total:number)=>{
   const side=symbolSide(total,scale);
   return (side*votes/total)*side;
  };
  expect(area(2000,10000)).toBeCloseTo(area(2000,100000));
  expect(area(2000,10000)).toBeCloseTo(2000/scale);
 });
 it('a geometria do bairro não entra no cálculo e valores pequenos não são inflados',()=>{
  expect(symbolSide(1,1500)**2).toBeCloseTo(1/1500);
  expect(symbolSide(0,1500)).toBe(0);
 });
 it('círculos e quadrados representam a mesma área por voto',()=>{
  for(const votes of [1,1000,2000,50000]){
   const scale=25,r=symbolDiameter(votes,scale)/2;
   expect(Math.PI*r*r).toBeCloseTo(symbolSide(votes,scale)**2);
   expect(Math.PI*r*r*.3).toBeCloseTo(votes*.3/scale);
  }
 });
 it('o filtro desenha apenas os votos escolhidos, sem outros nem inflar a área',()=>{
  const area:Area={key:'1',total:1000,votes:{a:200,b:300},others:500,top_five:[]};
  const entry=(id:string):LegendEntry=>({id,name:id,party:'',color:'#000000',votes:0});
  const original=JSON.stringify(area);
  expect(displayedVotes(area,[entry('a')])).toBe(200);
  expect(displayedVotes(area,[entry('a'),entry('b')])).toBe(500);
  expect(displayedVotes(area,[entry('a'),entry('b'),entry('others')])).toBe(1000);
  expect(displayedVotes(area,[entry('sem-votos')])).toBe(0);
  const radius=symbolDiameter(displayedVotes(area,[entry('a')]),25)/2;
  expect(Math.PI*radius*radius).toBeCloseTo(200/25);
  expect(JSON.stringify(area)).toBe(original);
 });
 it('desloca blocos colidentes sem alterar seus tamanhos ou âncoras',()=>{
  const input:VoteSymbol[]=Array.from({length:5},(_,i)=>({key:String(i),x:100,y:100,anchorX:100,anchorY:100,side:20}));
  const packed=packSymbols(input,300,300);
  expect(packed).toHaveLength(5);
  for(const p of packed){expect(p.side).toBe(20);expect(p.anchorX).toBe(100);expect(p.anchorY).toBe(100);}
  for(let i=0;i<packed.length;i++)for(let j=i+1;j<packed.length;j++){
   expect(Math.abs(packed[i].x-packed[j].x)>=21||Math.abs(packed[i].y-packed[j].y)>=21).toBe(true);
  }
 });
});
