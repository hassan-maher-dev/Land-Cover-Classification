# 📚 Technical Documentation

## Radiometric Calibration Formula

### Digital Number to Radiance
```
L_λ = ML × Q_cal + AL

Where:
- L_λ     = Spectral radiance (W/(m² × sr × μm))
- ML      = RADIANCE_MULT_BAND_X (from MTL.txt)
- Q_cal   = Digital number (DN) value [0-65535]
- AL      = RADIANCE_ADD_BAND_X (from MTL.txt)
```

### Radiance to TOA Reflectance
```
ρ_λ = MR × L_λ + AR

Where:
- ρ_λ    = TOA reflectance (unitless, 0-1)
- MR     = REFLECTANCE_MULT_BAND_X (from MTL.txt)
- L_λ    = Spectral radiance
- AR     = REFLECTANCE_ADD_BAND_X (from MTL.txt)
```

## Spectral Indices

### Normalized Difference Vegetation Index (NDVI)
```
NDVI = (B5 - B4) / (B5 + B4)

Where:
- B4 = Red band (650-680 nm)
- B5 = Near-Infrared / NIR (845-885 nm)

Range: [-1, 1]
- NDVI < 0.2: Non-vegetation
- NDVI 0.2-0.4: Low vegetation
- NDVI 0.4-0.6: Moderate vegetation
- NDVI > 0.6: Dense vegetation
```

### Normalized Difference Water Index (NDWI)
```
NDWI = (B5 - B6) / (B5 + B6)

Where:
- B5 = Near-Infrared / NIR (845-885 nm)
- B6 = Shortwave-Infrared 1 / SWIR1 (1560-1660 nm)

Range: [-1, 1]
- NDWI > 0.5: Water bodies
- NDWI 0.3-0.5: Vegetation with water
- NDWI < 0.3: No water or vegetation
```

### Normalized Difference Built-up Index (NDBI)
```
NDBI = (B6 - B5) / (B6 + B5)

Where:
- B6 = Shortwave-Infrared 1 / SWIR1 (1560-1660 nm)
- B5 = Near-Infrared / NIR (845-885 nm)

Range: [-1, 1]
- NDBI > 0.1: Built-up areas
- NDBI 0-0.1: Barren/desert areas
- NDBI < 0: Vegetation
```

## Landsat 8 Band Mapping

| Band | Name | Wavelength | Resolution | Purpose |
|------|------|-----------|-----------|---------|
| B1 | Coastal/Aerosol | 0.43 - 0.45 μm | 30m | Atmospheric correction |
| B2 | Blue | 0.45 - 0.51 μm | 30m | Water penetration |
| B3 | Green | 0.53 - 0.59 μm | 30m | Vegetation analysis |
| B4 | Red | 0.64 - 0.67 μm | 30m | NDVI calculation |
| B5 | NIR | 0.85 - 0.88 μm | 30m | Vegetation vigor |
| B6 | SWIR1 | 1.57 - 1.65 μm | 30m | Moisture content |
| B7 | SWIR2 | 2.11 - 2.29 μm | 30m | Built-up areas |
| B8 | Panchromatic | 0.50 - 0.68 μm | 15m | Pan-sharpening |
| B9 | Cirrus | 1.36 - 1.38 μm | 30m | Cloud detection |
| B10 | Thermal IR 1 | 10.60 - 11.19 μm | 100m | Temperature |

## MTL File Structure

```ini
GROUP = LANDSAT_METADATA_FILE
  GROUP = LEVEL1_RADIOMETRIC_RESCALING
    RADIANCE_MULT_BAND_1 = 1.2225E-02
    RADIANCE_ADD_BAND_1 = -61.12637
    REFLECTANCE_MULT_BAND_1 = 2.0000E-05
    REFLECTANCE_ADD_BAND_1 = -0.100000
    ...
  END_GROUP
END_GROUP
```

## Feature Stack Generation

