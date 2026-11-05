import numpy as np, wave, sys
sr=44100; dur=float(sys.argv[2]); bpm=84; beat=60/bpm
t=np.arange(int(sr*dur))/sr
def note(f): return 440*2**((f-69)/12)
# progresión Am - F - C - G (2 compases cada acorde)
prog=[[57,60,64],[53,57,60],[48,55,64],[55,59,62]]
bar=beat*4; out=np.zeros_like(t)
for i,ch in enumerate(prog*10):
    s=i*bar*2
    if s>=dur: break
    idx=(t>=s)&(t<s+bar*2); tt=t[idx]-s
    env=np.minimum(1,tt/0.8)*np.minimum(1,(bar*2-tt)/0.8)
    for m in ch:
        f=note(m)
        out[idx]+=env*(0.5*np.sin(2*np.pi*f*tt)+0.25*np.sin(2*np.pi*f*1.003*tt)+0.12*np.sin(2*np.pi*2*f*tt))*0.18
    # bajo
    f=note(ch[0]-12); out[idx]+=env*0.25*np.sin(2*np.pi*f*tt)
# bombo suave y hi-hat
for k in np.arange(0,dur,beat):
    n=int(k*sr); L=int(0.25*sr); tt=np.arange(L)/sr
    kick=np.sin(2*np.pi*(55+60*np.exp(-tt*30))*tt)*np.exp(-tt*12)*0.35
    if int(round(k/beat))%2==0: out[n:n+L]+=kick[:len(out[n:n+L])]
    h=int((k+beat/2)*sr); Lh=int(0.05*sr)
    if h+Lh<len(out): out[h:h+Lh]+=np.random.randn(Lh)*np.exp(-np.arange(Lh)/sr*80)*0.04
# fade in/out y suavizado
fade=np.minimum(1,np.minimum(t/1.5,(dur-t)/2.0)); out*=fade
out=np.convolve(out,np.ones(6)/6,mode="same")
out=out/np.max(np.abs(out))*0.6
w=wave.open(sys.argv[1],"wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((out*32767).astype(np.int16).tobytes()); w.close()
