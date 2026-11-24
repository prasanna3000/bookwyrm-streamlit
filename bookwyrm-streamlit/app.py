"""What Would the Bookwyrm Say?

A silly-question app starring a fictional dragon who hoards books and never gives
a straight answer (except on a lucky day). Replies come from Qwen3 on Groq when a
key is configured in Streamlit secrets, and from a built-in reply bank otherwise.
"""
import html
import os
import random
import re
import threading
import time
import zlib
from collections import deque

import requests
import streamlit as st
import streamlit.components.v1 as components

import content as C

st.set_page_config(page_title="What Would the Bookwyrm Say?", page_icon="\U0001F409", layout="wide")

LUCK_ODDS = 1 / 6
STAMPS = ["DEFLECTED", "UNDER REVIEW", "SEE APPENDIX", "TO BE CONTINUED"]
MOODS = {
    "DEFLECTED": "\U0001F643",
    "UNDER REVIEW": "\U0001F9D0",
    "SEE APPENDIX": "\U0001F4D6",
    "TO BE CONTINUED": "⏳",
    "LUCKY DAY": "\U0001F340",
}
DEFAULT_BASE = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "qwen/qwen3-32b"
MAX_ASKS_PER_SESSION = 40   # per visitor, so one friend cannot drain the shared quota
MAX_CALLS_PER_MIN = 20      # across everyone, kept under Groq's free-tier limit
SHELF_SIZE = 12


# ----------------------------------------------------------------- settings
def secret(name, default=None):
    try:
        value = st.secrets[name]
    except Exception:
        value = os.environ.get(name)
    return value or default


API_KEY = secret("GROQ_API_KEY")
API_BASE = (secret("GROQ_BASE_URL", DEFAULT_BASE) or DEFAULT_BASE).rstrip("/")
MODEL = secret("GROQ_MODEL", DEFAULT_MODEL)


# ------------------------------------------------------------------ engines
def esc(text):
    return html.escape(str(text), quote=True)


def plain_answer(q):
    for rx, answer in C.PLAIN:
        if re.search(rx, q, re.I):
            return answer
    return None


def builtin_reply(q, nonce, lucky):
    rnd = random.Random(zlib.crc32((q.lower() + "|" + str(nonce)).encode()))
    if lucky:
        answer = plain_answer(q)
        if answer:
            return {
                "answer": answer,
                "footnotes": [{"t": f"The Almanac of Occasional Clarity, p. {rnd.randint(11, 100)}",
                               "n": "Ignore the tone. This one is true."}],
                "stamp": "LUCKY DAY", "progress": 100, "lucky": True, "source": "builtin",
            }
    pool = C.DEFAULT_T
    for rx, tangents in C.THEMES:
        if re.search(rx, q, re.I):
            pool = tangents
            break
    parts = []
    if rnd.random() < 0.5:
        parts.append(rnd.choice(C.ACTIONS))
    parts += [rnd.choice(C.OPENERS), rnd.choice(pool)]
    if rnd.random() < 0.35:
        parts.append(rnd.choice(C.ASIDES))
    parts.append(rnd.choice(C.CLOSERS))
    first, second = rnd.sample(range(len(C.FN)), 2)
    footnotes = [{"t": f"{C.FN[i][0]}, p. {rnd.randint(11, 480)}", "n": C.FN[i][1]} for i in (first, second)]
    return {
        "answer": " ".join(parts), "footnotes": footnotes, "stamp": rnd.choice(STAMPS),
        "progress": rnd.randint(7, 60), "lucky": False, "source": "builtin",
    }


def parse_reply(text, lucky):
    import json
    text = re.sub(r"<think>[\s\S]*?</think>", "", str(text or ""))
    text = text.replace("```json", "").replace("```", "")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON found")
    data = json.loads(text[start:end + 1])
    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("no answer")
    footnotes = []
    for f in (data.get("footnotes") or [])[:3]:
        if isinstance(f, dict):
            footnotes.append({"t": str(f.get("t") or "Untitled Volume"), "n": str(f.get("n") or "")})
    stamp = data.get("stamp") if data.get("stamp") in STAMPS else "DEFLECTED"
    try:
        progress = max(1, min(99, int(data.get("progress"))))
    except (TypeError, ValueError):
        progress = 23
    if lucky:
        stamp, progress = "LUCKY DAY", 100
    return {"answer": answer[:600], "footnotes": footnotes, "stamp": stamp,
            "progress": progress, "lucky": bool(lucky)}


