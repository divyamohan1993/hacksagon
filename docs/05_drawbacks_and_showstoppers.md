# Drawbacks and Showstoppers

## Key Limitations (Max 5 Points)

---

### 1. Indirect Measurement Uncertainty
- Eco-Lens **estimates** pollution mathematically rather than directly measuring it with calibrated instruments
- The Gaussian Plume Model assumes flat terrain, steady-state meteorology, and no chemical transformation -- real urban environments have buildings, variable winds, and photochemical reactions
- **Mitigation:** Calibration against ground-truth reference sensors can reduce error to within ±15% (validated in literature); the model explicitly uses EPA-standard emission factors and Pasquill-Gifford stability classes to maximize accuracy

---

### 2. Camera Feed Dependency and Occlusion
- Vehicle classification accuracy degrades in poor visibility (fog, heavy rain, nighttime, snow)
- Camera occlusion (vehicles blocking each other) causes undercounting at high-density intersections
- YOLO accuracy drops to ~65% mAP in adverse weather vs. ~82% in clear conditions
- **Mitigation:** Temporal averaging over 5-second intervals smooths frame-level errors; simulation mode provides fallback data; future work includes thermal/IR camera support

---

### 3. Spatial Resolution Limitations
- Kriging interpolation between 6 sensors provides city-scale estimates, but street-level accuracy between sensors depends on the variogram model quality
- In areas far from any camera, estimates converge toward the mean (Kriging regression-to-mean property)
- Adding more cameras improves resolution but linearly increases compute cost
- **Mitigation:** The system is designed to scale horizontally; adding a new camera is as simple as adding a URL to the configuration

---

### 4. API Rate Limits and External Dependencies
- OpenWeatherMap free tier limits to 60 calls/minute (1,000/day) -- insufficient for production-scale deployment with hundreds of sensors
- Without live weather data, the system falls back to simulated wind patterns, reducing prediction accuracy
- Real-time video processing requires significant bandwidth (~2-5 Mbps per HD camera stream)
- **Mitigation:** 5-minute weather caching reduces API calls; paid tier ($40/month) supports 1,000,000 calls/day; edge computing can reduce bandwidth via on-camera inference

---

### 5. GPU Requirement for Real-Time YOLO Inference
- YOLOv8 inference at 5fps across 6 cameras demands GPU acceleration (NVIDIA T4 or better) for sub-200ms latency
- CPU-only inference on an E2 VM achieves ~1-2 fps, causing processing lag in high-traffic scenarios
- GPU cloud instances (e.g., GCE with T4) cost ~$0.35/hour vs. $0.04/hour for CPU-only
- **Mitigation:** YOLOv8-nano model reduces compute by 4x with acceptable accuracy trade-off; frame sampling at 5-second intervals reduces processing load by 25x compared to full video processing; simulation mode eliminates GPU dependency entirely for demonstrations
