# 🚀 QUICK START GUIDE

## For Windows Users 🪟

### Step 1: Install Python
1. Download Python 3.8+ from [python.org](https://www.python.org)
2. During installation, **check** ✓ "Add Python to PATH"
3. Click "Install Now"

### Step 2: Run the Application
1. Double-click **`run.bat`** in the project folder
2. Wait for dependencies to install
3. Open your browser and go to: **http://localhost:5000**

---

## For Mac/Linux Users 🍎🐧

### Step 1: Install Python
```bash
# macOS with Homebrew
brew install python3

# Ubuntu/Debian
sudo apt-get install python3 python3-pip

# Fedora
sudo dnf install python3 python3-pip
```

### Step 2: Run the Application
```bash
chmod +x run.sh
./run.sh
```

Then open your browser to: **http://localhost:5000**

---

## For Command Line Users 💻

### Step 1: Navigate to Project
```bash
cd "path/to/8_ECE435_Project_2026"
cd Code
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run Flask Server
```bash
python app.py
```

### Step 5: Open Browser
Navigate to: **http://localhost:5000**

---

## 📊 Using the Application

### 1. Download Landsat Data

Visit [USGS Earth Explorer](https://earthexplorer.usgs.gov/)

Steps:
- Search for your area of interest
- Select a **Landsat 8** scene (Collection 2, Level-1)
- Add to cart → Download
- Download the dataset (GeoTIFF format)
- Unzip the file

You'll have files like:
```
LC08_L1TP_177039_20250811_20250821_02_T1_B1.TIF
LC08_L1TP_177039_20250811_20250821_02_T1_B2.TIF
... (B3 through B10)
LC08_L1TP_177039_20250811_20250821_02_T1_MTL.txt
```

### 2. Upload to Web App

1. **Select Spectral Bands** (10 files)
   - Click each band input
   - Select B1.TIF, B2.TIF, ... B10.TIF **in order**

2. **Select Metadata File**
   - Click "📄 Click to select MTL.txt"
   - Choose the *_MTL.txt file

3. **Process Image**
   - Click "🚀 Process Image"
   - Wait for processing (30-60 seconds)

### 3. View Results

- ✅ **Classification Map**: Color-coded land cover map
- ✅ **Statistics Table**: 
  - Water, Vegetation, Urban, Desert
  - Pixel counts and area in km²
  - Percentage of total area

- ✅ **Download CSV**: Export statistics for reports

---

## 🎨 What the App Does

| Step | Process | Details |
|------|---------|---------|
| 1️⃣ | **Parse Metadata** | Reads calibration coefficients from MTL.txt |
| 2️⃣ | **Calibration** | Converts raw DN → Top-of-Atmosphere reflectance |
| 3️⃣ | **Indices** | Computes NDVI, NDWI, NDBI |
| 4️⃣ | **Stacking** | Combines B1-B7 + 3 indices = 10 features |
| 5️⃣ | **Classification** | Applies trained Random Forest model |
| 6️⃣ | **Statistics** | Calculates area per land cover class |

---

## 🎯 Expected Output

### Classification Map
```
Legend:
🔵 Blue   = Water (lakes, rivers)
🟢 Green  = Vegetation (forests, agriculture)
🔴 Red    = Urban (buildings, roads)
🟡 Yellow = Desert (bare soil, sand)
```

### Example Statistics
```
Class Name     | Pixel Count | Area (km²) | %
Water          | 180,100     | 162.09    | 4.5%
Vegetation     | 1,055,257   | 949.73    | 26.4%
Urban          | 1,396,136   | 1,256.52  | 34.9%
Desert         | 1,106,795   | 996.12    | 27.7%
─────────────────────────────────────────────
TOTAL          | 4,000,000   | 3,600.00  | 100%
```

---

## ⚠️ Troubleshooting

### Port 5000 Already in Use
**Error**: `Address already in use`

**Fix**: Stop other Flask apps or modify port in `Code/app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change to 5001
```

### Model Not Found
**Error**: `Trained model not found`

**Fix**: Run training first:
```bash
python Code/Model_Training/main.py
```

### Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'flask'`

**Fix**: Install requirements:
```bash
pip install -r Code/requirements.txt
```

### File Upload Failed
**Error**: `File too large` or timeout

**Solution**: 
- Ensure all band files are present
- Check file sizes (each ~30-50 MB)
- Use a stable internet connection

### Browser Shows Blank Page
**Fix**:
1. Check console (F12 → Console tab)
2. Refresh page (Ctrl+F5)
3. Try different browser
4. Check Flask server is running (terminal should show Flask logs)

---

## 📚 File Naming Convention

When downloading from USGS, you'll get:

```
LC08_L1TP_{PATH}_{ROW}_{DATE}_{PROCESSING_DATE}_{COLLECTION}_{TIER}_
├── B1.TIF           (Coastal)
├── B2.TIF           (Blue)
├── B3.TIF           (Green)
├── B4.TIF           (Red)
├── B5.TIF           (NIR)
├── B6.TIF           (SWIR1)
├── B7.TIF           (SWIR2)
├── B8.TIF           (Panchromatic)
├── B9.TIF           (Cirrus)
├── B10.TIF          (Thermal IR)
└── MTL.txt          (Metadata)
```

---

## 🔒 Important Notes

- ✅ All processing happens on your computer
- ✅ No data is sent to external servers
- ✅ Results are saved locally in `Outputs/` folder
- ✅ Each session gets a unique timestamp folder
- ✅ Downloads are automatic (no manual CSV creation needed)

---

## 📞 Need Help?

1. **Check README.md** - Comprehensive documentation
2. **Review TECHNICAL_DOCS.md** - Formulas and details
3. **Run test suite** - Verify setup:
   ```bash
   python test_suite.py
   ```

---

## 🎓 Educational Resources

- [USGS Landsat Bands](https://www.usgs.gov/faqs/what-are-band-designations-landsat-satellites)
- [Remote Sensing Indices](https://www.indexdatabase.de/)
- [Scikit-learn Random Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)

---

**Version**: 1.0 Production Ready  
**Last Updated**: May 17, 2026  
**Group**: ECE 435 - Batch 8
