const zlib=require("zlib"), fs=require("fs");
function readPNG(p){const b=fs.readFileSync(p);let o=8,w=0,h=0,idat=[];
  while(o<b.length){const len=b.readUInt32BE(o),type=b.toString("ascii",o+4,o+8);
    if(type==="IHDR"){w=b.readUInt32BE(o+8);h=b.readUInt32BE(o+12);}
    if(type==="IDAT")idat.push(b.subarray(o+8,o+8+len));
    o+=12+len;}
  const raw=zlib.inflateSync(Buffer.concat(idat));const px=Buffer.alloc(w*h*3);
  for(let y=0;y<h;y++)raw.copy(px,y*w*3,y*(w*3+1)+1,(y+1)*(w*3+1));return{w,h,px};}
function writePNG(p,w,h,px){const raw=Buffer.alloc((w*3+1)*h);
  for(let y=0;y<h;y++){raw[y*(w*3+1)]=0;px.copy(raw,y*(w*3+1)+1,y*w*3,(y+1)*w*3);}
  const T=(()=>{const t=new Int32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c;}return t;})();
  const crc=b=>{let c=-1;for(const v of b)c=T[(c^v)&255]^(c>>>8);return(c^-1)>>>0;};
  const ch=(t,d)=>{const l=Buffer.alloc(4);l.writeUInt32BE(d.length);const td=Buffer.concat([Buffer.from(t),d]);
    const c=Buffer.alloc(4);c.writeUInt32BE(crc(td));return Buffer.concat([l,td,c]);};
  const ih=Buffer.alloc(13);ih.writeUInt32BE(w,0);ih.writeUInt32BE(h,4);ih[8]=8;ih[9]=2;
  fs.writeFileSync(p,Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),ch("IHDR",ih),ch("IDAT",zlib.deflateSync(raw)),ch("IEND",Buffer.alloc(0))]));}
// franja: ANTES | DESPUÉS | Q4
const imgs=["out/B_Q1_actual.png","out/V_Q1.png","out/V_Q4.png"].map(readPNG);
const S=600, GAP=8, W=S*3+GAP*2, H=S;
const out=Buffer.alloc(W*H*3);
imgs.forEach((im,i)=>{const ox=i*(S+GAP);
  for(let y=0;y<S;y++)for(let x=0;x<S;x++){
    const sx=Math.floor(x*im.w/S), sy=Math.floor(y*im.h/S);
    for(let c=0;c<3;c++) out[((y)*W+(ox+x))*3+c]=im.px[(sy*im.w+sx)*3+c];}});
writePNG("out/COMPARATIVA.png",W,H,out);
console.log("out/COMPARATIVA.png  (izq: Q1 ANTES | centro: Q1 AHORA | dcha: Q4 referencia)");
