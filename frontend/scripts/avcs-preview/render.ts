// Renderizador de referencia del AVCS — replica el pipeline real (geometría
// REAL de lotus.ts + proyección + gl_PointSize + perfil de glow + blending
// aditivo + efecto DPR) en CPU, para poder VER el resultado sin GPU.
import { buildSceneGeometry, ROLE } from "../../src/avcs/math/lotus";
import * as zlib from "zlib";
import * as fs from "fs";

const OUT_W = 900, OUT_H = 900;
const FOV = 45, CAM_Z = 8.5;

function srgb2lin(hex: string): [number,number,number] {
  const n = parseInt(hex.replace("#",""),16);
  const to = (c:number)=>{const s=c/255; return s<=0.04045? s/12.92 : Math.pow((s+0.055)/1.055,2.4);};
  return [to((n>>16)&255), to((n>>8)&255), to(n&255)];
}
const uHeart = srgb2lin("#FFD9A0"), uAura = srgb2lin("#FFC65E"), uField = srgb2lin("#7FE0C3");
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const mix3=(a:number[],b:number[],t:number):number[]=>[mix(a[0],b[0],t),mix(a[1],b[1],t),mix(a[2],b[2],t)];
function smoothstep(e0:number,e1:number,x:number){const t=Math.max(0,Math.min(1,(x-e0)/(e1-e0)));return t*t*(3-2*t);}

/** color por rol — copia literal de render.frag.glsl */
function colorFor(vRole:number, vSeed:number, vBright:number): number[] {
  if (vRole>0.95) {
    const deep=[uHeart[0]*0.95,uHeart[1]*0.52,uHeart[2]*0.24];
    const hot=mix3(uHeart,[1,1,1],0.55);
    return mix3(deep,hot,smoothstep(0.2,0.95,vBright));
  }
  if (vRole>0.85) return mix3(uHeart,uAura,0.45);
  if (vRole>0.73) return mix3(uAura,uHeart,0.3+0.25*vSeed);
  if (vRole>0.59) return mix3([uAura[0]*0.92,uAura[1]*0.92,uAura[2]*0.92],uField,(vSeed>=0.82?1:0)*0.55);
  if (vRole>0.45) return vSeed>=0.65? uAura : uField;
  if (vRole>0.31) return uField;
  if (vRole>0.18) return [uField[0]*0.9,uField[1]*0.9,uField[2]*0.9];
  return mix3(uField,[1,1,1],0.35*vSeed);
}

export interface RenderOpts {
  N: number; dprTier: number; pointSize: number; brightBoost: number;
  hardness: number;          // 0 = degradado completo (Q4 actual) … 0.4 = disco duro
  seedBoost?: number;        // reparto: cuánto del pool va al logo (1 = actual)
  label: string;
}

