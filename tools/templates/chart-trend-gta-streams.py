import base64,sys,json
from playwright.sync_api import sync_playwright
def uri(f,m='image/jpeg'): return f"data:{m};base64,"+base64.b64encode(open(f,'rb').read()).decode()
art=uri('src/og4.jpg')
def hero(W,H,heroH,out):
    # og4 1600x436 -> scale to heroH height, center on characters (x~720/1600)
    sc=heroH/436; w=int(1600*sc); cx=int(720*sc); left=W//2-cx
    html=f"""<html><body style="margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#0b0820;position:relative">
<div style="position:absolute;left:{left}px;top:0;width:{w}px;height:{heroH}px;background:url({art}) 0 0/{w}px {heroH}px"></div>
<div style="position:absolute;left:0;right:0;top:{heroH-140}px;height:141px;background:linear-gradient(to bottom,rgba(11,8,32,0),#0b0820)"></div>
</body></html>"""
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={"width":W,"height":H}); pg.set_content(html); pg.wait_for_timeout(300); pg.screenshot(path=out,type='jpeg',quality=95); b.close()
def panel(W,Hp,out):
    k=W/1000
    pts=[(0,7.1),(1,4.84),(2,3.54),(3,2.62),(9,0.863)]
    html=f"""<html><head><style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{Hp}px;background:transparent;font-family:'Inter Display','Inter',sans-serif;position:relative;overflow:hidden}}
.panel{{position:absolute;left:10px;top:10px;right:10px;bottom:10px;border-radius:{int(30*k)}px;border:{int(5*k)}px solid #ff3d8b;background:linear-gradient(180deg,#1b1650,#120e38);box-shadow:0 0 30px rgba(255,61,139,.5)}}
.lab{{position:absolute;color:#fff;font-weight:900;line-height:.92;text-shadow:0 4px 16px rgba(0,0,0,.6)}}
.sub{{font-weight:600;font-size:{int(30*k)}px;color:#d9d6ff;line-height:1.15}}
.chip{{position:absolute;right:{int(36*k)}px;top:{int(34*k)}px;background:rgba(255,255,255,.1);border:2px solid rgba(255,255,255,.25);border-radius:{int(14*k)}px;padding:{int(8*k)}px {int(16*k)}px;color:#fff;font-weight:800;font-size:{int(27*k)}px;text-align:right;line-height:1.2}}
.chip b{{color:#3dff95}}
.src{{position:absolute;left:{int(36*k)}px;bottom:{int(26*k)}px;color:#a9a4d8;font-size:{int(19*k)}px;font-weight:600}}
</style></head><body><div class=panel></div><svg id=s width={W} height={Hp} style="position:absolute;left:0;top:0"></svg>
<div class=chip>Channels streaming it<br>27K &rarr; <b>48K</b></div>
<div id=L></div><div class=src>Daily peak viewers across Twitch, YouTube, Kick and more. Source: GatorStreams via VGTimes</div>
<script>
const W={W},H={Hp},k={k};
const x0=90*k,x1=W-110*k,ytop=150*k,ybot=H-90*k,lo=0,hi=7.6,days=9;
const X=d=>x0+(x1-x0)*d/days, Y=v=>ybot-(ybot-ytop)*(v-lo)/(hi-lo);
const P={json.dumps(pts)};
let d=`M${{X(P[0][0])}},${{Y(P[0][1])}}`;
for(let i=1;i<P.length;i++){{const [a,b]=P[i-1],[c,e]=P[i];const m=(X(a)+X(c))/2;d+=` C${{m}},${{Y(b)}} ${{m}},${{Y(e)}} ${{X(c)}},${{Y(e)}}`}}
document.getElementById('s').innerHTML=`<defs><linearGradient id=g x1=0 x2=1><stop offset=0 stop-color="#ff3d8b"/><stop offset=1 stop-color="#8f6bff"/></linearGradient>
<linearGradient id=f x1=0 y1=0 x2=0 y2=1><stop offset=0 stop-color="#ff3d8b" stop-opacity=".6"/><stop offset=1 stop-color="#ff3d8b" stop-opacity="0"/></linearGradient></defs>
<path d="${{d}} L${{X(9)}},${{ybot}} L${{X(0)}},${{ybot}} Z" fill="url(#f)"/>
<path d="${{d}}" stroke="url(#g)" stroke-width="${{10*k}}" fill="none" stroke-linecap="round" style="filter:drop-shadow(0 0 ${{10*k}}px rgba(255,61,139,.9))"/>
${{P.map(([a,b],i)=>`<circle cx="${{X(a)}}" cy="${{Y(b)}}" r="${{(i==0||i==P.length-1?20:12)*k}}" fill="#fff" stroke="#ff3d8b" stroke-width="${{6*k}}"></circle>`).join('')}}`;
document.getElementById('L').innerHTML=`<div class=lab style="left:${{X(0)+45*k}}px;top:${{22*k}}px;font-size:${{120*k}}px">7.1M<div class=sub>peak viewers, Nov 18</div></div>
<div class=lab style="left:${{X(9)-300*k}}px;top:${{Y(0.863)-200*k}}px;font-size:${{120*k}}px;color:#ff6f9e;text-align:right;width:${{330*k}}px">863K<div class=sub style="color:#ffd0de">Nov 27 <span style="background:#ff2d55;color:#fff;border-radius:8px;padding:0 10px;font-weight:900">&minus;88%</span></div></div>`;
</script></body></html>"""
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={"width":W,"height":Hp}); pg.set_content(html); pg.wait_for_timeout(300); pg.screenshot(path=out,omit_background=True); b.close()
if __name__=="__main__":
    hero(1080,918,560,'hero-fb.jpg'); panel(1000,460,'panel-fb.png')