def qwen_reply(q, lucky):
    persona = C.PERSONA + (C.LUCKY_NOTE if lucky else "")
    try:
        resp = requests.post(
            API_BASE + "/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "temperature": 0.9, "max_tokens": 1500, "stream": False,
                  "messages": [{"role": "system", "content": persona},
                               {"role": "user", "content": "/no_think\nQuestion: " + q}]},
            timeout=45,
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("the model took too long to answer")
    except requests.exceptions.RequestException:
        raise RuntimeError("could not reach the model server")
    if resp.status_code != 200:
        try:
            message = resp.json().get("error", {}).get("message", "")
        except ValueError:
            message = ""
        raise RuntimeError(f"HTTP {resp.status_code}" + (f" - {message[:120]}" if message else ""))
    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError):
        raise RuntimeError("the model sent an empty reply")
    try:
        reply = parse_reply(content, lucky)
    except Exception:
        raise RuntimeError("the model replied, but not in the expected JSON format")
    reply["source"] = "qwen"
    reply["model"] = MODEL
    return reply


@st.cache_resource
def _limiter():
    return {"lock": threading.Lock(), "calls": deque()}


def allow_call():
    limiter = _limiter()
    now = time.time()
    with limiter["lock"]:
        calls = limiter["calls"]
        while calls and now - calls[0] > 60:
            calls.popleft()
        if len(calls) >= MAX_CALLS_PER_MIN:
            return False
        calls.append(now)
        return True


def get_reply(q, engine, again):
    ss = st.session_state
    ss.nonce = ss.nonce + 1 if again else 0
    lucky = random.random() < LUCK_ODDS
    reply, fallback = None, None
    if engine == "qwen":
        if ss.asks >= MAX_ASKS_PER_SESSION:
            fallback = "you have used all your Qwen questions for this visit"
        elif not allow_call():
            fallback = "the shared Qwen quota is busy, try again in a minute"
        else:
            try:
                reply = qwen_reply(q, lucky)
            except Exception as err:  # shown to the visitor, then we fall back
                fallback = str(err)
    if reply is None:
        reply = builtin_reply(q, ss.nonce, lucky)
        if fallback:
            reply["fallback"] = fallback
    ss.asks += 1
    return reply


# -------------------------------------------------------------------- state
ss = st.session_state
for key, default in {"shelf": [], "count": 0, "asks": 0, "nonce": 0, "current": None,
                     "pop": False, "q": "", "trigger": None, "confetti": 0}.items():
    ss.setdefault(key, default)


def use_chip(text):
    ss.q = text
    ss.trigger = "send"


def start_send():
    ss.trigger = "send"


def start_again():
    ss.trigger = "again"


def reopen(index):
    ss.current = ss.shelf[index]
    ss.pop = False


