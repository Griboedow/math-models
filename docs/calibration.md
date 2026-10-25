# Calibration without a laboratory

1. **Mass and dimensions.** Weigh the complete stand and the ball separately.
   Measure the ball diameter in two directions, its height, the horizontal
   distance to the hand, and hand height above the surface under the feet.
   Enter semi-axes.

2. **Starting resistance.** Remove the ball. Pull the platform tangentially
   with yarn at a known radius r, measuring the force needed to start and
   sustain slow rotation. `τ_start = F_start r`, `τ_run ≈ F_slow r`.
   Use a sufficiently sensitive force gauge; coarse scales cannot resolve
   these small forces. Small known weights are an alternative if guide
   friction is accounted for. 1 gram-force = 0.00980665 N.
   Measure the assembled mechanism at several platform positions.

3. **Ball on the platform.** Hold the platform and assess how easily the ball
   rotates relative to it. A tight spindle fit adds coupling, represented by
   `spindle_coupling_Nm`. Repeat with a nearly empty ball. Without a measurement,
   keep the additional torque at zero and treat the slip warning as a reason
   to check the fit.

4. **Yarn and rhythm.** Record a short video of normal knitting and estimate
   the period and length of each draw. To estimate effective stiffness,
   measure extension ΔL under a small known force F: `EA ≈ F L / ΔL`.
   Repeat several times because yarn is nonlinear and exhibits hysteresis.
   Estimate layer-peeling resistance by slow unwinding with free rotation,
   subtracting the bearing contribution `τ_run/A`.

5. **Feet and rim.** Slowly pull the assembled stand horizontally at a low
   height: `μ_foot ≈ F_slide / (m_total g)`. Test actual yarn leaving low on
   a nearly empty ball with hands below the stand. A few minutes of knitting
   reveal overrun, slack, and snags better than another decimal place.

Save measured parameters in a new JSON file without overwriting the original
scenarios. Validate one simple situation first, then compare designs.
