#!/usr/bin/env python3
"""Réalise la scène 8 d'une vidéo football avec incrustations animées.

Sources vidéo et audio : MP4 que l'utilisateur fournit. Pas de fausse
capture de tweet, une imprimée ou séquence d'interview : seules des citations
attribuées et des titres web vérifiés sont reproduits dans une mise en page originale.

Exemple : python montage_scene8.py --input "Scene_08_Pedri_Bellingham_Premium_1080p(1).mp4"
"""
from __future__ import annotations
import argparse, bisect, json, math, os, shutil, subprocess, sys, wave
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
DEFAULT_TIMELINE=ROOT/'scene8_timeline.json'
W,H=1920,1080
S=2  # Toutes les compositions sont dessinées à moitié résolution puis mises à l'échelle
w,h=W//S,H//S
FPS=25
DURATION=72.68
BG=(10,12,21)
WHITE=(247,248,252); SOFT=(194,203,220); GOLD=(255,206,105); CYAN=(111,214,255); RED=(255,71,83)
INTER='/usr/share/fonts/opentype/inter/Inter-Bold.otf'
REG='/usr/share/fonts/opentype/inter/Inter-Regular.otf'
DISPLAY='/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
FONTS=[INTER,REG,DISPLAY]

def font(size, bold=True):
    p = DISPLAY if bold else REG
    if not os.path.isfile(p):
        p= '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(p,max(8,int(size)))

def color(seg):
    return {'spain':GOLD,'england':CYAN,'neutral':(245,207,147)}[seg.get('accent','neutral')]

def clamp(x,lo=0,hi=1):return max(lo,min(hi,x))
def ease(x):x=clamp(x);return 1-(1-x)**3

def draw_fit(d,xy,text,size=38,color=WHITE,limit=790,bold=True):
    f=font(size,bold)
    while d.textbbox((0,0),text,font=f)[2]>limit and size>11:
        size-=2;f=font(size,bold)
    d.text(xy,text,font=f,fill=color,stroke_width=0)

def transparent():return Image.new('RGBA',(w,h),(0,0,0,0))

def rounded(d,rect,r=16,fill=(8,12,22,216),outline=None,width=1):
    d.rounded_rectangle(rect,radius=r,fill=fill,outline=outline,width=width)

def draw_trophy(d,x,y,scale=1,fill=GOLD):
    """Pictogramme ORIGiNAL de coupe, non présenté comme un logo officiel."""
    def p(a,b):return (int(x+a*scale),int(y+b*scale))
    d.ellipse((*p(11,2),*p(44,12)),fill=fill)
    d.polygon([p(10,11),p(47,11),p(43,31),p(35,43),p(22,43),p(14,31)], fill=fill)
    d.arc((*p(0,11),*p(22,38)),60,300,fill=fill,width=max(2,int(4*scale)))
    d.arc((*p(35,11),*p(57,38)),245,120,fill=fill,width=max(2,int(4*scale)))
    d.rectangle((*p(25,40),*p(32,53)),fill=fill)
    d.rounded_rectangle((*p(14,53),*p(44,58)),radius=2,fill=fill)
    d.line([p(17,8),p(38,8)],fill=(255,250,215),width=max(1,int(scale)))

def draw_crest(d,x,y,mode='spain'):
    # Petit badge graphique original d'identification pays, pas un blason officiel
    c=(249,183,58) if mode=='spain' else (142,216,251)
    d.ellipse((x,y,x+32,y+32),fill=(12,17,27,238),outline=(*c,255),width=2)
    if mode=='spain':
        d.rectangle((x+6,y+9,x+26,y+23),fill=(220,35,44))
        d.rectangle((x+6,y+13,x+26,y+19),fill=(250,218,42))
    else:
        d.ellipse((x+8,y+8,x+24,y+24),outline=(243,243,249),width=2)
        d.line((x+8,y+16,x+24,y+16),fill=(246,246,251),width=2)

