export {};
declare global {
 var GolgeImages: {confirmCost:(detail:string,signal?:AbortSignal)=>Promise<boolean>;resolve:(text:string)=>'generate'|'edit'|null;options:(text:string)=>{aspect_ratio:string;style:string}};
}
