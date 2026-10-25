"""Generate figures and the English result note from saved numerical outputs."""
from pathlib import Path
import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'results/scenarios.json').read_text(encoding='utf-8'))
sens=json.loads((ROOT/'results/sensitivity.json').read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.facecolor':'#fffdf9','figure.facecolor':'#f4f2eb','axes.labelcolor':'#25352e','text.color':'#25352e','grid.color':'#d8e1d7'})
def get(ball,motion,setup='desk_side',stand='pitaya_v08'):
    return next(x for x in rows if x['case']==dict(stand=stand,ball=ball,motion=motion,setup=setup))
fig,axs=plt.subplots(2,2,figsize=(12,6),sharex=True)
for col,ba in enumerate(['full','nearly_empty']):
    for mo,color in [('knitting','#236b50'),('crochet','#ba2e71')]:
        r=get(ba,mo);t=[x['t_s'] for x in r['trace']]
        axs[0,col].plot(t,[x['tension_N'] for x in r['trace']],color=color,label='Knitting' if mo=='knitting' else 'Crochet',lw=1.8)
        axs[1,col].plot(t,[x['slack_m']*1000 for x in r['trace']],color=color,lw=1.8)
    axs[0,col].set_title('Full · 100 g' if ba=='full' else 'Nearly empty · 10 g (assumed coupling)')
    axs[1,col].set_xlabel('Time, s')
    for ax in axs[:,col]:ax.grid(alpha=.7)
axs[0,0].set_ylabel('Tension, N');axs[1,0].set_ylabel('Hypothetical excess feed, mm');axs[0,0].legend(frameon=False)
fig.suptitle('PITAYA · stand beside the hand on a desk',fontsize=17)
fig.text(.05,.015,'Scenario assumptions, no physical measurements. Right: coupling fails; the curves do not predict actual slip.',fontsize=9)
fig.tight_layout(rect=[0,.04,1,.94]);fig.savefig(ROOT/'docs/tension.png',dpi=150);plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(11,4.4))
for ba,col,label in [('full','#236b50','Full'),('nearly_empty','#ba2e71','Nearly empty')]:
    points=[x for x in sens if x['sweep']=='bearing_and_feet' and x['ball_preset']==ba and x['motion_preset']=='knitting' and x['foot_mu']==.45]
    axs[0].plot([x['start_torque_mNm'] for x in points],[x['start_N'] for x in points],'o-',color=col,label=label)
    setups=['desk_side','front','far_side','high_table','floor']
    axs[1].plot(range(5),[get(ba,'knitting',p)['summary']['static_limits']['critical_snag_N'] for p in setups],'o-',color=col,label=label)
axs[0].set(xlabel='Assembly starting torque, mN·m',ylabel='Starting tension, N',title='Small ball: shorter effective lever arm')
axs[1].set(xticks=range(5),xticklabels=['Side','Front','Far','Hands below','Floor'],ylabel='Static snag threshold, N',title='First sliding / tipping / lift-off limit')
for ax in axs:ax.grid(alpha=.7);ax.legend(frameon=False)
fig.tight_layout();fig.savefig(ROOT/'docs/sensitivity.png',dpi=150);plt.close(fig)

lines=['# PITAYA calculation results','',
'All values below use assumed, unmeasured yarn and stand properties. Foot and platform dimensions come from CAD. These are guides for testing, not product certification.','',
'## Beside the hand on a desk','',
'The working hand is 40 cm away horizontally and 20 cm above the surface under the feet. Stand mass: 230 g; full ball: 100 g; nearly empty ball: 10 g.','',
'| Ball | Feed | Start, N | Coupled-model peak, N | Snag threshold, N | Traction throughout run |',
'|---|---|---:|---:|---:|---|']
for ba in ['full','nearly_empty']:
    for mo in ['knitting','crochet']:
        x=get(ba,mo)['summary'];lines.append(f"| {'Full' if ba=='full' else 'Nearly empty'} | {'Knitting' if mo=='knitting' else 'Crochet'} | {x['static_limits']['start_tension_N']:.3f} | {x['peak_tension_N']:.3f} | {x['static_limits']['critical_snag_N']:.2f} | {'yes, under the assumptions' if x['hypotheses_valid_for_entire_run'] else 'no; hypothetical peak'} |")
lines += ['',
'The nearly empty ball lacks platform traction in the baseline scenario, so its dynamic peaks must not be presented as actual forces. Spindle fit is particularly important; the separate `spindle_grip` analysis shows the effect of additional retaining torque.','',
'![Tension](tension.png)','','## What the comparison shows','',
'- A smaller ball radius increases starting tension at the same assembly resistance. Lower mass does not guarantee easy feed.',
'- Sharp pulses in the selected crochet scenario cause more acceleration and overrun. This follows from the prescribed rhythm, not an inherent property of crochet.',
'- With default parameters, no PITAYA sliding or tipping was detected during normal feed. The roughly one-newton threshold concerns snagging and is not a large margin against a strong hand pull.',
'- With hands below a tall stand, a low exit from a nearly empty ball can intersect the rim. Changing leaf shape does not remove this cause: relative hand and stand heights matter more.',
'- A steep upward pull reduces the effective lever arm and ball contact force. Yarn may unwind in a different mode outside this model.',
'- Wider support raises the tipping limit but does not fix slippery feet. Compare actual contact geometry, not the diameter of decoration.','',
'![Sensitivity](sensitivity.png)','','## Check coverage','',
f'- {len(rows)} stand × ball × rhythm × position scenarios.',
f'- {len(sens)} sensitivity cases: assembly resistance, foot friction, yarn elasticity, layer peeling, and spindle fit.',
'- 864 geometric path checks: two leaf types, two balls, three positions, three exit heights, and 24 azimuths. This is a check grid, not probability statistics.',
'- Analytical tests for equilibrium, tangency, rotational invariance, integrated feed, configuration errors, and time-step convergence.','',
'For physical testing, start by checking low rotational resistance and the fit of a nearly empty ball. A normal desk beside the hand is a reasonable starting setup. After printing, enter measurements following the [calibration guide](calibration.md).','']
(ROOT/'docs/results.md').write_text('\n'.join(lines),encoding='utf-8')
print('Figures and result note generated from saved outputs')
