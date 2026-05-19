# 🛰️ Landsat Land Cover Classification Web Application

**ECE 435: Remote Sensing Course Project**  
**Zagazig University - Faculty of Engineering | Batch 2026 | Group 8**

---

## 📋 Project Overview

A professional **web-based** application that automates the complete remote sensing image processing pipeline:

1. ✅ **Radiometric Calibration**: Convert raw Digital Number (DN) values to Top-of-Atmosphere (TOA) reflectance
2. ✅ **Spectral Indices Computation**: Calculate NDVI, NDWI, NDBI from calibrated bands
3. ✅ **Feature Stacking**: Combine B1-B7 + 3 indices = 10 features (2000×2000×10)
4. ✅ **ML Classification**: Apply pre-trained Random Forest model
5. ✅ **Statistics & Visualization**: Generate color-coded maps and area statistics

---

## 🎯 Features

- **Professional Web UI**: Modern, responsive interface
- **Automated Processing**: No manual ENVI or external software needed
- **Complete Pipeline**: From raw Landsat data to final classification
- **Real-time Progress**: Visual feedback during processing
- **CSV Export**: Download statistics for further analysis
- **High-quality Visualization**: 300 DPI classification maps

---

## 📥 Data Requirements

### Input Files (from USGS Earth Explorer)
Download your Landsat 8 scene from: [earthexplorer.usgs.gov](https://earthexplorer.usgs.gov/)

Required files:
- ✅ 7 Spectral Bands: `B1.TIF` - `B7.TIF` (GeoTIFF format)
- ✅ Metadata File: `*_MTL.txt` (contains calibration coefficients)

**Note**: While Landsat 8 provides 10 bands, this application uses B1-B7 calibrated to TOA reflectance, plus 3 computed spectral indices (NDVI, MNDWI, NDBI) for a total of 10 input features to the ML classifier.

### Pre-trained Model
- ✅ `Outputs/best_model.pkl` - Random Forest classifier trained on 4 land cover classes

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1: Install Dependencies

```bash
cd Code
pip install -r requirements.txt
```

### Step 2: Verify Project Structure

```
8_ECE435_Project_2026/
├── Code/
│   ├── app.py                      # Flask backend
│   ├── requirements.txt            # Python dependencies
│   ├── templates/
│   │   └── index.html             # Web interface
│   ├── static/
│   │   ├── style.css              # Styling
│   │   └── script.js              # Frontend logic
│   ├── Model_Training/
│   │   └── main.py                # Model training script
│   └── Model_Testing/
│       └── predict_new_image.py   # Single image prediction
├── Data/
│   └── Labeled_ROI.csv            # Training dataset
├── Outputs/
│   └── best_model.pkl            # Pre-trained model
└── uploads/                       # Temporary upload folder (auto-created)
```

### Step 3: Run the Application

```bash
python app.py
```

**Expected Output:**
```
============================================================
ECE 435 Remote Sensing - Web Application
Starting Flask Server...
============================================================

 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

### Step 4: Access the Web Interface

Open your browser and navigate to:
```
http://localhost:5000
```

---

## 📖 How to Use

### 1. Download Landsat Data

1. Go to [USGS Earth Explorer](https://earthexplorer.usgs.gov/)
2. Search for your area of interest
3. Select a Landsat 8 scene
4. Download the dataset (Collection 2, Level-1)
5. Unzip the downloaded file

You'll have files like:
```
LC08_L1TP_177039_20250811_20250821_02_T1_B1.TIF
LC08_L1TP_177039_20250811_20250821_02_T1_B2.TIF
...
LC08_L1TP_177039_20250811_20250821_02_T1_MTL.txt
```

### 2. Upload to Web App

1. **Select Bands**: Click on each band input and select the corresponding TIF file (B1-B7 in order)
2. **Select Metadata**: Choose the `*_MTL.txt` file
3. **Define Crop Window**: Enter row/column start and end indices (default: 1000-3000 for both)
4. **Process**: Click "🚀 Process Image"

### 3. View Results

- ✅ Real-time progress updates
- ✅ Classification map visualization
- ✅ Area statistics table
- ✅ Download CSV report

---

## 🔧 Processing Pipeline Details

### Step 1: Parse Metadata
```
Extract from MTL.txt:
- RADIANCE_MULT_BAND_X (ML)
- RADIANCE_ADD_BAND_X (AL)
- REFLECTANCE_MULT_BAND_X (MR)
- REFLECTANCE_ADD_BAND_X (AR)
- SUN_ELEVATION
- EARTH_SUN_DISTANCE
```

### Step 2: Radiometric Calibration
```
DN → Radiance: L = ML × DN + AL
Radiance → TOA Reflectance: ρ = MR × L + AR
```

### Step 3: Spectral Indices
```
NDVI = (B5 - B4) / (B5 + B4)      # Vegetation index
NDWI = (B5 - B6) / (B5 + B6)      # Water index
NDBI = (B6 - B5) / (B6 + B5)      # Built-up index
```

Where:
- B4 = Red band
- B5 = Near-infrared (NIR)
- B6 = Shortwave-infrared 1 (SWIR1)

### Step 4: Feature Stacking
```
Final Feature Array: [B1, B2, B3, B4, B5, B6, B7, NDVI, NDWI, NDBI]
Shape: 2000 × 2000 × 10 features
```

### Step 5: Classification
- **Model**: Random Forest Classifier
- **Training Data**: 133,201 labeled pixels (4 classes)
- **Test Accuracy**: ~92%+ (from main.py)
- **Classes**:
  - 🔵 Water
  - 🟢 Vegetation
  - 🔴 Urban
  - 🟡 Desert

### Step 6: Statistics Computation
```
Area = Pixel Count × (30m)² / 1,000,000
```

---

## 📊 Output Files

Results are saved to `Outputs/{session_id}/`:

1. **classified_map.png**
   - 300 DPI color-coded classification map
   - Color legend: Blue (Water), Green (Vegetation), Red (Urban), Yellow (Desert)

2. **statistics.csv**
   - Class names
   - Pixel counts
   - Area in km²
   - Downloadable from web interface

---

## 🐛 Troubleshooting

### Issue: "Trained model not found"
**Solution**: Ensure `Outputs/best_model.pkl` exists. Run `Model_Training/main.py` first.

### Issue: "Missing band files"
**Solution**: Select all 10 bands (B1-B10) in the correct order.

### Issue: "Failed to parse MTL file"
**Solution**: 
- Verify the MTL file is from Landsat 8 (L1TP level)
- Ensure the file is not corrupted

### Issue: Port 5000 already in use
**Solution**: Modify `app.py` line:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Change to 5001
```

### Issue: Large file upload timeout
**Solution**: Increase timeout in your web server configuration or split the upload.

---

## 📚 Technical Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Flask 2.0+ |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Data Processing** | NumPy, Pandas, Rasterio |
| **Machine Learning** | Scikit-learn (Random Forest) |
| **Visualization** | Matplotlib |

---

## 📈 Performance

- **Processing Time**: ~30-60 seconds per scene (depending on hardware)
- **Memory Usage**: ~500 MB for typical 2000×2000 scenes
- **Output Accuracy**: ~92-95% land cover classification

---

## 🎓 Project Structure

```
8_ECE435_Project_2026/
├── Code/
│   ├── app.py                          # Main Flask application (Phase 3)
│   ├── config.py                       # Flask configuration
│   ├── requirements.txt                # Python package dependencies
│   ├── templates/
│   │   └── index.html                 # Web interface (HTML5)
│   ├── static/
│   │   ├── style.css                  # Styling (CSS3)
│   │   └── script.js                  # Frontend logic (Vanilla JS)
│   ├── Model_Training/
│   │   └── main.py                    # Phase 1: Train 6 classifiers, save best
│   └── Model_Testing/
│       └── predict_new_image.py       # Phase 2: Single image inference (legacy)
├── Data/
│   └── Labeled_ROI.csv                # Training dataset (133,201 labeled pixels)
├── Outputs/
│   └── best_model.pkl                 # Pre-trained Random Forest model
├── Documentation/
├── README.md                           # Main documentation
├── QUICK_START.md                      # Quick start guide
├── START_HERE.md                       # First-time setup
└── uploads/                            # Temporary session folders (auto-created)
```

---

## 📝 Notes

- The application automatically handles missing or nodata pixels
- Results are organized by session ID (timestamp) for easy tracking
- Each session folder contains both the map image and statistics CSV
- The model was trained on 133,201 labeled pixels from 4 land cover classes

---

## 👥 Group Information

**ECE 435: Remote Sensing Course**  
**Zagazig University - Faculty of Engineering**  
**Batch 2026 | Group 8**

### Team Members:
- **Islam Ramadan** 
- **Hazem Nasr**
- **Yahia Mohamed**
- **Hassan Maher**
- **Ahmed Hany**
- **Osama Ashraf**
- **Mohamed Elsayed**

---

## 📄 License

Academic Project - Zagazig University

---

## 🔗 References

- [Landsat 8 Bands](https://www.usgs.gov/faqs/what-are-band-designations-landsat-satellites)
- [USGS Earth Explorer](https://earthexplorer.usgs.gov/)
- [Scikit-learn Documentation](https://scikit-learn.org/)
- [Rasterio Documentation](https://rasterio.readthedocs.io/)

---

**Last Updated**: May 17, 2026  
**Version**: 1.0 - Production Ready