export function render(o: RenderOpts): Buffer {
  // framebuffer a la resolución REAL del tier (dpr/2 respecto a Q4) → reproduce
  // el blur de escalado que sufren los tiers bajos.
  const scale = o.dprTier/2;
  const W = Math.max(1,Math.round(OUT_W*scale)), H = Math.max(1,Math.round(OUT_H*scale));
  const buf = new Float32Array(W*H*3);

  const { genome, anchor } = buildSceneGeometry(o.N, 1.55, (o as any).seedFrac ?? 0.436, 12345);
  const tanHalf = Math.tan(FOV*Math.PI/360);
  const uDpr = Math.min(2,o.dprTier);

  for (let i=0;i<o.N;i++){
    const g=i*4;
    const vSeed=genome[g], vRole=genome[g+1], sizeClass=genome[g+2], brightClass=genome[g+3];
    const x=anchor[g], y=anchor[g+1], z=anchor[g+2];
    // reposo: P≈A → closeness≈1
    const tw = 0.6+0.4*Math.sin(vSeed*55.0);      // uTime=0
    const sizeMul = sizeClass*1.0*tw;
    const vBright = brightClass*1.0*tw;
    const mvz = CAM_Z - z;
    let ps = o.pointSize*sizeMul*uDpr/Math.max(0.1,mvz);
    ps = Math.max(1,Math.min(70,ps));
    const ndcX=(x/mvz)/tanHalf, ndcY=(y/mvz)/tanHalf;   // aspect 1:1
    const px=(ndcX*0.5+0.5)*W, py=(1-(ndcY*0.5+0.5))*H;
    const edge=Math.max(Math.abs(ndcX),Math.abs(ndcY));
    const edgeFalloff=1-smoothstep(0.92,1.0,edge);
    if (edgeFalloff<=0) continue;
    const col=colorFor(vRole,vSeed,vBright);
    const r=ps/2;
    const x0=Math.max(0,Math.floor(px-r)), x1=Math.min(W-1,Math.ceil(px+r));
    const y0=Math.max(0,Math.floor(py-r)), y1=Math.min(H-1,Math.ceil(py+r));
    for(let yy=y0;yy<=y1;yy++)for(let xx=x0;xx<=x1;xx++){
      const d=Math.hypot(xx+0.5-px, yy+0.5-py)/ps;   // gl_PointCoord-0.5 → 0..0.5
      if(d>0.5)continue;
      const glow=smoothstep(0.5,o.hardness,d);
      // WebGL clampa gl_FragColor a [0,1] en un render target de 8 bits: un
      // brillo alto SATURA, no suma indefinidamente. Sin este clamp la
      // calibración sobreestima lo que rinde subir el brillo.
      const a=Math.min(1, glow*vBright*o.brightBoost*0.85*edgeFalloff);
      const k=(yy*W+xx)*3, m=0.35+0.9*vBright;
      buf[k]+=col[0]*m*a; buf[k+1]+=col[1]*m*a; buf[k+2]+=col[2]*m*a;
    }
  }

  let _lum = 0; for (let k = 0; k < buf.length; k++) _lum += buf[k];
  (globalThis as any).__lastLum = _lum / (W * H);

  // upscale a OUT_W×OUT_H (bilineal) = lo que hace el navegador con dpr<2
  const px8=Buffer.alloc(OUT_W*OUT_H*3);
  const lin2srgb=(v:number)=>{const c=Math.max(0,Math.min(1,v));return Math.round(255*(c<=0.0031308?c*12.92:1.055*Math.pow(c,1/2.4)-0.055));};
  for(let y=0;y<OUT_H;y++)for(let x=0;x<OUT_W;x++){
    const sx=(x+0.5)*W/OUT_W-0.5, sy=(y+0.5)*H/OUT_H-0.5;
    const ix=Math.floor(sx), iy=Math.floor(sy), fx=sx-ix, fy=sy-iy;
    const smp=(cx:number,cy:number,c:number)=>{const X=Math.max(0,Math.min(W-1,cx)),Y=Math.max(0,Math.min(H-1,cy));return buf[(Y*W+X)*3+c];};
    for(let c=0;c<3;c++){
      const v=smp(ix,iy,c)*(1-fx)*(1-fy)+smp(ix+1,iy,c)*fx*(1-fy)+smp(ix,iy+1,c)*(1-fx)*fy+smp(ix+1,iy+1,c)*fx*fy;
      px8[(y*OUT_W+x)*3+c]=lin2srgb(v);
    }
  }
  // PNG
  const raw=Buffer.alloc((OUT_W*3+1)*OUT_H);
  for(let y=0;y<OUT_H;y++){raw[y*(OUT_W*3+1)]=0;px8.copy(raw,y*(OUT_W*3+1)+1,y*OUT_W*3,(y+1)*OUT_W*3);}
  const crcT=(()=>{const t=new Int32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c;}return t;})();
  const crc=(b:Buffer)=>{let c=-1;for(const v of b)c=crcT[(c^v)&255]^(c>>>8);return (c^-1)>>>0;};
  const chunk=(type:string,data:Buffer)=>{const len=Buffer.alloc(4);len.writeUInt32BE(data.length);
    const td=Buffer.concat([Buffer.from(type),data]);const cr=Buffer.alloc(4);cr.writeUInt32BE(crc(td));return Buffer.concat([len,td,cr]);};
  const ihdr=Buffer.alloc(13);ihdr.writeUInt32BE(OUT_W,0);ihdr.writeUInt32BE(OUT_H,4);ihdr[8]=8;ihdr[9]=2;
  return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk("IHDR",ihdr),
    chunk("IDAT",zlib.deflateSync(raw)),chunk("IEND",Buffer.alloc(0))]);
}

if (require.main === module) {
  const outDir="/tmp/avcs/out"; fs.mkdirSync(outDir,{recursive:true});
  const arg=(k:string,d:number)=>{const m=process.argv.find(a=>a.startsWith(`--${k}=`));return m?parseFloat(m.split("=")[1]):d;};
  const name=process.argv.find(a=>a.startsWith("--name="))?.split("=")[1] ?? "out";
  const png=render({N:arg("n",512*512),dprTier:arg("dpr",2),pointSize:arg("ps",42),
    brightBoost:arg("boost",1),hardness:arg("hard",0),label:name,seedFrac:arg("seed",0.436)});
  fs.writeFileSync(`${outDir}/${name}.png`,png);
  console.log(`${outDir}/${name}.png`);
}
