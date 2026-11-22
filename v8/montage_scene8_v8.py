#!/usr/bin/env python3
"""LE FOOT AU RAPPORT — Scène 8 V8 Premium (Python/OpenCV/Pillow/FFmpeg).

Utilisation :
 python montage_scene8_v8.py --input '/chemin/Scene_08_Pedri_Bellingham_Premium_1080p(1).mp4' \
     --output 'Scene_08_Pedri_Bellingham_V8_Premium_1080p25.mp4'

Données affichées uniquement selon timeline (voix off Descript exportée).
Visuels de trophées et collage final : illustrations fournies par l'utilisateur,
non présentées comme photos de presse. Aucune fausse capture de tweet ni d'interview.
"""
from __future__ import annotations
import argparse, bisect, json, math, subprocess, time, os, wave, base64
from pathlib import Path
from functools import lru_cache
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parent
W,H=1920,1080
OW,OH=960,540
FPS=25
DURATION=72.68
NAVY=(2,21,38)
GREEN=(13,232,104)
LIGHT_GREEN=(149,255,187)
WHITE=(249,253,254)
ICE=(208,231,240)
MUTED=(179,202,216)
DARK=(4,24,39)
SHADOW=(3,13,24)
FONT_BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_REG='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_DISPLAY='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'

def font(px,bold=True):
    p=FONT_DISPLAY if bold else FONT_REG
    return ImageFont.truetype(p,int(px))

def ease(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)

def clamp(x):return max(0.,min(1.,x))

def text(draw, xy, s, px=28, color=WHITE, max_width=None, bold=True, stroke=0):
    while True:
        f=font(px,bold)
        bounds=draw.textbbox((0,0),str(s),font=f)
        if max_width is None or bounds[2]-bounds[0]<=max_width or px<=10: break
        px-=1
    draw.text(xy,str(s),font=f,fill=(*color,255) if len(color)==3 else color,
              stroke_width=stroke,stroke_fill=(2,14,21,160) if stroke else None)
    return bounds[2]-bounds[0]

def circle_alpha_remove_white(image: Image.Image) -> Image.Image:
    # Élimine seulement le blanc extérieur au cercle du logo officiel fourni.
    img=image.convert('RGBA');v=np.asarray(img).copy();height,width=v.shape[:2]
    yy,xx=np.ogrid[:height,:width];cx=(width-1)/2;cy=(height-1)/2
    radius=min(width,height)*.474
    dist=np.sqrt((xx-cx)**2+(yy-cy)**2)
    edge=np.clip((radius+2-dist)/3,0,1)
    v[:,:,3]=np.minimum(v[:,:,3],(edge*255).astype(np.uint8))
    return Image.fromarray(v,'RGBA')

def ensure_assets():
    """Décode les visuels inclus dans GitHub lorsque les PNG/JPG ne sont pas présents."""
    folder=ROOT/'assets'; folder.mkdir(exist_ok=True)
    for name in ('logo_officiel_original.png','trophee_euro.png','trophee_mondial.png','conclusion_visuelle.png'):
        target=folder/name
        encoded=folder/(name+'.b64')
        if not target.is_file() and encoded.is_file():
            target.write_bytes(base64.b64decode(encoded.read_text(encoding='ascii')))
        if not target.is_file():
            raise FileNotFoundError(f'Média requis : {target} (ou {encoded} depuis GitHub)')

@lru_cache(maxsize=1)
def assets():
    ensure_assets()
    a=ROOT/'assets'
    log=circle_alpha_remove_white(Image.open(a/'logo_officiel_original.png')).resize((76,76),Image.Resampling.LANCZOS)
    trophies={}
    for key,name in [('euro','trophee_euro.png'),('world','trophee_mondial.png')]:
        im=Image.open(a/name).convert('RGBA')
        bbox=im.getchannel('A').getbbox()
        im=im.crop(bbox).copy()
        ht=268 if key=='world' else 265
        wd=int(im.width*ht/im.height)
        im=im.resize((wd,ht),Image.Resampling.LANCZOS)
        trophies[key]=im
    im=Image.open(a/'conclusion_visuelle.png').convert('RGB')
    # Remplissage natif 16:9, pas de bandes noires
    im=im.resize((W,H),Image.Resampling.LANCZOS)
    return log,trophies,im

