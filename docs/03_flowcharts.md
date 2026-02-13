# System Flowcharts

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph Input_Layer["INPUT LAYER"]
        CAM[/"Traffic CCTV Cameras<br/>(RTSP/MJPEG Streams)"/]
        WX[/"OpenWeatherMap API<br/>(Wind, Temp, Humidity)"/]
        EPA[/"EPA Emission Factors<br/>(AP-42 Database)"/]
    end

    subgraph Processing_Engine["PROCESSING ENGINE (FastAPI Backend)"]
        VS["Vision Service<br/>YOLOv8 Vehicle Detection"]
        PE["Physics Engine<br/>Gaussian Plume Model"]
        WS["Weather Service<br/>Real-time Wind Vectors"]
        MS["Mesh Service<br/>Kriging Interpolation"]
        FS["Forecast Service<br/>Holt-Winters Prediction"]
        HS["Health Service<br/>WHO Dose-Response"]
        AS["Acoustic Service<br/>FHWA TNM Noise Model"]
        RS["Routing Service<br/>A* Green Corridor"]
    end

    subgraph Data_Layer["DATA LAYER"]
        DB[(SQLite / PostgreSQL<br/>Time-Series Storage)]
        CACHE["In-Memory Cache<br/>Current State"]
    end

    subgraph Output_Layer["OUTPUT LAYER (Next.js Dashboard)"]
        MAP["Interactive Pollution Map<br/>Leaflet + Heatmap"]
        CHARTS["Real-Time Charts<br/>Recharts"]
        PARTICLE["Particle Simulation<br/>HTML5 Canvas"]
        HEALTH["Health Impact Panel"]
        ROUTE["Green Route Planner"]
    end

    CAM --> VS
    WX --> WS
    EPA --> PE
    VS -->|Vehicle Counts| PE
    WS -->|Wind Data| PE
    PE -->|Concentrations| MS
    PE -->|PM2.5 History| FS
    PE -->|PM2.5, NO2| HS
    VS -->|Vehicle Classes| AS
    MS -->|Pollution Grid| RS
    PE --> DB
    PE --> CACHE
    CACHE -->|WebSocket Push| MAP
    CACHE -->|WebSocket Push| CHARTS
    CACHE -->|Wind + Emissions| PARTICLE
    HS --> HEALTH
    RS --> ROUTE
```

---

## 2. Data Processing Pipeline

```mermaid
flowchart LR
    A["Camera Frame<br/>(every 5 sec)"] --> B["YOLOv8<br/>Inference"]
    B --> C{"Vehicle<br/>Classification"}
    C -->|"Class 7"| D["Trucks"]
    C -->|"Class 2"| E["Cars"]
    C -->|"Class 5"| F["Buses"]
    C -->|"Class 3"| G["Motorcycles"]

    D --> H["Emission Rate Q<br/>Q = Σ(Count × EPA Factor)"]
    E --> H
    F --> H
    G --> H

    I["OpenWeatherMap<br/>API Call"] --> J["Wind Speed u<br/>Wind Direction θ"]

    H --> K["Gaussian Plume<br/>Dispersion Model"]
    J --> K

    K --> L["PM2.5 Concentration"]
    K --> M["PM10 Concentration"]
    K --> N["NO2 Concentration"]
    K --> O["CO Concentration"]

    L --> P["AQI Calculation<br/>(EPA Breakpoints)"]
    L --> Q["Health Impact<br/>(WHO Dose-Response)"]
    L --> R["Kriging Grid<br/>Interpolation"]

    style A fill:#1e2538,stroke:#3b82f6,color:#f0f4f8
    style K fill:#1e2538,stroke:#00d68f,color:#f0f4f8
    style P fill:#1e2538,stroke:#f59e0b,color:#f0f4f8
```

---

## 3. Gaussian Plume Dispersion Model

```mermaid
flowchart TB
    subgraph Inputs
        Q["Emission Rate Q (g/s)<br/>= Trucks×0.070 + Cars×0.005<br/>+ Buses×0.055 + Motos×0.008"]
        U["Wind Speed u (m/s)<br/>from OpenWeatherMap"]
        STAB["Stability Class (A-F)<br/>from Wind Speed"]
    end

    subgraph Pasquill_Gifford["Pasquill-Gifford Coefficients"]
        SY["σy = a × x^0.894<br/>(Crosswind Dispersion)"]
        SZ["σz = c × x^d<br/>(Vertical Dispersion)"]
    end

    subgraph Equation["Gaussian Plume Equation"]
        FORMULA["C(x,y,z) = Q/(2π·u·σy·σz)<br/>× exp(-y²/2σy²)<br/>× [exp(-(z-H)²/2σz²)<br/>  + exp(-(z+H)²/2σz²)]"]
    end

    subgraph Output
        CONC["Concentration C<br/>(μg/m³ at receptor)"]
        AQI["AQI Score<br/>(0 - 500)"]
    end

    Q --> FORMULA
    U --> FORMULA
    STAB --> SY
    STAB --> SZ
    SY --> FORMULA
    SZ --> FORMULA
    FORMULA --> CONC
    CONC --> AQI
