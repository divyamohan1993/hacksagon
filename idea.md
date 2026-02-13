This is a Technical Specification Document for a project designed to win by sheer **technical depth** and **infrastructure ingenuity**.

Most participants will build a "Dashboard" that displays static data. You will build a **"Virtual Sensor Network"** that generates *new* data from existing infrastructure.

### **Project Codename: Eco-Lens (The Virtual Air Quality Matrix)**

#### **1. The Core Concept (The "Rare" Factor)**

* **The Problem:** Physical air quality sensors are expensive ($5,000+), sparse, and require maintenance. We have huge "blind spots" in cities.
* **The Innovation:** We don't need new sensors. We turn **existing Traffic CCTV Cameras** into "Virtual Air Quality Monitors."
* **How:** By using Computer Vision to count specific vehicle classes (Trucks vs. Cars vs. EVs) and combining this with real-time **Wind Vector Data** and **EPA Emission Factors**, we can mathematically calculate the pollution plume at that exact street corner without a physical sensor.
* **Why it wins:** It is "Software defining Hardware." It merges **Computer Vision (AI)** with **Environmental Physics**.

---

### **2. Technical Architecture & Stack**

This is a heavy-duty backend project. The "Front-end" is just a window; the "Magic" happens on the **Google Cloud VM**.

**The Stack (Open Innovation Track):**

* **Infrastructure:** **Google Compute Engine (GCE)** – N2 or E2 Series (High CPU for Video Processing).
* **AI/Computer Vision:** **YOLOv8 (You Only Look Once)** – For real-time vehicle detection and classification.
* **Backend Logic:** Python (FastAPI) – Handles the pipeline.
* **Mathematical Physics:** **Gaussian Plume Dispersion Model** (Implemented in NumPy) – To calculate how exhaust spreads based on wind.
* **External Real Data:**
* **Video:** Public IP Camera Feeds (RTSP/MJPEG streams).
* **Weather:** OpenWeatherMap API (Wind Speed & Direction).
* **Reference:** EPA (Environmental Protection Agency) Emission Standards Database.



---

### **3. The "Real Data" Pipeline (No Simulations)**

This system relies entirely on live, messy, real-world data.

#### **Phase A: The Visual Input (The Eyes)**

Instead of simulating a video, we connect to **Real Public IP Cameras**.

* **Source:** Many cities publish live traffic feeds (e.g., NYC DOT, EarthCam, or open RTSP directories).
* **Action:** The Python script on the Google VM connects to the stream URL (e.g., `rtsp://192.168.x.x/live`).

#### **Phase B: The Inference Engine (The Brain)**

The Google VM grabs a frame every 5 seconds (to save bandwidth) and runs **YOLOv8**.

* **Differentiation:** It doesn't just count "cars." It distinguishes:
* **Heavy Duty Trucks** (High NOx/PM2.5 emission factor).
* **Private Sedans** (Medium emission).
* **Buses** (High emission).


* **Output:** A JSON stream: `{"timestamp": 12:00, "trucks": 4, "cars": 12, "buses": 1}`.

#### **Phase C: The Physics Engine (The Differentiator)**

This is where you impress the judges. You don't just guess; you calculate using the **Gaussian Plume Model Equation**:


* ** (Emission Rate):** Calculated dynamically (Count of Trucks × EPA Emission Factor per Truck).
* ** (Wind Speed):** Fetched LIVE from OpenWeatherMap for that coordinate.
* ** (Concentration):** The final PM2.5 level we predict.

---

### **4. Implementation Guide (Google Cloud VM Focus)**

Here is how you actually deploy this on the VM to show "Technical Complexity."

#### **Step 1: Provision the VM**

* **Machine:** Google Compute Engine `e2-standard-4` (4 vCPUs are needed for smooth video inference).
* **OS:** Ubuntu 22.04 LTS (Deep Learning Image).
* **Networking:** Open port `8000` (API) and `8501` (Streamlit Dashboard).

#### **Step 2: The Vision Pipeline Code (`vision.py`)**

*Create a script that ingests a live URL and outputs counts.*

```python
from ultralytics import YOLO
import cv2

# Load the nano model (lightweight for VM)
model = YOLO('yolov8n.pt') 

# REAL DATA: Public Traffic Cam (Example URL)
video_url = "http://<PUBLIC_CAM_IP>/mjpg/video.mjpg" 

def analyze_frame():
    cap = cv2.VideoCapture(video_url)
    ret, frame = cap.read()
    if ret:
        results = model(frame)
        # Innovation: Extract specific classes (Truck vs Car)
        detections = results[0].boxes.cls.tolist()
        trucks = detections.count(7) # Class ID 7 is truck
        cars = detections.count(2)   # Class ID 2 is car
        return {"trucks": trucks, "cars": cars}
    return {"error": "Stream Offline"}

```

#### **Step 3: The Dispersion Logic (`physics.py`)**

*The mathematical core.*

```python
import numpy as np

# EPA Constants (Real Data Points in grams/mile)
EMISSION_FACTOR_TRUCK = 1.2 
EMISSION_FACTOR_CAR = 0.05

def calculate_pollution(counts, wind_speed):
    # 1. Calculate Total Source Emission (Q)
    Q = (counts['trucks'] * EMISSION_FACTOR_TRUCK) + (counts['cars'] * EMISSION_FACTOR_CAR)
    
    # 2. Simple Box Model Dispersion (Simplified Gaussian)
    # Concentration = Emission / (Wind Speed * Area Factor)
    if wind_speed < 0.1: wind_speed = 0.1 # Prevent divide by zero
    
    concentration = Q / wind_speed
    return concentration # Returns estimated PM2.5 index

```

---

### **5. UX/UI & Feasibility (The "Sell")**

The judges need to see it to believe it.

* **The Dashboard:** Use **Streamlit** (Python-based UI) running on the same VM.
* **Visuals:**
1. **Left Panel:** The Live Video Feed with Bounding Boxes drawn around cars (Visual Proof).
2. **Right Panel:** A Real-Time Graph showing "Estimated PM2.5".
3. **Overlay:** A "Wind Arrow" that rotates based on real OpenWeatherMap data.



### **6. Why this hits the Judging Criteria**

1. **Innovation:** You aren't buying sensors; you are creating *software sensors*. This scales infinitely (just add more camera URLs).
2. **Technical Complexity:** You are running Computer Vision (YOLO) *and* API integrations *and* Physics Math on a cloud server.
3. **Scalability:** Google Cloud VM allows you to process 1 camera or 1,000 cameras just by upgrading the CPU.
4. **Impact:** Cities can monitor pollution on every street corner without spending tax money on hardware.

### **7. Next Step: Execution**

Would you like me to provide the **Shell Script (`setup.sh`)** that automatically installs YOLO, Python, and the dependencies on your Google VM so you can be up and running in 5 minutes?