def make_gradient(w=OW,h=OH):
    # Dégradé alpha spatial, sans cartouche/rectangle : 100% image plein écran.
    yy=np.arange(h,dtype=np.float32)[:,None]
    xx=np.arange(w,dtype=np.float32)[None,:]
    lower=np.clip((yy-210)/280,0,1)**1.55
    side=np.clip((w-xx)/450,0,1)**.78
    a=np.minimum(204,lower*215*side+lower*58)
    arr=np.zeros((h,w,4),dtype=np.uint8)
    arr[:,:,:3]=NAVY
    arr[:,:,3]=a.astype(np.uint8)
    return Image.fromarray(arr,'RGBA')

GRAD=make_gradient()

@lru_cache(maxsize=1)
def halo():
    im=Image.new('RGBA',(290,340),(0,0,0,0))
    d=ImageDraw.Draw(im,'RGBA')
    d.ellipse((50,40,235,318),fill=(*GREEN,55))
    return im.filter(ImageFilter.GaussianBlur(32))


def trophy_key(seg):
    return 'world' if 'WORLD CUP' in seg.get('trophy','') or 'MONDIAL 2026' in seg.get('eyebrow','') or 'COUPE DU MONDE' in seg.get('eyebrow','') else 'euro' if seg.get('trophy','') else None


def blend_image(dst:Image.Image,im:Image.Image,xy,alpha=1.0):
    if alpha<=.01:return
    if alpha<.99:
        im=im.copy();im.putalpha(im.getchannel('A').point(lambda v:int(v*alpha)))
    dst.alpha_composite(im,(int(xy[0]),int(xy[1])))


def draw_brand(im):
    d=ImageDraw.Draw(im,'RGBA')
    d.line((35,80,255,80),fill=(*GREEN,165),width=2)
    blend_image(im,assets()[0],(30,14),1)
    text(d,(111,28),'LE FOOT AU RAPPORT',20,WHITE,max_width=277)
    text(d,(113,55),'PEDRI  ×  BELLINGHAM     |     SÉLECTIONS',10,LIGHT_GREEN,max_width=320,bold=False)


def title_lines(seg):
    k=seg['kind'];t=seg['title']
    if k=='passing':return [('65', ' / 66'), ('PASSES RÉUSSIES', '')]
    if k=='counters':return [('7', ' BUTS   +   1 PASSE DÉCISIVE'), ('COUPE DU MONDE 2026','')]
    if k=='rank':return [('3e', ' MEILLEUR BUTEUR'), ('DU MONDIAL 2026','')]
    return [(t,'')]


def base_overlay(seg):
    im=GRAD.copy();draw_brand(im)
    d=ImageDraw.Draw(im,'RGBA')
    d.line((56,326,145,326),fill=(*GREEN,250),width=3)
    text(d,(57,295),seg['eyebrow'],17,LIGHT_GREEN,max_width=830)
    title=seg['title']
    y=342
    if seg['kind']=='counters':
        text(d,(57,y),'L’INCROYABLE BILAN DE JUDE',36,WHITE,max_width=660)
        text(d,(60,480),'STATISTIQUES OFFICIELLES FIFA',13,LIGHT_GREEN,max_width=670,bold=False)
    elif seg['kind']=='passing':
        text(d,(57,y),'65/66 PASSES',49,WHITE,max_width=700)
        text(d,(61,414),'98,5 % de précision contre l’Italie',21,ICE,max_width=720,bold=False)
    elif seg['kind']=='chart':
        text(d,(57,y),'7 BUTS AU MONDIAL',45,WHITE,max_width=680)
        text(d,(58,420),'Un rendement offensif exceptionnel pour un milieu',18,ICE,max_width=715,bold=False)
    elif seg['kind']=='comparison':
        text(d,(57,y),'TITRES OU INFLUENCE ?',43,WHITE,max_width=715)
        text(d,(59,420),'Deux trajectoires, une même génération',19,ICE,max_width=680,bold=False)
    else:
        fsize=44 if len(title)<30 else 37 if len(title)<42 else 33
        text(d,(57,y),title,fsize,WHITE,max_width=750)
        text(d,(58,418),seg['subtitle'],20,ICE,max_width=765,bold=False)
    # Bas de plan — petite ligne déportée, pas d'encadré.
    if seg['kind']!='counters':
        d.line((58,492,185,492),fill=(*GREEN,215),width=2)
        if seg.get('trophy'):
            text(d,(60,501),'UEFA EURO' if trophy_key(seg)=='euro' else 'COUPE DU MONDE FIFA',11,MUTED,bold=False)
    return im