# ------------------------------------------------------------------- styling
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Rajdhani:wght@500;600;700&display=swap');
:root{--cyan:#19f0ff;--magenta:#ff3df2;--lime:#b6ff3c;--dim:#8d9bc4;--text:#e6ecff;--panel:rgba(10,15,32,.86)}
html,body{background:#070a14!important}
.stApp{background:radial-gradient(900px 500px at 15% -10%,rgba(255,61,242,.16),transparent 60%),radial-gradient(900px 500px at 100% 20%,rgba(25,240,255,.14),transparent 60%)!important;position:relative;z-index:1}
[data-testid="stHeader"],[data-testid="stToolbar"],footer,#MainMenu{display:none!important}
.block-container{padding:20px clamp(16px,3vw,44px) 48px!important;max-width:none!important}
.stApp,.stApp p,.stApp label,.stApp li,.stApp span,.stApp div{font-family:'Rajdhani','Trebuchet MS',sans-serif;font-weight:600}
.stApp h1,.stApp h2{font-family:'Press Start 2P',monospace!important;font-weight:400!important}
.bw-hud{display:flex;align-items:center;gap:14px;padding:10px 14px;border:2px solid var(--cyan);background:var(--panel);box-shadow:0 0 18px rgba(25,240,255,.35),inset 0 0 24px rgba(25,240,255,.07);font-family:'Press Start 2P',monospace;font-size:10px;color:var(--dim);margin-bottom:18px}
.bw-hud b{color:var(--lime);font-weight:400;text-shadow:0 0 8px rgba(182,255,60,.6)}
.bw-xp{flex:1;height:12px;border:2px solid var(--cyan);background:#04060d}
.bw-xp i{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--magenta));box-shadow:0 0 10px var(--cyan)}
.bw-title{margin:0 0 12px;font-family:'Press Start 2P',monospace;font-weight:400;line-height:1.55;font-size:clamp(17px,2.6vw,32px);text-transform:uppercase;color:#fff;text-shadow:3px 0 var(--magenta),-3px 0 var(--cyan),0 0 22px rgba(25,240,255,.5)}
.bw-title span{display:block}
.bw-sub{color:var(--dim);font-size:20px;max-width:48ch;margin:0 0 10px}
.bw-small{font-family:'Press Start 2P',monospace;font-size:10px;line-height:1.8;color:var(--dim);margin:0 0 6px}
.bw-small b{color:var(--magenta);font-weight:400}
.bw-luck{font-family:'Press Start 2P',monospace;font-size:10px;line-height:1.8;color:var(--lime);text-shadow:0 0 8px rgba(182,255,60,.5);margin:0 0 14px}
.bw-label{font-family:'Press Start 2P',monospace;font-size:10px;color:var(--cyan);margin:10px 0 6px}
.bw-card{border:2px solid var(--cyan);background:var(--panel);padding:16px;display:flex;flex-direction:column;gap:12px;box-shadow:0 0 18px rgba(25,240,255,.35),inset 0 0 24px rgba(25,240,255,.07);animation:bwfade .5s ease both}
.bw-card.lucky{border-color:var(--lime);animation:bwglow 1.4s ease-in-out infinite alternate;box-shadow:0 0 28px rgba(182,255,60,.6),inset 0 0 26px rgba(182,255,60,.12)}
@keyframes bwglow{from{box-shadow:0 0 14px rgba(182,255,60,.4)}to{box-shadow:0 0 34px rgba(182,255,60,.8)}}
@keyframes bwfade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.bw-call{display:flex;justify-content:space-between;font-family:'Press Start 2P',monospace;font-size:9px;color:var(--dim)}
.bw-quest{font-family:'Press Start 2P',monospace;font-size:clamp(11px,1vw,14px);line-height:1.8;color:var(--cyan);overflow-wrap:anywhere}
.bw-talk{display:flex;gap:14px;align-items:flex-start}
.bw-portrait{flex:0 0 auto;width:clamp(72px,9vw,128px);height:clamp(72px,9vw,128px);display:flex;align-items:center;justify-content:center;font-size:clamp(40px,5vw,70px);line-height:1;border:3px solid var(--magenta);background:rgba(0,0,0,.5);box-shadow:0 0 16px rgba(255,61,242,.5)}
.bw-card.lucky .bw-portrait{border-color:var(--lime);box-shadow:0 0 18px rgba(182,255,60,.7)}
.bw-who{flex:1;min-width:0;display:flex;flex-direction:column;gap:8px}
.bw-name{font-family:'Press Start 2P',monospace;font-size:11px;color:var(--magenta)}
.bw-stamp{font-family:'Press Start 2P',monospace;font-size:9px;color:#ffc84a;border:2px solid #ffc84a;padding:4px 6px;margin-left:8px}
.bw-card.lucky .bw-stamp{color:#08140a;background:var(--lime);border-color:var(--lime);box-shadow:0 0 12px rgba(182,255,60,.8)}
.bw-answer{font-size:clamp(21px,1.7vw,28px);line-height:1.45;color:var(--text);overflow-wrap:anywhere;margin:0}
.bw-fn{list-style:none;margin:0;padding:10px 0 0;border-top:2px dashed rgba(141,155,196,.4);display:flex;flex-direction:column;gap:6px}
.bw-fn li{font-size:16px;line-height:1.35;color:var(--dim)}
.bw-fn i{color:var(--cyan);font-style:normal}
.bw-fn sup{font-family:'Press Start 2P',monospace;font-size:8px;color:var(--lime);margin-right:5px}
.bw-meter{display:flex;align-items:center;gap:10px;font-family:'Press Start 2P',monospace;font-size:9px;color:var(--dim)}
.bw-bar{flex:1;height:12px;border:2px solid var(--lime);background:#04060d}
.bw-bar i{display:block;height:100%;background:linear-gradient(90deg,var(--lime),var(--cyan));box-shadow:0 0 10px var(--lime)}
.bw-source{font-family:'Press Start 2P',monospace;font-size:9px;line-height:1.7;color:var(--dim);overflow-wrap:anywhere}
.bw-source.bad{color:#ffc84a}
.bw-note{font-family:'Press Start 2P',monospace;font-size:9px;line-height:1.7;color:#ffc84a}
.bw-pop{position:fixed;top:12px;left:50%;z-index:9999;display:flex;align-items:center;gap:14px;max-width:calc(100vw - 24px);padding:10px 18px;background:var(--panel);border:3px solid var(--magenta);box-shadow:0 0 26px rgba(255,61,242,.65);pointer-events:none;animation:bwdrop 2.6s ease forwards}
.bw-pop.lucky{border-color:var(--lime);box-shadow:0 0 30px rgba(182,255,60,.8)}
.bw-pop .e{font-size:56px;line-height:1}
.bw-pop .t{font-family:'Press Start 2P',monospace;font-size:11px;line-height:1.6;color:var(--text)}
@keyframes bwdrop{0%{opacity:0;transform:translate(-50%,-150%)}12%{opacity:1;transform:translate(-50%,0)}18%{transform:translate(-50%,-6px)}24%{transform:translate(-50%,0)}82%{opacity:1;transform:translate(-50%,0)}100%{opacity:0;transform:translate(-50%,-150%)}}
/* inputs and buttons */
.stTextArea textarea{background:rgba(0,0,0,.45)!important;color:#fff!important;border:2px solid rgba(25,240,255,.55)!important;border-radius:0!important;font-size:21px!important;font-weight:600!important;caret-color:var(--magenta)}
.stTextArea textarea:focus{border-color:var(--magenta)!important;box-shadow:0 0 14px rgba(255,61,242,.5)!important}
.stTextArea label p,.stRadio label p{font-family:'Press Start 2P',monospace!important;font-size:10px!important;color:var(--cyan)!important}
.stButton>button{background:linear-gradient(180deg,rgba(25,240,255,.26),rgba(25,240,255,.09));border:2px solid var(--cyan);color:#eafcff;border-radius:4px;box-shadow:0 4px 0 #0b5a66,0 0 10px rgba(25,240,255,.25);font-family:'Rajdhani',sans-serif;font-weight:700;letter-spacing:.04em;text-transform:uppercase;transition:transform .08s,box-shadow .08s,filter .15s}
.stButton>button:hover{filter:brightness(1.25);color:#fff;border-color:var(--cyan)}
.stButton>button:active{transform:translateY(3px);box-shadow:0 1px 0 #0b5a66}
.stButton>button[kind="primary"]{background:linear-gradient(90deg,#d12ac4,#2fb7ff);border:2px solid rgba(255,255,255,.35);box-shadow:0 5px 0 #5b1457,0 0 18px rgba(255,61,242,.45);font-family:'Press Start 2P',monospace;font-size:12px;padding:14px 16px}
.bw-model{border:2px dashed var(--lime);background:rgba(182,255,60,.07);padding:10px 12px;margin:8px 0}
.bw-model .l{font-family:'Press Start 2P',monospace;font-size:11px;color:var(--lime);text-shadow:0 0 8px rgba(182,255,60,.6);margin-bottom:6px}
.bw-model .a{font-size:17px;color:var(--text)}
.bw-model .a b{color:var(--lime)}
@media (max-width:900px){.bw-talk{gap:10px}}
@media (prefers-reduced-motion:reduce){.bw-card,.bw-card.lucky,.bw-pop{animation:none}}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

PARTICLES_JS = """
<script>
(function(){
  try{
    var P=window.parent,d=P.document;
    if(d.getElementById('bw-bg')) return;
    var reduce=P.matchMedia&&P.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var c=d.createElement('canvas');c.id='bw-bg';
    c.style.cssText='position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none';
    d.body.appendChild(c);
    var ctx=c.getContext('2d'),dpr=Math.min(P.devicePixelRatio||1,2),w=0,h=0,pts=[],m={x:-999,y:-999};
    var cols=['#19f0ff','#ff3df2','#b6ff3c'],LINK=120,GRAB=150;
    function size(){
      w=P.innerWidth;h=P.innerHeight;c.width=w*dpr;c.height=h*dpr;ctx.setTransform(dpr,0,0,dpr,0,0);
      var n=Math.max(34,Math.min(88,Math.round(w*h/14000)));
      while(pts.length<n) pts.push({x:Math.random()*w,y:Math.random()*h,vx:(Math.random()-.5)*.55,vy:(Math.random()-.5)*.55,r:1+Math.random()*1.8,c:cols[pts.length%cols.length]});
      pts.length=n;
    }
    function draw(){
      ctx.clearRect(0,0,w,h);
      for(var i=0;i<pts.length;i++){
        var p=pts[i],dx,dy,dd;
        if(!reduce){
          dx=p.x-m.x;dy=p.y-m.y;dd=Math.sqrt(dx*dx+dy*dy);
          if(dd<90&&dd>0){p.x+=dx/dd*1.4;p.y+=dy/dd*1.4;}
          p.x+=p.vx;p.y+=p.vy;
          if(p.x<0||p.x>w)p.vx*=-1;
          if(p.y<0||p.y>h)p.vy*=-1;
        }
        ctx.globalAlpha=.9;ctx.fillStyle=p.c;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,6.2832);ctx.fill();
        for(var j=i+1;j<pts.length;j++){
          var q=pts[j];dx=p.x-q.x;dy=p.y-q.y;dd=Math.sqrt(dx*dx+dy*dy);
          if(dd<LINK){ctx.globalAlpha=(1-dd/LINK)*.45;ctx.strokeStyle='#19f0ff';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.stroke();}
        }
        dx=p.x-m.x;dy=p.y-m.y;dd=Math.sqrt(dx*dx+dy*dy);
        if(dd<GRAB){ctx.globalAlpha=(1-dd/GRAB)*.7;ctx.strokeStyle='#ff3df2';ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(m.x,m.y);ctx.stroke();}
      }
      ctx.globalAlpha=1;
    }
    function loop(){draw();P.requestAnimationFrame(loop);}
    P.addEventListener('resize',size);
    P.addEventListener('pointermove',function(e){m.x=e.clientX;m.y=e.clientY;},{passive:true});
    P.addEventListener('pointerup',function(){m.x=-999;m.y=-999;},{passive:true});
    size();draw();if(!reduce) loop();
  }catch(e){}
})();
</script>
"""

CONFETTI_JS = """
<script>
(function(){
  try{
    var P=window.parent,d=P.document;
    if(P.matchMedia&&P.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var old=d.getElementById('bw-confetti');if(old) old.remove();
    var c=d.createElement('canvas');c.id='bw-confetti';
    c.style.cssText='position:fixed;inset:0;width:100%;height:100%;z-index:9998;pointer-events:none';
    d.body.appendChild(c);
    var dpr=Math.min(P.devicePixelRatio||1,2),w=P.innerWidth,h=P.innerHeight;
    c.width=w*dpr;c.height=h*dpr;
    var ctx=c.getContext('2d');ctx.scale(dpr,dpr);
    var cols=['#19f0ff','#ff3df2','#b6ff3c','#ffc84a','#ffffff','#7b5cff'],parts=[];
    for(var i=0;i<150;i++){var side=i%2;
      parts.push({x:side?w:0,y:h,vx:(side?-1:1)*(2+Math.random()*7),vy:-(11+Math.random()*10),r:Math.random()*6.28,vr:(Math.random()-.5)*.4,s:6+Math.random()*6,col:cols[i%cols.length]});}
    var start=P.performance.now();
    (function frame(now){
      var t=now-start;ctx.clearRect(0,0,w,h);
      parts.forEach(function(q){
        q.vy+=.36;q.vx*=.992;q.x+=q.vx;q.y+=q.vy;q.r+=q.vr;
        ctx.save();ctx.translate(q.x,q.y);ctx.rotate(q.r);ctx.globalAlpha=Math.max(0,1-t/3800);
        ctx.fillStyle=q.col;ctx.fillRect(-q.s/2,-q.s/4,q.s,q.s/2);ctx.restore();
      });
      if(t<3800) P.requestAnimationFrame(frame); else c.remove();
    })(start);
  }catch(e){}
})();
</script>
"""

def run_script(markup):
    """Run a small script that decorates the parent page. Uses st.iframe on new Streamlit, components.html on old."""
    if hasattr(st, "iframe"):
        st.iframe(markup, height=1)
    else:
        components.html(markup, height=0)


run_script(PARTICLES_JS)

# --------------------------------------------------------------------- page
level = 1 + ss.count // 3
xp = max(6, (ss.count % 3) / 3 * 100)
st.markdown(
    "".join([
        '<div class="bw-hud"><span>LVL <b>', str(level), '</b></span>',
        '<span style="flex:1;display:flex;align-items:center;gap:8px">XP<span class="bw-xp"><i style="width:',
        f"{xp:.0f}", '%"></i></span></span>',
        '<span>SCORE <b>', f"{ss.count * 100:05d}", '</b></span><span>LUCK <b>1/6</b></span></div>',
    ]),
    unsafe_allow_html=True,
)

left, right = st.columns([5, 7], gap="large")

with left:
    st.markdown(
        '<h1 class="bw-title"><span>What Would</span><span>The Bookwyrm</span><span>Say?</span></h1>'
        '<p class="bw-sub">It has read every book in the dungeon except the page you need. '
        "Send a silly question and collect a ruling, a tangent, and a citation.</p>"
        '<p class="bw-small">STATUS: <b>MID-CHAPTER</b> &middot; AVAILABILITY: <b>RELUCTANT</b></p>'
        '<p class="bw-luck">LUCKY DAY: ABOUT 1 IN 6 SLIPS GETS A STRAIGHT ANSWER</p>',
        unsafe_allow_html=True,
    )
    st.text_area("PLAYER INPUT ▸", key="q", max_chars=240, height=110,
                 placeholder="Is a hot dog a sandwich?")

    chip_cols = st.columns(3)
    for i, chip in enumerate(C.CHIPS):
        chip_cols[i % 3].button(chip, key=f"chip{i}", on_click=use_chip, args=(chip,), use_container_width=True)

    options = ["Built-in", "Qwen3"] if API_KEY else ["Built-in"]
    st.markdown('<div class="bw-model"><div class="l">&#9654; SELECT MODEL</div></div>', unsafe_allow_html=True)
    choice = st.radio("Select model", options, index=len(options) - 1, horizontal=True,
                      key="engine", label_visibility="collapsed")
    engine = "qwen" if choice == "Qwen3" else "builtin"
    active = f"QWEN3 · {MODEL}" if engine == "qwen" else "BUILT-IN BOOKWYRM (NO MODEL)"
    st.markdown(f'<div class="bw-model"><div class="a">Active model: <b>{esc(active)}</b></div></div>',
                unsafe_allow_html=True)
    if not API_KEY:
        st.markdown('<p class="bw-note">Qwen3 is off because no GROQ_API_KEY is set. '
                    "See the README to turn it on.</p>", unsafe_allow_html=True)

    st.button("SEND ▶", key="send", type="primary", on_click=start_send, use_container_width=True)
    note_slot = st.empty()

    trigger, ss.trigger = ss.trigger, None
    if trigger in ("send", "again"):
        question = (ss.current["q"] if trigger == "again" and ss.current else ss.q).strip()
        if not question:
            note_slot.markdown('<p class="bw-note">Write a question on the slip first.</p>', unsafe_allow_html=True)
        else:
            with st.spinner("The Bookwyrm is turning pages..."):
                reply = get_reply(question, engine, trigger == "again")
            ss.current = {"q": question, "rep": reply}
            ss.shelf = [s for s in ss.shelf if s["q"] != question]
            ss.shelf.insert(0, ss.current)
            ss.shelf = ss.shelf[:SHELF_SIZE]
            ss.count += 1
            ss.pop = True
            if reply["lucky"]:
                ss.confetti += 1
            if reply.get("fallback"):
                note_slot.markdown(
                    f'<p class="bw-note">Fallback: {esc(reply["fallback"])}. The built-in Bookwyrm answered instead.</p>',
                    unsafe_allow_html=True)
            elif reply["lucky"]:
                note_slot.markdown('<p class="bw-note">It\'s your lucky day. It answered plainly.</p>',
                                   unsafe_allow_html=True)

with right:
    current = ss.current
    if current is None:
        sample_q = "Is a hot dog a sandwich?"
        current = {"q": sample_q, "rep": builtin_reply(sample_q, 0, False)}
    rep = current["rep"]
    mood = MOODS.get(rep["stamp"], "\U0001F409")
    if rep.get("fallback"):
        source = f"BUILT-IN (FALLBACK: {rep['fallback']})"
    elif rep.get("source") == "qwen":
        source = f"QWEN3 · {rep.get('model', '')}"
    else:
        source = "BUILT-IN"
    footnotes = "".join(
        f'<li><sup>{i + 1}</sup><i>{esc(f["t"])}</i>. {esc(f["n"])}</li>' for i, f in enumerate(rep["footnotes"]))
    progress_label = "ATTENTION: FULL" if rep["lucky"] else f"ATTENTION: {rep['progress']}%"
    slip_no = 1000 + zlib.crc32(current["q"].encode()) % 9000
    st.markdown(
        "".join([
            f'<div class="bw-card{" lucky" if rep["lucky"] else ""}">',
            f'<div class="bw-call"><span>DIALOGUE</span><span>SLIP #{slip_no}</span></div>',
            f'<div class="bw-quest">“{esc(current["q"])}”</div>',
            f'<div class="bw-talk"><div class="bw-portrait">{mood}</div><div class="bw-who">',
            f'<div><span class="bw-name">THE BOOKWYRM</span><span class="bw-stamp">STATUS: {esc(rep["stamp"])}</span></div>',
            f'<p class="bw-answer">{esc(rep["answer"])}</p></div></div>',
            f'<ul class="bw-fn">{footnotes}</ul>',
            f'<div class="bw-meter"><span>{progress_label}</span><div class="bw-bar"><i style="width:{rep["progress"]}%"></i></div></div>',
            f'<div class="bw-source{" bad" if rep.get("fallback") else ""}">SOURCE: {esc(source)}</div>',
            "</div>",
        ]),
        unsafe_allow_html=True,
    )
    st.button("ASK AGAIN ↻", key="again", on_click=start_again)

    if ss.pop and ss.current is not None:
        label = "LUCKY DAY! STRAIGHT ANSWER" if rep["lucky"] else rep["stamp"]
        st.markdown(
            f'<div class="bw-pop{" lucky" if rep["lucky"] else ""}"><span class="e">{mood}</span>'
            f'<span class="t">{esc(label)}</span></div>',
            unsafe_allow_html=True,
        )
        ss.pop = False
        if rep["lucky"]:
            run_script(CONFETTI_JS + f"<!-- {ss.confetti} -->")

st.markdown('<h2 style="font-size:13px;color:#b6ff3c;margin:26px 0 4px">INVENTORY</h2>'
            '<p class="bw-sub" style="font-size:16px">Every answered slip drops into a slot. Tap one to reopen it.</p>',
            unsafe_allow_html=True)
if not ss.shelf:
    st.markdown('<p class="bw-small">EMPTY SLOTS. SEND A QUESTION TO LOOT ONE.</p>', unsafe_allow_html=True)
else:
    per_row = 6
    for start in range(0, len(ss.shelf), per_row):
        cols = st.columns(per_row)
        for offset, item in enumerate(ss.shelf[start:start + per_row]):
            emoji = MOODS.get(item["rep"]["stamp"], "\U0001F409")
            short = item["q"] if len(item["q"]) <= 20 else item["q"][:19] + "…"
            cols[offset].button(f"{emoji} {short}", key=f"slot{start + offset}", on_click=reopen,
                                args=(start + offset,), use_container_width=True, help=item["q"])

st.markdown(
    '<p class="bw-sub" style="font-size:15px;margin-top:24px">The Bookwyrm is a fictional character. '
    "Every book it cites is invented. Questions you send are passed to a Qwen3 model hosted by Groq "
    "when Qwen3 is selected, so please don't type anything private.</p>",
    unsafe_allow_html=True,
)