def card_base(seg):
    a=transparent();d=ImageDraw.Draw(a)
    # Dégradé spatial pour fondre les inscriptions DANS l'image, aucun cadre PPT
    gradient=np.zeros((h,w,4),dtype=np.uint8)
    y=np.arange(h,dtype=float)[:,None]
    x=np.arange(w,dtype=float)[None,:]
    vertical=np.clip((y-260)/230,0,1)**0.8
    horizontal=np.clip((960-x)/250,0,1)**0.65
    alpha=np.uint8(np.minimum(185,183*vertical*horizontal))
    gradient[:,:,0]=8; gradient[:,:,1]=12; gradient[:,:,2]=21
    gradient[:,:,3]=alpha
    a.alpha_composite(Image.fromarray(gradient,'RGBA'))
    d=ImageDraw.Draw(a)
    ac=color(seg)
    d.line((57,314,668,314),fill=(*ac,130),width=2)
    d.rounded_rectangle((56,334,61,478),radius=2,fill=(*ac,235))
    draw_fit(d,(75,284),seg['eyebrow'],17,ac,limit=770)
    title=seg['title'];special=seg['kind']
    ts=42 if len(title)<36 else 34
    if special in ('counters','chart','comparison'):ts=37
    if special=='outro':ts=48
    draw_fit(d,(75,343),title,ts,WHITE,limit=740)
    draw_fit(d,(75,415),seg['subtitle'],20,SOFT,limit=775,bold=False)
    if seg.get('trophy'):
        rounded(d,(674,454,910,506),12,(15,22,34,210),outline=(*ac,170),width=2)
        draw_trophy(d,684,458,.72,GOLD)
        draw_fit(d,(742,475),seg['trophy'],13,GOLD,limit=158)
    if special in ('passing','chart'):
        d.ellipse((780,368,869,457),outline=(*ac,85),width=2)
    d.rounded_rectangle((76,501,604,503),radius=1,fill=(90,100,120,130))
    return a

def draw_extra(seg,t,local,base):
    d=ImageDraw.Draw(base)
    ac=color(seg);typ=seg['kind']
    # badges animés à droite du panneau, selon les besoins de narration
    if typ=='award':
        draw_trophy(d,775,336,1.15,GOLD)
        d.ellipse((785,365,832,412),outline=(255,238,179),width=2)
    elif typ=='passing':
        p=ease(local/.85); cx,cy=824,407
        d.arc((cx-57,cy-57,cx+57,cy+57),-90,-90+int(360*(65/66)*p),fill=ac,width=9)
        draw_fit(d,(789,389),f'{int(65*p)}',39,WHITE,limit=75)
        draw_fit(d,(813,427),'/ 66',14,SOFT,limit=60)
        draw_fit(d,(76,468),'629 MIN     92,3 % PASSES     76,1 KM',17,ac,limit=555)
    elif typ=='scoreboard':
        # impact visuel au moment du score
        p=ease(local/.65)
        d.line([(695,407),(695+int(134*p),407)],fill=ac,width=5)
        draw_fit(d,(76,468),'RÉSULTAT OFFICIEL',15,ac,limit=380)
    elif typ=='interview':
        # extrait authentique en incrustation, pas une fausse vidéo d'interview
        rounded(d,(76,447,623,493),12,(37,44,62,241))
        draw_fit(d,(89,455),f'« {seg["quote"]} »',21,WHITE,limit=515)
        draw_fit(d,(77,510),seg['by'],10,SOFT,limit=570)
    elif typ=='quote':
        rounded(d,(75,455,665,500),10,(28,38,56,225))
        draw_fit(d,(87,465),f'« {seg["quote"]} »',21,WHITE,limit=545)
    elif typ=='press':
        # Encart de presse = TITRE WEB réel, jamais une fausse une de journal
        rounded(d,(76,456,658,507),11,(21,27,38,226),outline=(*ac,130))
        draw_fit(d,(90,459),seg['press']+' · TITRE WEB',12,GOLD,limit=540)
        draw_fit(d,(90,480),seg['headline'],16,WHITE,limit=540)
    elif typ=='rank':
        p=ease(local/.8)
        draw_fit(d,(77,466),f'{max(0,min(3,int(round(3*p)))):d}e AU CLASSEMENT FIFA',21,GOLD,limit=505)
    elif typ=='counters':
        p=ease(local/1.05)
        a=int(round(seg['goals']*p));b=int(round(seg['assists']*p))
        rounded(d,(75,450,232,499),12,(35,50,65,240))
        rounded(d,(241,450,448,499),12,(35,50,65,240))
        draw_fit(d,(89,457),f'{a}  BUTS',28,ac,limit=132)
        draw_fit(d,(258,461),f'{b}  PASSE D.',24,WHITE,limit=177)
        d.rounded_rectangle((460,466,600,479),radius=5,fill=(55,65,78))
        d.rounded_rectangle((460,466,460+int(140*p),479),radius=5,fill=ac)
    elif typ=='chart':
        # bar chart horizontal animé, intégré à l'image, pas une diapositive
        entries=[('MBAPPÉ',10,GOLD),('MESSI',8,SOFT),('BELLINGHAM',7,CYAN),('HAALAND',7,SOFT)]
        p=ease(local/1.4)
        for i,(name,val,c) in enumerate(entries):
            x0=78+ i*191
            draw_fit(d,(x0,451),name,12,c,limit=170)
            d.rounded_rectangle((x0,474,x0+145,485),radius=4,fill=(52,57,72))
            d.rounded_rectangle((x0,474,x0+int(145*val/10*p),485),radius=4,fill=c)
            draw_fit(d,(x0+153,468),str(val),17,WHITE,limit=33)
    elif typ=='comparison':
        draw_fit(d,(76,469),'PALMARÈS · PEDRI',17,GOLD,limit=350)
        draw_fit(d,(440,469),'BUTS AU MONDIAL · JUDE',17,CYAN,limit=350)
    # Barrette du plan s'anime continuellement
    d.rounded_rectangle((76,501,76+int(528*clamp(local/max(.1,seg['end']-seg['start']))),503),radius=1,fill=ac)

