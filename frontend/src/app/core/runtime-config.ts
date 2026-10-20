import {HttpInterceptorFn} from '@angular/common/http';
export const runtimeConfig={apiBaseUrl:''};
export async function loadRuntimeConfig(){
 const response=await fetch(new URL('api-config.json',document.baseURI),{cache:'no-store'});
 if(!response.ok)throw new Error('Configuração da API indisponível');
 const value:unknown=await response.json();
 const url=typeof value==='object'&&value!==null&&'apiBaseUrl' in value?value.apiBaseUrl:undefined;
 if(typeof url!=='string')throw new Error('URL da API inválida');
 if(url){const parsed=new URL(url);if(parsed.protocol!=='https:'||parsed.username||parsed.password||parsed.pathname!=='/'||parsed.search||parsed.hash)throw new Error('A API pública precisa de uma origem HTTPS');}
 runtimeConfig.apiBaseUrl=url.replace(/\/$/,'');
}
export const apiOriginInterceptor:HttpInterceptorFn=(request,next)=>{
 const allowed=/^\/(map\/|candidates(?:\?|$)|health(?:\?|$))/;
 if(!runtimeConfig.apiBaseUrl||!allowed.test(request.url))return next(request);
 const url=runtimeConfig.apiBaseUrl+request.url;
 const ngrok=/(?:\.ngrok-free\.(?:app|dev)|\.ngrok\.(?:app|io))$/.test(new URL(runtimeConfig.apiBaseUrl).hostname);
 return next(request.clone({url,setHeaders:ngrok?{'ngrok-skip-browser-warning':'1'}:{}}));
};
