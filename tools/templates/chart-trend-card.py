import base64,sys
from playwright.sync_api import sync_playwright
W,H,photoH,out=int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
PANEL=len(sys.argv)>5
k=H/850
ph="data:image/jpeg;base64,"+base64.b64encode(open('corsair_rgb.jpg','rb').read()).decode()
# chart geometry inside panel
px,py,pw,phh=36,int(photoH-40*k),W-72,int(H-photoH+20*k)
pts=[("2026",12),("2027",16),("2028",8)]
html=f"""<html><head><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{W}px;height:{H}px;overflow:hidden;position:relative;background:{'transparent' if PANEL else '#0b0820'};font-family:'Inter Display','Inter',sans-serif}}
.ph{{position:absolute;left:0;top:0;width:{W}px;height:{photoH}px;background:#efefef url({ph}) {int((W-W*min(1,photoH/400))/2)}px {int(-372*min(1,photoH/400))}px/{int(W*min(1,photoH/400))}px auto no-repeat;filter:brightness(.9) contrast(1.08)}}
.ph:after{{content:'';position:absolute;inset:0;background:linear-gradient(to bottom,rgba(11,8,32,0) 55%,rgba(11,8,32,.95))}}
.badge{{position:absolute;right:{int(30*k)}px;top:{int(28*k)}px;background:#fff;color:#0b0820;font-weight:900;font-size:{int(44*k)}px;padding:{int(6*k)}px {int(20*k)}px;border-radius:{int(14*k)}px;transform:rotate(3deg);box-shadow:0 8px 24px rgba(0,0,0,.5);letter-spacing:1px}}
.badge b{{color:#e0144a}}
.panel{{position:absolute;left:{px}px;top:{py}px;width:{pw}px;height:{phh}px;border-radius:{int(30*k)}px;border:{max(3,int(5*k))}px solid #ff3d8b;background:linear-gradient(180deg,#1b1650,#120e38);box-shadow:0 0 40px rgba(255,61,139,.45)}}
svg{{position:absolute;left:0;top:0}}
.lab{{position:absolute;color:#fff;font-weight:900;line-height:.95;text-shadow:0 4px 16px rgba(0,0,0,.6)}}
.sub{{font-weight:600;font-size:{int(30*k)}px;color:#d9d6ff;line-height:1.1}}
.src{{position:absolute;left:{px+24}px;top:{py+phh-int(44*k)}px;color:#a9a4d8;font-size:{int(20*k)}px;font-weight:600}}
</style></head><body>{'' if PANEL else '<div class=ph></div><div class=badge>32GB DDR5 <b>KIT</b></div>'}
<div class=panel></div>
<svg width="{W}" height="{H}" id=s></svg>
<div id=labs></div>
<div class=src>Est. using GF Securities DRAM forecast (2028 base case). Today: MemRadar, Nov 27</div>
<script>
const W={W},px={px},py={py},pw={pw},ph={phh},k={k};
const x0=px+90*k, x1=px+pw-90*k, ytop=py+175*k, ybot=py+ph-95*k;
const lo=0, hi=700;
const X=i=>x0+(x1-x0)*i/2, Y=val=>ybot-(ybot-ytop)*(val-lo)/(hi-lo);
const s=document.getElementById('s');
let d=`M${{X(0)}},${{Y(475)}} C${{X(0.5)}},${{Y(615)}} ${{X(0.7)}},${{Y(663)}} ${{X(1)}},${{Y(633)}} C${{X(1.3)}},${{Y(610)}} ${{X(1.6)}},${{Y(375)}} ${{X(2)}},${{Y(317)}}`;
s.innerHTML=`<defs><linearGradient id=g x1=0 x2=1><stop offset=0 stop-color="#ff2d55"/><stop offset=.5 stop-color="#ff2d55"/><stop offset=.75 stop-color="#ffc34d"/><stop offset=1 stop-color="#22e07a"/></linearGradient>
<linearGradient id=f x1=0 y1=0 x2=0 y2=1><stop offset=0 stop-color="#ff3d8b" stop-opacity=.55 /><stop offset=1 stop-color="#ff3d8b" stop-opacity=0 /></linearGradient></defs>
<path d="${{d}} L${{X(2)}},${{ybot}} L${{X(0)}},${{ybot}} Z" fill="url(#f)"/>
<path d="${{d}}" stroke="url(#g)" stroke-width=${{11*k}} fill=none stroke-linecap=round style="filter:drop-shadow(0 0 ${{10*k}}px rgba(255,61,139,.9))"/>
${{[[0,475,'#fff'],[1,633,'#ff2d55'],[2,317,'#22e07a']].map(([i,val,c])=>`<circle cx=${{X(i)}} cy=${{Y(val)}} r="${{20*k}}" fill="${{c}}" stroke="#fff" stroke-width="${{6*k}}"></circle>`).join('')}}
`;
const L=document.getElementById('labs');
L.innerHTML=`<div class=lab style="left:${{X(0)-40*k}}px;top:${{Y(475)-170*k}}px;font-size:${{84*k}}px">$475<div class=sub>today</div></div>
<div class=lab style="left:${{X(1)-150*k}}px;top:${{Y(633)-172*k}}px;font-size:${{124*k}}px;color:#ff4d6a">~$630<div class=sub style="color:#ffd0d8">2027 peak</div></div>
<div class=lab style="left:${{X(2)-330*k}}px;top:${{Y(317)+30*k}}px;font-size:${{124*k}}px;color:#3dff95;text-align:right;width:${{360*k}}px">~$315<div class=sub style="color:#c8ffe0">2028</div></div>`;
</script></body></html>"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={"width":W,"height":H}); pg.set_content(html); pg.wait_for_timeout(300); pg.screenshot(path=out,omit_background=True) if PANEL else pg.screenshot(path=out,type="jpeg",quality=95); b.close()
print(out)
