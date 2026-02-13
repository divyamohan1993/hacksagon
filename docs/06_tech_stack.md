# Technology Stack

## Programming Languages

| Language | Version | Usage |
|----------|---------|-------|
| **Python** | 3.11+ | Backend API, AI/ML inference, scientific computing, data pipeline |
| **TypeScript** | 5.4+ | Frontend dashboard, type-safe component architecture |
| **HTML5 / CSS3** | - | Canvas particle simulation, responsive dark-theme UI |

---

## Backend Frameworks & Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **FastAPI** | 0.110.0 | Async REST API + WebSocket server (ASGI) |
| **Uvicorn** | 0.27.1 | ASGI server with HTTP/WebSocket support |
| **Pydantic** | 2.6.1 | Data validation, serialization, settings management |
| **SQLAlchemy** | 2.0.25 | ORM for time-series data persistence |
| **aiosqlite** | 0.19.0 | Async SQLite driver for non-blocking DB operations |
| **NumPy** | 1.26.4 | Gaussian Plume math, Kriging matrix operations |
| **SciPy** | 1.12.0 | Scientific computing, optimization, spatial analysis |
| **httpx** | 0.27.0 | Async HTTP client for weather API integration |
| **YOLOv8 (Ultralytics)** | 8.1.0 | Real-time vehicle detection and classification (optional) |
| **OpenCV** | 4.9.0 | Video stream capture and frame processing (optional) |
| **python-dotenv** | 1.0.1 | Environment variable management |

---

## Frontend Frameworks & Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| **Next.js** | 14.2+ | React meta-framework with App Router, SSR, API proxying |
| **React** | 18.3+ | Component-based UI with hooks and state management |
| **Tailwind CSS** | 3.4+ | Utility-first CSS for dark-theme enterprise dashboard |
| **Leaflet** | 1.9.4 | Interactive maps with CartoDB Dark Matter tiles |
| **react-leaflet** | 4.2.1 | React bindings for Leaflet map components |
| **Recharts** | 2.12+ | Composable charting library for time-series and bar charts |
| **Lucide React** | 0.400+ | Icon library (Wind, Car, Truck, Heart, Volume, etc.) |
| **clsx** | 2.1+ | Conditional CSS class composition |

---

## External APIs & Data Sources

| API / Source | Purpose | Authentication |
|-------------|---------|---------------|
| **OpenWeatherMap API** | Real-time wind speed, direction, temperature, humidity | API Key (free tier) |
| **EPA AP-42 Database** | Vehicle emission factors (PM2.5, PM10, NOx, CO per class) | Bundled as JSON |
| **WHO Guidelines** | Health dose-response parameters, exposure thresholds | Bundled as JSON |
| **FHWA TNM** | Traffic noise reference emission levels per vehicle class | Bundled as JSON |
| **CartoDB Dark Matter** | Dark-themed map tiles for Leaflet | Open (no key) |

---

## Infrastructure & DevOps

| Tool | Purpose |
|------|---------|
| **Docker** | Containerized backend and frontend deployment |
| **Docker Compose** | Multi-service orchestration with health checks |
| **SQLite** | Local development database (upgradeable to PostgreSQL) |
| **WebSocket (RFC 6455)** | Real-time bidirectional data streaming |

---

## Scientific Models & Algorithms

| Model / Algorithm | Application |
|-------------------|-------------|
| **Gaussian Plume Dispersion Model** | Calculate pollutant concentrations from vehicle emissions |
| **Pasquill-Gifford Stability Classes** | Atmospheric stability classification for dispersion coefficients |
| **Ordinary Kriging Interpolation** | Spatial interpolation for continuous pollution surface |
| **Spherical Variogram Model** | Spatial autocorrelation modeling for Kriging |
| **Holt-Winters Exponential Smoothing** | Time-series forecasting with seasonal decomposition |
| **FHWA Traffic Noise Model (TNM)** | Acoustic pollution estimation from vehicle classification |
| **WHO Log-Linear Dose-Response** | Health impact scoring from pollutant exposure |
| **A* Pathfinding Algorithm** | Pollution-weighted minimum-exposure routing |
| **EPA AQI Breakpoint Calculation** | Standard air quality index from PM2.5 concentrations |
| **Haversine Distance Formula** | Geographic distance computation for routing heuristic |
