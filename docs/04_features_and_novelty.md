# Features and Novelty

## 5 Unique Features (Never Implemented Before in This Combination)

---

### 1. Kriging-Interpolated Virtual Sensor Mesh Network

**What it does:** Transforms 6 discrete camera-based pollution readings into a continuous city-wide pollution surface using Ordinary Kriging geostatistical interpolation.

**Why it's novel:**
- Kriging is used in mining geology and meteorology but has **never been applied to real-time traffic-camera-derived pollution data**
- Computes a semivariogram to model spatial autocorrelation of pollution
- Solves a linear system of Kriging equations at each grid point
- Produces a 25x25 resolution heatmap with **mathematically optimal, unbiased estimates**
- Provides pollution estimates at locations with NO physical sensor

**Scientific Basis:** Matheron, G. (1963). Principles of Geostatistics. *Economic Geology*, 58(8).

---

### 2. Exposure Dosimetry with "Equivalent Cigarettes" Health Metric

**What it does:** Converts raw PM2.5 concentrations into a human-understandable health impact score using WHO dose-response curves, including a novel "equivalent cigarettes smoked" metric.

**Why it's novel:**
- Goes beyond standard AQI -- calculates **cumulative inhaled dose** using breathing rate × concentration × time
- Uses WHO log-linear dose-response relationship (RR = 1.06 per 10 μg/m³ PM2.5)
- Converts exposure to **equivalent cigarettes** (1 cigarette ~ 22 μg/m³ for 24h, Berkeley Earth methodology)
- Vulnerability-adjusted scores for children, elderly, and asthmatic populations
- No existing air quality dashboard provides real-time dosimetry with cigarette equivalence

**Scientific Basis:** WHO Global Air Quality Guidelines (2021); Apte et al., "Addressing Global Mortality from Ambient PM2.5," *Environ. Sci. Technol.* (2015).

---

### 3. Acoustic Pollution Co-Estimation (FHWA Traffic Noise Model)

**What it does:** Extracts noise pollution levels (in dB(A)) from the same vehicle classification data used for air quality, providing **two environmental metrics from one camera feed**.

**Why it's novel:**
- Uses FHWA Traffic Noise Model (TNM) reference emission levels:
  - Heavy Truck: 84 dB(A) at 15m
  - Car: 67 dB(A) at 15m
  - Bus: 81 dB(A) at 15m
  - Motorcycle: 78 dB(A) at 15m
- Applies logarithmic sound addition for multiple sources: L_total = 10·log₁₀(Σ10^(Lᵢ/10))
- Distance attenuation: L = L_ref - 20·log₁₀(d/d_ref)
- **No other system derives noise pollution from traffic cameras** -- all existing noise monitoring requires dedicated microphone hardware

**Scientific Basis:** FHWA Traffic Noise Model (TNM) Version 2.5 Technical Manual.

---

### 4. Real-Time Gaussian Plume Particle Visualization

**What it does:** Renders a 60fps HTML5 Canvas particle simulation showing how vehicle exhaust disperses through the atmosphere based on real wind data and Gaussian physics.

**Why it's novel:**
- Each particle represents a pollution "packet" following actual Gaussian dispersion equations
- Particles spawn at emission sources proportional to real vehicle count × emission factor
- Movement governed by real-time wind direction and speed from OpenWeatherMap
- Gaussian spread perpendicular to wind direction (σ_y dispersion coefficient)
- Color-coded by concentration: green (low) → yellow → orange → red (high)
- Age-based transparency decay simulating atmospheric dilution
- **No air quality platform provides real-time physics-based particle visualization** -- most use static heatmaps

**Scientific Basis:** Turner, D.B. (1970). *Workbook of Atmospheric Dispersion Estimates*. EPA.

---

### 5. Pollution-Weighted A* Green Corridor Routing

**What it does:** Finds the healthiest walking/cycling path between two points by minimizing total pollution exposure, not just distance.

**Why it's novel:**
- Creates a weighted graph where edge cost = distance × (1 + α × normalized_PM2.5)
- Uses the Kriging-interpolated pollution grid as the cost surface
- Implements A* pathfinding with Haversine distance heuristic
- Compares with shortest (Euclidean) path to show **percentage reduction in pollution exposure**
- Calculates total inhaled dose along each route
- **Google Maps and Waze optimize for distance/time -- no routing engine optimizes for health exposure**

**Scientific Basis:** Hart, P.E., Nilsson, N.J., Raphael, B. (1968). "A Formal Basis for the Heuristic Determination of Minimum Cost Paths." *IEEE Transactions*.

---

## Additional Enterprise Features

| Feature | Description |
|---------|-------------|
| **Real-time WebSocket Streaming** | Sub-second data push to all connected clients with connection pooling |
| **Multi-Camera Fusion** | 6 simultaneous camera feeds processed and correlated |
| **Predictive Forecasting** | 6-hour PM2.5 predictions using Holt-Winters triple exponential smoothing |
| **EPA AQI Compliance** | AQI calculated using official EPA breakpoint tables |
| **Adaptive Traffic Simulation** | Time-of-day aware traffic generation with rush-hour patterns |
| **Dark-Theme Enterprise Dashboard** | Professional glassmorphism UI with 11 interactive widgets |
| **Docker-Ready Deployment** | One-command deployment via docker-compose |
| **Graceful Degradation** | Works without API keys (simulated weather), without YOLO (simulated traffic) |