```

---

## 4. Real-Time WebSocket Communication Flow

```mermaid
sequenceDiagram
    participant FE as Next.js Frontend
    participant WS as WebSocket Server
    participant SIM as Simulation Loop
    participant YOLO as Vision Service
    participant PHY as Physics Engine
    participant WX as Weather API

    FE->>WS: Connect ws://localhost:8000/ws
    WS-->>FE: Initial State (all sensors)

    loop Every 5 seconds
        SIM->>YOLO: Get vehicle counts (per camera)
        YOLO-->>SIM: {trucks, cars, buses, motorcycles}
        SIM->>WX: Get wind data (cached 5 min)
        WX-->>SIM: {wind_speed, wind_direction}
        SIM->>PHY: Calculate dispersion
        PHY-->>SIM: {pm25, pm10, no2, co, aqi}
        SIM->>WS: Push sensor_update message
        WS-->>FE: WebSocketMessage JSON
        FE->>FE: Update Map, Charts, Particles
    end

    FE->>WS: Disconnect
    WS->>WS: Remove from connection pool
```

---

## 5. Green Corridor Routing Algorithm

```mermaid
flowchart TB
    START["User selects<br/>Start & End Points"] --> GRID["Generate Grid Graph<br/>over City Bounds"]
    GRID --> COST["Assign Edge Costs<br/>cost = distance × (1 + α × PM2.5)"]
    COST --> ASTAR["A* Pathfinding<br/>(Haversine Heuristic)"]
    ASTAR --> GREEN["Green Path<br/>(Least Pollution Exposure)"]

    COST --> DIRECT["Shortest Path<br/>(Distance Only)"]

    GREEN --> COMPARE["Compare Paths"]
    DIRECT --> COMPARE

    COMPARE --> RESULT["Result:<br/>✓ X% less pollution exposure<br/>✓ Y km vs Z km distance<br/>✓ Exposure dose comparison"]

    style START fill:#1e2538,stroke:#3b82f6,color:#f0f4f8
    style ASTAR fill:#1e2538,stroke:#00d68f,color:#f0f4f8
    style RESULT fill:#1e2538,stroke:#00d68f,color:#f0f4f8
```

---

## 6. Kriging Spatial Interpolation Flow

```mermaid
flowchart LR
    A["6 Discrete Sensor<br/>Readings"] --> B["Calculate<br/>Semivariogram<br/>γ(h)"]
    B --> C["Fit Spherical<br/>Variogram Model<br/>γ(h) = c₀ + c₁[1.5(h/a) - 0.5(h/a)³]"]
    C --> D["Build Kriging<br/>System Matrix<br/>[Γ]{λ} = {γ₀}"]
    D --> E["Solve for<br/>Kriging Weights λᵢ"]
    E --> F["Interpolate at<br/>25×25 Grid Points<br/>Ẑ = Σλᵢ·Z(xᵢ)"]
    F --> G["Continuous Pollution<br/>Surface (Heatmap)"]

    style A fill:#1e2538,stroke:#3b82f6,color:#f0f4f8
    style G fill:#1e2538,stroke:#00d68f,color:#f0f4f8
```

---

## 7. Health Impact Dosimetry Flow

```mermaid
flowchart TB
    PM["PM2.5 Reading<br/>(μg/m³)"] --> DOSE["Dose Calculation<br/>dose = C × BR × t<br/>(BR = 0.02 m³/min)"]
    PM --> CIG["Equivalent Cigarettes<br/>= PM2.5 / 22.0<br/>× (exposure_hours/24)"]
    PM --> RR["Relative Risk<br/>RR = 1.06 per 10 μg/m³"]

    DOSE --> SCORE["Health Score<br/>100 - (PM2.5/3)²"]
    RR --> SCORE

    SCORE --> LEVEL{"Risk Level"}
    LEVEL -->|"> 80"| LOW["Low Risk 🟢"]
    LEVEL -->|"60-80"| MOD["Moderate 🟡"]
    LEVEL -->|"40-60"| HIGH["High 🟠"]
    LEVEL -->|"20-40"| VHIGH["Very High 🔴"]
    LEVEL -->|"< 20"| HAZ["Hazardous ⛔"]

    CIG --> ADVISORY["Vulnerable Population<br/>Advisory"]

    style PM fill:#1e2538,stroke:#3b82f6,color:#f0f4f8
    style SCORE fill:#1e2538,stroke:#00d68f,color:#f0f4f8
```
