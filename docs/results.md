# PITAYA calculation results

All values below use assumed, unmeasured yarn and stand properties. Foot and platform dimensions come from CAD. These are guides for testing, not product certification.

## Beside the hand on a desk

The working hand is 40 cm away horizontally and 20 cm above the surface under the feet. Stand mass: 230 g; full ball: 100 g; nearly empty ball: 10 g.

| Ball | Feed | Start, N | Coupled-model peak, N | Snag threshold, N | Traction throughout run |
|---|---|---:|---:|---:|---|
| Full | Knitting | 0.029 | 0.092 | 1.34 | yes, under the assumptions |
| Full | Crochet | 0.029 | 0.203 | 1.34 | yes, under the assumptions |
| Nearly empty | Knitting | 0.040 | 0.128 | 0.97 | no; hypothetical peak |
| Nearly empty | Crochet | 0.040 | 0.270 | 0.97 | no; hypothetical peak |

The nearly empty ball lacks platform traction in the baseline scenario, so its dynamic peaks must not be presented as actual forces. Spindle fit is particularly important; the separate `spindle_grip` analysis shows the effect of additional retaining torque.

![Tension](tension.png)

## What the comparison shows

- A smaller ball radius increases starting tension at the same assembly resistance. Lower mass does not guarantee easy feed.
- Sharp pulses in the selected crochet scenario cause more acceleration and overrun. This follows from the prescribed rhythm, not an inherent property of crochet.
- With default parameters, no PITAYA sliding or tipping was detected during normal feed. The roughly one-newton threshold concerns snagging and is not a large margin against a strong hand pull.
- With hands below a tall stand, a low exit from a nearly empty ball can intersect the rim. Changing leaf shape does not remove this cause: relative hand and stand heights matter more.
- A steep upward pull reduces the effective lever arm and ball contact force. Yarn may unwind in a different mode outside this model.
- Wider support raises the tipping limit but does not fix slippery feet. Compare actual contact geometry, not the diameter of decoration.

![Sensitivity](sensitivity.png)

## Check coverage

- 80 stand × ball × rhythm × position scenarios.
- 69 sensitivity cases: assembly resistance, foot friction, yarn elasticity, layer peeling, and spindle fit.
- 864 geometric path checks: two leaf types, two balls, three positions, three exit heights, and 24 azimuths. This is a check grid, not probability statistics.
- Analytical tests for equilibrium, tangency, rotational invariance, integrated feed, configuration errors, and time-step convergence.

For physical testing, start by checking low rotational resistance and the fit of a nearly empty ball. A normal desk beside the hand is a reasonable starting setup. After printing, enter measurements following the [calibration guide](calibration.md).