def draw_hud(frame,t,seg):
    # HUD transparent en coin haut, style retransmission sportive
    d=ImageDraw.Draw(frame)
    ac=color(seg)
    rounded(d,(30,24,321,73),12,(12,17,30,210),outline=(*ac,140))
    draw_crest(d,40,32,seg.get('accent') if seg.get('accent') in ['spain','england'] else 'spain')
    draw_fit(d,(83,32),'LE FOOT AU RAPPORT',19,WHITE,limit=226)
    draw_fit(d,(84,56),'DÉCRYPTAGE INTERNATIONAL',9,ac,limit=220)
    rounded(d,(735,26,928,67),12,(12,17,30,204),outline=(*ac,124))
    draw_fit(d,(748,36),'PEDRI  ×  BELLINGHAM',14,WHITE,limit=165)
    # Vignette X: transcription de post authentique, présentation graphique originale
    if seg.get('tweet') and seg['kind']=='press' and 31.18<=t<35.90:
        rounded(d,(593,118,921,228),14,(18,24,39,224),outline=(131,205,250,145),width=1)
        draw_fit(d,(610,131),'X  ·  POST AUTHENTIQUE',15,(137,211,251),limit=270)
        draw_fit(d,(610,161),'@England  ·  30 juin 2024',13,SOFT,limit=285,bold=False)
        draw_fit(d,(611,183),'« Unbelievable. »',24,WHITE,limit=282)
        draw_fit(d,(612,212),'Source : England Football',10,SOFT,limit=270,bold=False)
    if seg['kind']=='comparison' and 63.39<=t<68.31:
        rounded(d,(585,121,920,222),13,(18,24,39,217),outline=(240,200,102,118))
        draw_fit(d,(601,133),'X  ·  @SEFutbol · 7 août 2025',14,GOLD,limit=300)
        draw_fit(d,(601,163),'« El último pase suele llevar',17,WHITE,limit=305)
        draw_fit(d,(601,184),'su firma. »  ·  Pedri',17,WHITE,limit=305)
        draw_fit(d,(601,208),'Source : RFEF',10,SOFT,limit=290,bold=False)
    # ligne de contrôle football télé: minute exacte du montage, non un faux temps de match
    draw_fit(d,(34,86),f'{int(t//60):02d}:{int(t%60):02d}  /  01:12',13,SOFT,limit=150)