```
Input:  10 Landsat 8 bands (B1-B10) at 2000×2000 pixels
        ↓
Step 1: Calibrate B1-B10 to TOA reflectance
        ↓
Step 2: Extract B1-B7 (7 bands)
        ↓
Step 3: Compute 3 spectral indices (NDVI, NDWI, NDBI)
        ↓
Step 4: Stack: [B1, B2, B3, B4, B5, B6, B7, NDVI, NDWI, NDBI]
        ↓
Output: Feature array (10, 2000, 2000)
        Reshaped to (4,000,000, 10) for classification
```

## Classification Model

- **Algorithm**: Random Forest Classifier
- **Training Data**: 133,201 labeled pixels
- **Classes**: 4 (Water, Vegetation, Urban, Desert)
- **Features**: 10 (B1-B7 + NDVI/NDWI/NDBI)
- **Hyperparameters**: 
  - n_estimators: 100
  - random_state: 42
- **Expected Accuracy**: ~92-95%

## Area Calculation

```
Pixel Area = 30m × 30m = 900 m²
Total Area = Pixel Count × 900 m²
Area (km²) = Total Area / 1,000,000

Example:
- 1,000,000 pixels = 900,000,000 m² = 900 km²
```

## Error Handling

### File Validation
- ✓ All 10 band files must be present
- ✓ MTL file must be valid Landsat 8 L1TP format
- ✓ Maximum file size: 500 MB

### Data Validation
- ✓ DN values: 0-65535 (UINT16)
- ✓ Reflectance values: 0-1 (clipped)
- ✓ Nodata pixels: Handled gracefully

## Performance Metrics

- **Processing Time**: 30-60 seconds per 2000×2000 scene
- **Memory Usage**: ~500-800 MB
- **Output Disk Space**: ~10-20 MB per result
- **Network Bandwidth**: ~100-500 MB upload (scene dependent)

## Browser Compatibility

- ✓ Chrome/Chromium (64+)
- ✓ Firefox (60+)
- ✓ Safari (12+)
- ✓ Edge (79+)

## API Endpoints

### Process Image
```
POST /api/process
Content-Type: multipart/form-data

Parameters:
- bands (file): 10 band TIF files
- mtl (file): MTL metadata file

Response:
{
  "success": true,
  "session_id": "20260517_143022",
  "map_image": "data:image/png;base64,...",
  "statistics": {
    "Water": {"pixel_count": 180100, "area_km2": 162.09},
    "Vegetation": {"pixel_count": 1055257, "area_km2": 949.73},
    "Urban": {"pixel_count": 1396136, "area_km2": 1256.52},
    "Desert": {"pixel_count": 1106795, "area_km2": 996.12}
  },
  "csv_download": "/api/download/20260517_143022/statistics.csv"
}
```

### Download Results
```
GET /api/download/{session_id}/{filename}

Parameters:
- session_id: Unique session identifier
- filename: "statistics.csv"

Response: Binary file download
```

## Logging & Debugging

The application logs detailed information to the console:

```
[INFO] Loading spectral training data from CSV...
[PROCESS] Training Classifier: Random Forest...
[SUCCESS] Model loaded: RandomForestClassifier
[RUNNING] Running spatial mapping classification cells...
[SUCCESS] Processing complete!
```

## Future Enhancements

- [ ] Batch processing (multiple scenes)
- [ ] Support for Sentinel-2 data
- [ ] Advanced classification algorithms (SVM, Deep Learning)
- [ ] Interactive web-based map viewer
- [ ] Real-time streaming processing
- [ ] Multi-language support (Arabic, English)
- [ ] Machine learning model versioning
- [ ] Accuracy assessment tool
- [ ] Spectral curve plotting
- [ ] Change detection analysis

---

**Version**: 1.0  
**Last Updated**: May 17, 2026  
**Developed by**: ECE 435 Remote Sensing - Group 8