@lru_cache(maxsize=64)
def cached_overlay(i):
    return base_overlay(SCENES[i])


def trophy_layer(im,seg,t,local,alpha):
    key=trophy_key(seg)
    if key is None:return
    if seg['kind'] in ('passing','chart'):
        # Sur les plans riches en statistiques, on réduit le trophée.
        height_ratio=.74
    else:height_ratio=1
    trophy=assets()[1][key]
    if height_ratio!=1:
        trophy=trophy.resize((int(trophy.width*height_ratio),int(trophy.height*height_ratio)),Image.Resampling.LANCZOS)
    x=OW-trophy.width-57
    # Le trophée est placé AU-DESSUS du bandeau narratif, jamais sur les lettres.
    y=int(49+5*math.sin(2*math.pi*.17*t))
    if seg['kind'] in ('counters','chart'):y=46
    h=halo()
    blend_image(im,h,(x-(290-trophy.width)//2,y-45),alpha*.5)
    blend_image(im,trophy,(x,y),alpha*.9)


def draw_dynamic(im,seg,t,local,alpha):
    d=ImageDraw.Draw(im,'RGBA');kind=seg['kind'];p=ease(local/.9)
    if kind=='passing':
        # Anneau de précision animé + arcs de passes graphiques libres.
        cx,cy=778,391;r=68
        d.arc((cx-r,cy-r,cx+r,cy+r),-90,-90+int(360*(65/66)*p),fill=(*GREEN,255),width=11)
        d.arc((cx-r+12,cy-r+12,cx+r-12,cy+r-12),-90,270,fill=(*ICE,100),width=2)
        text(d,(cx-42,cy-31),f'{int(98.5*p):d}%',35,WHITE,max_width=90)
        for idx in range(5):
            x1=580+idx*35; y1=463-idx*17
            d.line((x1,y1,x1+22,y1-9),fill=(*GREEN,int(120+100*math.sin(t*3+idx)**2)),width=3)
            d.ellipse((x1+19,y1-12,x1+25,y1-6),fill=(*LIGHT_GREEN,235))
    elif kind=='counters':
        # Chiffres sans encadrés : typographie cinétique + traits radiaux.
        text(d,(62,395),str(int(round(7*p))),72,LIGHT_GREEN)
        text(d,(162,418),'BUTS',29,WHITE)
        text(d,(334,403),'+',48,WHITE)
        text(d,(420,395),str(int(round(1*p))),72,LIGHT_GREEN)
        text(d,(507,418),'PASSE DÉCISIVE',24,WHITE,max_width=278)
        for i in range(12):
            angle=2*math.pi*i/12+t*0.65
            x=790+80*math.cos(angle);y=433+47*math.sin(angle)
            d.ellipse((x,y,x+4,y+4),fill=(*GREEN,int(95+135*p)))
    elif kind=='rank':
        for i in range(3):
            r=25+i*20
            d.arc((773-r,367-r,773+r,367+r),20,int(20+320*p),fill=(*GREEN,210-i*40),width=4)
        text(d,(747,347),'3e',34,WHITE)
    elif kind=='chart':
        data=[('MBAPPÉ',10),('MESSI',8),('BELLINGHAM',7),('HAALAND',7)]
        for i,(name,v) in enumerate(data):
            x=565+i*84; bottom=470;top=bottom-int(v*8.2*p)
            drawcol=LIGHT_GREEN if name=='BELLINGHAM' else (151,175,183)
            d.rounded_rectangle((x,bottom-(v*8.2*p),x+38,bottom),radius=8,fill=(*drawcol,225))
            text(d,(x+5,top-26),str(int(v*p)),20,WHITE)
            text(d,(x-2,480),name,10,WHITE if name=='BELLINGHAM' else MUTED,max_width=75)
    elif kind in ('result','scoreboard'):
        score=seg.get('score')
        if score:
            # Score surgissant du côté haut droit sans grand panneau.
            d.line((680,252,855,252),fill=(*GREEN,175),width=2)
            text(d,(688,258),score,30,LIGHT_GREEN,max_width=220)
    elif kind in ('award',):
        # halo d'un trophée + trois éclats football.
        for i in range(3):
            x=665+i*19;y=370-i*13
            d.ellipse((x,y,x+6,y+6),fill=(*GREEN,int(70+140*p)))
    elif kind=='interview':
        q=seg.get('quote','')
        if q:
            text(d,(63,466),'« '+q+' »',20,LIGHT_GREEN,max_width=695)
            text(d,(65,508),'RFEF · traduction française',11,MUTED,bold=False)
    elif kind=='quote':
        q=seg.get('quote','')
        if q:
            text(d,(62,466),'« '+q+' »',21,LIGHT_GREEN,max_width=720)
            text(d,(64,509),seg.get('by',''),11,MUTED,max_width=700,bold=False)
    elif kind=='press':
        d.line((58,458,58,517),fill=(*GREEN,230),width=3)
        text(d,(70,458),seg.get('press','SOURCE SPORTIVE'),14,LIGHT_GREEN,max_width=700)
        text(d,(70,487),seg.get('headline',''),16,WHITE,max_width=690)
    elif kind=='comparison':
        text(d,(60,467),'PEDRI   2 GRANDS TITRES',22,LIGHT_GREEN,max_width=380)
        text(d,(451,467),'JUDE   7 BUTS · 1 PASSE D.',21,WHITE,max_width=455)
    elif kind=='outro':
        pass
    return im


def create_overlay(seg_index,t):
    seg=SCENES[seg_index];local=t-seg['start'];dur=seg['end']-seg['start']
    alpha=ease(local/.42)*ease((dur-local)/.3)
    img=cached_overlay(seg_index).copy()
    trophy_layer(img,seg,t,local,alpha)
    draw_dynamic(img,seg,t,local,alpha)
    # reflets / impulsions électriques verts, originaux et discrets
    d=ImageDraw.Draw(img,'RGBA')
    x=140+int(((t*135)%700))
    d.line((x,320,x+62,320),fill=(*GREEN,int(60+85*math.sin(t*2)**2)),width=2)
    if alpha<.995:
        a=np.array(img)
        a[:,:,3]=(a[:,:,3].astype(np.float32)*alpha).astype(np.uint8)
        img=Image.fromarray(a,'RGBA')
    return img


def read_source_images(cap):
    src={}
    for name,time_pos in [('pedri_selection',41.0),('england_interview',33.2),('spain_euro',37.4),('stadium',13.3),('jude_world',56.2)]:
        cap.set(cv2.CAP_PROP_POS_MSEC,time_pos*1000)
        ok,img=cap.read()
        if ok:src[name]=img
    cap.set(cv2.CAP_PROP_POS_FRAMES,0)
    return src

def source_background(t,frame,src):
    key=None
    if 7.75<=t<11.78:key='pedri_selection'
    elif 18.39<=t<22.81:key='england_interview'
    elif 22.81<=t<26.9:key='spain_euro'
    elif 35.9<=t<43.7:key='stadium'
    elif 58.21<=t<63.39:key='jude_world'
    if not key or key not in src:return frame
    base=src[key]
    # zoom doux ≠ changement de photos faux évènements
    u=(t%4.9)/4.9;scale=1.019+.015*u
    ww=int(W/scale);hh=int(H/scale)
    x=int((W-ww)*(.25+.35*u));y=int((H-hh)*(.28+.3*u))
    return cv2.resize(base[y:y+hh,x:x+ww],(W,H),interpolation=cv2.INTER_LINEAR)


def endcard(t):
    """Le visuel récapitulatif fourni n'apparaît qu'après que les chiffres sont cités."""
    original=assets()[2]
    pct=clamp((t-68.31)/(72.68-68.31))
    zoom=1.012+0.014*pct
    ww=int(W/zoom);hh=int(H/zoom)
    x0=int((W-ww)*(.50-.15*pct));y0=int((H-hh)*(.55+.1*pct))
    view=original.crop((x0,y0,x0+ww,y0+hh))
    # Le logo authentique de l'utilisateur couvre le logo approximatif de l'illustration.
    canvas=view.resize((W,H),Image.Resampling.BILINEAR).convert('RGBA')
    log=assets()[0].resize((226,226),Image.Resampling.LANCZOS)
    canvas.alpha_composite(log,(W//2-113,9))
    return cv2.cvtColor(np.array(canvas.convert('RGB')),cv2.COLOR_RGB2BGR)


def alpha_blend(bg,overlay):
    lay=np.asarray(overlay)
    lay=cv2.cvtColor(lay,cv2.COLOR_RGBA2BGRA)
    lay=cv2.resize(lay,(W,H),interpolation=cv2.INTER_LINEAR)
    alpha=lay[:,:,3:4].astype(np.float32)/255.
    # OpenCV: éviter les écrasements de niveaux avec multiplication float32.
    return (bg.astype(np.float32)*(1-alpha)+lay[:,:,:3].astype(np.float32)*alpha).astype(np.uint8)


def make_audio_bed(path,duration):
    rate=16000;n=int(rate*duration);rng=np.random.default_rng(47)
    noise=rng.normal(0,1,n).astype(np.float32)
    noise=cv2.GaussianBlur(noise.reshape(1,-1),(0,0),4).ravel()
    noise=noise/max(1e-8,np.std(noise))
    t=np.arange(n)/rate
    # ambiance de stade synthétique originale, très discrète ; dynamique aux événements
    crowd=(.0055+.0025*np.sin(2*np.pi*.05*t))*noise
    for marker in (4.75,11.78,18.39,22.81,35.9,43.70,48.62,54.79,63.39,68.31):
        k=int(marker*rate);leng=min(int(.34*rate),n-k)
        if leng>0:
            z=np.arange(leng)/rate
            crowd[k:k+leng]+=.007*np.sin((200+300*z)*z*2*np.pi)*np.exp(-15*z)
    sound=(np.clip(crowd,-1,1)*32767).astype('<i2')
    with wave.open(str(path),'wb') as wav:
        wav.setsampwidth(2);wav.setnchannels(1);wav.setframerate(rate);wav.writeframes(sound.tobytes())


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height,r_frame_rate','-of','json',str(path)]))


def render(src_path:Path,out_path:Path,limit:float|None=None):
    global SCENES,ENDS
    SCENES=json.loads((ROOT/'scene8_timeline.json').read_text(encoding='utf-8'))
    ENDS=[s['end'] for s in SCENES]
    assert len(SCENES)==19 and abs(ENDS[-1]-DURATION)<.02
    meta=probe(src_path)
    if not any(s.get('codec_type')=='audio' for s in meta['streams']):raise RuntimeError('Pas de piste audio source')
    if not any(s.get('width')==W and s.get('height')==H for s in meta['streams']):raise RuntimeError('Source 1920x1080 requise')
    length=min(DURATION,limit or DURATION)
    out_path.parent.mkdir(parents=True,exist_ok=True)
    bed=ROOT/'exports'/'ambiance_football_originale.wav'
    make_audio_bed(bed,length)
    cv2.setNumThreads(2)
    cap=cv2.VideoCapture(str(src_path))
    if not cap.isOpened():raise RuntimeError('Échec lecture vidéo source')
    sources=read_source_images(cap)
    cmd=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
         '-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0',
         '-i',str(src_path),'-i',str(bed),'-filter_complex',
         '[1:a]aresample=48000,volume=1.0[vo];[2:a]aresample=48000,volume=0.8[amb];[vo][amb]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]',
         '-map','0:v','-map','[a]','-t',str(length),'-c:v','libx264','-preset','veryfast','-crf','18',
         '-pix_fmt','yuv420p','-r',str(FPS),'-threads','4','-c:a','aac','-b:a','192k',
         '-movflags','+faststart',str(out_path)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    count=int(math.ceil(length*FPS));frames=0
    try:
        for k in range(count):
            t=k/FPS;ok,bgr=cap.read()
            if not ok:break
            if t>=68.31:
                bgr=endcard(t)
            else:
                bgr=source_background(t,bgr,sources)
                idx=min(len(SCENES)-1,bisect.bisect_right(ENDS,t))
                overlay=create_overlay(idx,t)
                bgr=alpha_blend(bgr,overlay)
            proc.stdin.write(bgr.tobytes());frames+=1
            if k%125==0:
                print(f'{t:05.2f}s / {length:.2f}s — plan {min(19,bisect.bisect_right(ENDS,t)+1)}/19',flush=True)
    finally:
        cap.release()
        if proc.stdin:proc.stdin.close()
    err=proc.stderr.read().decode('utf8','replace');ret=proc.wait()
    if ret!=0:raise RuntimeError('FFmpeg '+err[:2500])
    result=probe(out_path)
    output_length=float(result['format']['duration'])
    if abs(output_length-length)>.3:raise RuntimeError(f'Durée invalide {output_length} au lieu de {length}')
    print('EXPORT OK',out_path,'durée',output_length,'frames',frames,'size',out_path.stat().st_size,flush=True)
    return out_path

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'exports'/'Scene_08_Pedri_Bellingham_V8_Premium_1080p25.mp4')
    p.add_argument('--limit',type=float,default=None)
    a=p.parse_args();render(a.input,a.output,a.limit)