def make_overlay(seg,t):
    local=t-seg['start'];dur=seg['end']-seg['start']
    layer=card_base_cached(seg['start']).copy();draw_extra(seg,t,local,layer)
    # Mouvement organique : entrée courte et sortie fine
    alp=ease(local/.40)*ease((dur-local)/.32)
    dx=int(32*(1-ease(local/.52)))
    dy=int(22*(1-ease(local/.55)))
    if dx or dy:
        layer=layer.transform((w,h),Image.Transform.AFFINE,(1,0,-dx,0,1,-dy),resample=Image.Resampling.BILINEAR)
    arr=np.array(layer,dtype=np.uint8)
    arr[:,:,3]=(arr[:,:,3].astype(np.float32)*alp).astype(np.uint8)
    hud=transparent();draw_hud(hud,t,seg)
    hadd=np.array(hud)
    return arr,hadd

@lru_cache(maxsize=64)
def card_base_cached(start):
    return card_base(SEG_BY_START[start])

def blend_native(frame,bg):
    # bg = image BGRA dimensions 960x540, agrandie en haute qualité
    lay=cv2.resize(bg,(W,H),interpolation=cv2.INTER_LINEAR)
    a=lay[:,:,3:4].astype(np.float32)/255.0
    np.multiply(frame,1-a,out=frame,casting='unsafe')
    frame[:,:,:]+= (lay[:,:,:3].astype(np.float32)*a).astype(np.uint8)
    return frame

def bed_audio(path,duration,seed=9):
    """Ambiance originale synthétique, discrète et sans extrait protégé."""
    sample=16000;N=int(sample*duration)
    rng=np.random.default_rng(seed)
    # Bruit rose adouci -> impression de stade / foule, mais -35 dB environ
    z=rng.standard_normal(N).astype('float32')
    z=cv2.GaussianBlur(z.reshape(1,-1),(0,0),3.2).ravel()
    z/=max(1e-6,float(np.std(z)))
    step=np.arange(N,dtype=np.float32)/sample
    amp=.008*(.66+.25*np.sin(2*np.pi*.07*step))
    crowd=z*amp
    # accent de percussion douce aux transitions majeures
    for when in (4.75,18.39,22.81,35.90,43.70,48.62,54.79,63.39):
        start=int(when*sample);cnt=min(N-start,int(.22*sample))
        if cnt>0:
            t=np.arange(cnt)/sample
            swoosh=.0055*np.sin(2*np.pi*(110+580*t)*t)*np.exp(-17*t)
            crowd[start:start+cnt]+=swoosh
    data=(np.clip(crowd,-.9,.9)*32767).astype(np.int16)
    with wave.open(str(path),'wb') as wf:
        wf.setframerate(sample);wf.setnchannels(1);wf.setsampwidth(2);wf.writeframes(data.tobytes())

def probe(fp):
    q=subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',str(fp)])
    return json.loads(q)

def make_background_sources(input_path:Path):
    """Évite d'illustrer une compétition avec un évènement hors contexte.

    Remplacements issus exclusivement du MP4 d'origine et d'une image du
    projet source fournie par l'auteur : aucun photomontage de faux match.
    """
    source=cv2.VideoCapture(str(input_path))
    def at(t):
        source.set(cv2.CAP_PROP_POS_MSEC,t*1000)
        ok,img=source.read()
        if not ok:raise RuntimeError('Capture source impossible a '+str(t))
        return img
    frames={
        'bellingham_interview':at(33.2),
        'spain_euro2024':at(37.4),
        'stadium_neutral':at(13.3),
        'bellingham_mondial':at(56.2),
        'pedri_selection_illustration':at(41.0),
    }
    source.release()
    # Photo du joueur sous le maillot espagnol issue du MP4 fourni.
    # Il s'agit d'une illustration du joueur, pas d'une capture de la demi-finale 2021.
    return frames

def corrected_background(t,original,frames):
    name=None
    if 7.75<=t<11.78:name='pedri_selection_illustration'
    elif 18.39<=t<22.81:name='bellingham_interview'
    elif 22.81<=t<26.90:name='spain_euro2024'
    elif 35.90<=t<43.70:name='stadium_neutral'
    elif 58.21<=t<63.39:name='bellingham_mondial'
    if not name:return original
    base=frames[name]
    # mouvement Ken Burns très léger, stable, sans faux mouvement de match
    duration=8 if name=='stadium_neutral' else 4.5
    pct=clamp((t%duration)/duration)
    zoom=1.016+0.018*pct
    ww=int(W/zoom);hh=int(H/zoom)
    x0=int((W-ww)*(.32+.30*pct));y0=int((H-hh)*(.30+.22*pct))
    x0=max(0,min(W-ww,x0));y0=max(0,min(H-hh,y0))
    cropped=base[y0:y0+hh,x0:x0+ww]
    return cv2.resize(cropped,(W,H),interpolation=cv2.INTER_LINEAR)

def render(input_path:Path,output_path:Path,timeline:Path,limit=None):
    global SEG,ENDS,SEG_BY_START
    SEG=json.loads(timeline.read_text(encoding='utf-8'))
    ENDS=[s['end'] for s in SEG];SEG_BY_START={s['start']:s for s in SEG}
    assert abs(SEG[-1]['end']-DURATION)<.1
    assert all(abs(SEG[i]['end']-SEG[i+1]['start'])<.002 for i in range(len(SEG)-1)), 'Timeline discontinue'
    meta=probe(input_path)
    streams=meta['streams']
    if not any(s['codec_type']=='audio' for s in streams):raise RuntimeError('La source ne contient pas de son')
    if not any(s.get('width')==W and s.get('height')==H for s in streams):raise RuntimeError('Source vidéo 1920x1080 nécessaire')
    duration=min(DURATION,limit if limit else DURATION)
    nframes=int(math.ceil(duration*FPS))
    cap=cv2.VideoCapture(str(input_path))
    replacement_frames=make_background_sources(input_path)
    if not cap.isOpened():raise RuntimeError('Impossible de lire le MP4')
    sourcefps=cap.get(cv2.CAP_PROP_FPS)
    if abs(sourcefps-FPS)>.2:raise RuntimeError(f'Vérifier FPS source : {sourcefps} vs {FPS}')
    out_folder=output_path.parent;out_folder.mkdir(parents=True,exist_ok=True)
    bed=out_folder/'scene8_ambiance_orig.wav';bed_audio(bed,duration)
    cmd=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-i',str(input_path),'-i',str(bed),'-filter_complex',
       '[1:a]aresample=48000,volume=1.0[v];[2:a]aresample=48000,volume=0.85[amb];[v][amb]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.94[a]',
       '-map','0:v','-map','[a]','-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','18','-maxrate','15M','-bufsize','30M','-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','192k','-movflags','+faststart',str(output_path)]
    ff=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for k in range(nframes):
            t=k/FPS
            ok,frame=cap.read()
            if not ok:break
            idx=min(len(SEG)-1,bisect.bisect_right(ENDS,t))
            seg=SEG[idx]
            # Photos cohérentes avec la narration, toutes en plein écran.
            frame=corrected_background(t,frame,replacement_frames)
            frame=cv2.convertScaleAbs(frame,alpha=1.035,beta=-2)
            graphic,hud=make_overlay(seg,t)
            blend_native(frame,graphic);blend_native(frame,hud)
            ff.stdin.write(frame.tobytes())
            if k%100==0:print(f'{t:5.1f} s / {duration:.1f} s  — {seg["kind"]}',flush=True)
    except BrokenPipeError:
        err=ff.stderr.read().decode(errors='replace')
        raise RuntimeError('Ffmpeg a refusé les images : '+err[:2000])
    finally:
        cap.release()
        if ff.stdin:ff.stdin.close()
    stderr=ff.stderr.read().decode(errors='replace')
    code=ff.wait()
    if code!=0:raise RuntimeError('FFmpeg : '+stderr)
    report={'source':str(input_path),'output':str(output_path),'duration':duration,'fps':FPS,'format':'1920x1080','timeline':SEG,'sources_json':'sources_verifiees.json','video_bytes':output_path.stat().st_size}
    (output_path.with_suffix('.rapport.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('EXPORT FINAL',output_path,output_path.stat().st_size,'octets',flush=True)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--timeline',type=Path,default=DEFAULT_TIMELINE)
    p.add_argument('--output',type=Path,default=ROOT/'exports'/'Scene_08_Pedri_Bellingham_V4_Premium_1080p25.mp4')
    p.add_argument('--limit',type=float,default=None,help='Export de test des N premières secondes')
    a=p.parse_args()
    render(a.input,a.output,a.timeline,a.limit)
if __name__=='__main__': main()