"""
ECE 435: Remote Sensing - Web Application
Phase 3: Professional Web Interface with Complete Processing Pipeline
Zagazig University - Faculty of Engineering (Batch 2026)
Group: 8
"""

import os
import pickle
import re
import numpy as np
import pandas as pd
import rasterio
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import io
import base64
from pathlib import Path
from config import get_config

TARGET_HEIGHT = 2000
TARGET_WIDTH = 2000
REFLECTANCE_SCALE = 10000.0
FIXED_ROW_START = 1000
FIXED_ROW_END = 3000
FIXED_COL_START = 1000
FIXED_COL_END = 3000

# Initialize Flask app with configuration
app = Flask(__name__)
config = get_config(os.environ.get('FLASK_ENV', 'development'))
app.config.from_object(config)

# Create folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

print(f"[CONFIG] Running in {os.environ.get('FLASK_ENV', 'development')} mode")
print(f"[CONFIG] Upload folder: {app.config['UPLOAD_FOLDER']}")
print(f"[CONFIG] Output folder: {app.config['OUTPUT_FOLDER']}")

# =========================================================================
# UTILITY FUNCTIONS
# =========================================================================

def parse_mtl_file(mtl_path):
    """Parse Landsat MTL metadata file and extract calibration coefficients."""
    metadata = {}
    
    try:
        with open(mtl_path, 'r') as f:
            content = f.read()
        
        # Extract radiometric rescaling coefficients for reflective bands (B1-B9)
        for band in range(1, 10):
            mult_key = f"RADIANCE_MULT_BAND_{band}"
            add_key = f"RADIANCE_ADD_BAND_{band}"
            
            mult_match = re.search(f"{mult_key}\\s*=\\s*([0-9.E+-]+)", content)
            add_match = re.search(f"{add_key}\\s*=\\s*([0-9.E+-]+)", content)
            
            if mult_match and add_match:
                metadata[f'ML_{band}'] = float(mult_match.group(1))
                metadata[f'AL_{band}'] = float(add_match.group(1))
        
        # Extract reflectance rescaling coefficients
        for band in range(1, 9):
            mult_key = f"REFLECTANCE_MULT_BAND_{band}"
            add_key = f"REFLECTANCE_ADD_BAND_{band}"
            
            mult_match = re.search(f"{mult_key}\\s*=\\s*([0-9.E+-]+)", content)
            add_match = re.search(f"{add_key}\\s*=\\s*([0-9.E+-]+)", content)
            
            if mult_match and add_match:
                metadata[f'MR_{band}'] = float(mult_match.group(1))
                metadata[f'AR_{band}'] = float(add_match.group(1))
        
        # Extract sun elevation
        sun_elev_match = re.search(r"SUN_ELEVATION\s*=\s*([0-9.E+-]+)", content)
        if sun_elev_match:
            metadata['SUN_ELEVATION'] = float(sun_elev_match.group(1))
        
        # Extract earth-sun distance
        esd_match = re.search(r"EARTH_SUN_DISTANCE\s*=\s*([0-9.E+-]+)", content)
        if esd_match:
            metadata['EARTH_SUN_DISTANCE'] = float(esd_match.group(1))
        
        return metadata
    
    except Exception as e:
        print(f"[ERROR] Failed to parse MTL file: {str(e)}")
        return None

def calibrate_to_toa(dn_value, ml, al, mr, ar, sun_elevation=None):
    """
    Convert Digital Number (DN) to TOA reflectance using Landsat calibration coefficients.

    Step 1: DN -> Radiance (for debug / intermediate verification)
    Step 2: DN -> TOA Reflectance using reflectance coefficients
    Step 3: Apply sun elevation correction if available
    """
    # Step 1: DN to Radiance (intermediate diagnostic)
    radiance = ml * dn_value + al

    # Step 2: DN to Planetary Reflectance (before sun-angle correction)
    toa_reflectance = mr * dn_value + ar

    # Step 3: Correct for sun elevation if provided
    if sun_elevation is not None:
        toa_reflectance = toa_reflectance / np.sin(np.deg2rad(sun_elevation))

    # Clamp to valid range [0, 1]
    toa_reflectance = np.clip(toa_reflectance, 0, 1)

    return toa_reflectance


def validate_crop_window(row_start, row_end, col_start, col_end):
    """Validate the requested crop window and enforce 2000x2000 pixels."""
    if row_start < 0 or col_start < 0:
        raise ValueError("Crop window must use non-negative pixel indices.")
    if row_end <= row_start or col_end <= col_start:
        raise ValueError("Crop window end indices must be greater than start indices.")
    if (row_end - row_start) != TARGET_HEIGHT or (col_end - col_start) != TARGET_WIDTH:
        raise ValueError(
            f"Crop window must be exactly {TARGET_HEIGHT}x{TARGET_WIDTH} pixels. "
            f"Received {row_end - row_start}x{col_end - col_start}."
        )


def crop_to_target(image, row_start, row_end, col_start, col_end):
    """Crop a band image to the requested subset window. Parameters are required (no defaults)."""
    height, width = image.shape
    validate_crop_window(row_start, row_end, col_start, col_end)

    if row_end > height or col_end > width:
        raise ValueError(
            f"Requested crop window {row_start}:{row_end}, {col_start}:{col_end} "
            f"does not fit inside image size ({height}, {width})."
        )

    cropped = image[row_start:row_end, col_start:col_end]
    print(f"[INFO] Cropped band from ({height}, {width}) to {cropped.shape} using subset rows "
          f"{row_start}-{row_end} cols {col_start}-{col_end}")
    return cropped


def scale_reflectance_bands(bands_array, scale=REFLECTANCE_SCALE):
    """
    Perform Atmospheric Correction via Dark Object Subtraction (DOS1)
    to match ENVI FLAASH Surface Reflectance training data, then scale.
    """
    print(f"[STEP] Atmospheric Calibration (DOS + Scaling by {scale})...")
    corrected_bands = np.zeros_like(bands_array)
    
    for i in range(7):
        band = bands_array[i]
        # تجاهل البيكسلات السوداء (Nodata) أثناء الحساب
        valid_mask = band > 0
        if np.any(valid_mask):
            # إيجاد قيمة البيكسل المظلم (Path Radiance) باستخدام الـ 1st percentile لضمان الدقة
            dark_pixel = np.percentile(band[valid_mask], 1)
            print(f"  [DEBUG] Band {i+1} Dark Pixel Value subtracted: {dark_pixel:.4f}")
            
            # طرح تأثير الغلاف الجوي من الباند بالكامل
            band_dos = band - dark_pixel
            
            # منع وجود قيم انعكاس بالسالب
            band_dos = np.clip(band_dos, 0, 1)
            corrected_bands[i] = band_dos
        else:
            corrected_bands[i] = band
            
    scaled = corrected_bands * scale
    print(f"[SUCCESS] DOS applied and Reflectance scaled. Range: [{scaled.min():.1f}, {scaled.max():.1f}]")
    return scaled


def apply_nodata_mask(bands_array):
    """
    Create a nodata mask for the bands. Pixels with all zeros are considered nodata.
    Returns the mask (True = valid data, False = nodata).
    """
    print("[STEP] Applying nodata mask...")
    # If all bands are 0 at same pixel, mark as nodata
    mask = ~(np.sum(bands_array, axis=0) == 0)
    num_valid = np.sum(mask)
    num_nodata = mask.size - num_valid
    print(f"  [INFO] Valid pixels: {num_valid}, Nodata pixels: {num_nodata}")
    return mask


def load_and_calibrate_bands(band_paths, mtl_metadata, row_start, row_end, col_start, col_end):
    """Load the first 7 bands and calibrate them to TOA reflectance (required crop parameters)."""
    bands = []
    expected_shape = None
    
    for band_idx in range(1, 8):
        band_path = band_paths.get(band_idx)
        if not band_path or not os.path.exists(band_path):
            raise FileNotFoundError(f"Band {band_idx} file not found: {band_path}")
        
        print(f"[INFO] Loading and calibrating Band {band_idx}...")
        
        with rasterio.open(band_path) as src:
            print(f"  [DEBUG] File shape: {src.shape}, Count (bands): {src.count}")
            dn_data = src.read(1).astype(np.float32)
            print(f"  [DEBUG] DN range (raw): [{dn_data.min():.1f}, {dn_data.max():.1f}]")
        
        # Get calibration coefficients
        ml = mtl_metadata.get(f'ML_{band_idx}')
        al = mtl_metadata.get(f'AL_{band_idx}')
        mr = mtl_metadata.get(f'MR_{band_idx}')
        ar = mtl_metadata.get(f'AR_{band_idx}')
        
        if ml is None or al is None or mr is None or ar is None:
            raise ValueError(f"Missing calibration coefficients for Band {band_idx}")
        
        print(f"  [DEBUG] Coefficients - ML:{ml:.6f}, AL:{al:.6f}, MR:{mr:.6f}, AR:{ar:.6f}")
        
        # Calibrate to TOA reflectance
        sun_elevation = mtl_metadata.get('SUN_ELEVATION')
        toa_band = calibrate_to_toa(dn_data, ml, al, mr, ar, sun_elevation=sun_elevation)
        print(f"  [DEBUG] TOA range (before crop): [{toa_band.min():.3f}, {toa_band.max():.3f}]")
        
        if expected_shape is None:
            expected_shape = toa_band.shape
        elif toa_band.shape != expected_shape:
            raise ValueError(
                f"Band dimensions are inconsistent across inputs: expected {expected_shape}, "
                f"got {toa_band.shape} for Band {band_idx}"
            )
        
        # Crop to the requested subset window for model compatibility
        toa_band = crop_to_target(toa_band, row_start=row_start, row_end=row_end, col_start=col_start, col_end=col_end)
        print(f"  [DEBUG] TOA range (after crop): [{toa_band.min():.3f}, {toa_band.max():.3f}]")
        bands.append(toa_band)
    
    bands_array = np.array(bands)
    return bands_array


def compute_spectral_indices(bands_array):
    print("[STEP] Computing Spectral Indices (NDVI, MNDWI, NDBI)...")
    
    B3 = bands_array[2]  # Green
    B4 = bands_array[3]  # Red
    B5 = bands_array[4]  # NIR
    B6 = bands_array[5]  # SWIR1
    
    # 1. NDVI (Feature 8 in CSV)
    print("  [COMPUTING] NDVI...")
    ndvi = (B5 - B4) / (B5 + B4 + 1e-8)
    ndvi = np.clip(ndvi, -1, 1)
    
    # 2. MNDWI - Modified NDWI (Feature 9 in CSV)
    print("  [COMPUTING] MNDWI...") 
    mndwi = (B3 - B6) / (B3 + B6 + 1e-8)
    mndwi = np.clip(mndwi, -1, 1)
    
    # 3. NDBI (Feature 10 in CSV)
    print("  [COMPUTING] NDBI...")
    ndbi = (B6 - B5) / (B6 + B5 + 1e-8)
    ndbi = np.clip(ndbi, -1, 1)
    
    return ndvi, mndwi, ndbi

def create_feature_stack(bands_array, ndvi, mndwi, ndbi):
    print("[STEP] Layer Stacking (B1-B7 + NDVI/MNDWI/NDBI)...")
    
    b1_to_b7 = bands_array[:7]
    
    feature_stack = np.vstack([
        b1_to_b7,
        ndvi[np.newaxis, :, :],   # Band 8
        mndwi[np.newaxis, :, :],  # Band 9
        ndbi[np.newaxis, :, :]    # Band 10
    ])
    
    print(f"[SUCCESS] Feature stack created with shape: {feature_stack.shape}")
    return feature_stack

def classify_image(feature_stack, model):
    """Apply trained model to feature stack for classification."""
    print("[INFO] Applying trained model for classification...")
    
    height, width = feature_stack.shape[1], feature_stack.shape[2]
    
    # Reshape to (num_pixels, num_features)
    features_reshaped = feature_stack.reshape(10, -1).T  # (height*width, 10)
    
    # Debug: Print feature ranges
    print(f"[DEBUG] Feature ranges in input to model:")
    for i in range(10):
        print(f"  Feature {i}: [{features_reshaped[:, i].min():.2f}, {features_reshaped[:, i].max():.2f}] (mean: {features_reshaped[:, i].mean():.2f})")
    
    # Predict
    predictions = model.predict(features_reshaped)
    
    # Debug: Print prediction distribution
    unique_preds, counts = np.unique(predictions, return_counts=True)
    print(f"[DEBUG] Prediction distribution:")
    for pred, count in zip(unique_preds, counts):
        print(f"  {pred}: {count} pixels ({100*count/len(predictions):.2f}%)")
    
    # Reshape back to image
    classification_map = np.zeros((height, width), dtype=np.int32)
    
    # Use class mapping from config
    class_mapping = {name: idx for idx, name in app.config['CLASS_NAMES'].items()}
    
    for idx, label in enumerate(predictions):
        classification_map[idx // width, idx % width] = class_mapping.get(label, 0)
    
    print("[SUCCESS] Classification complete!")
    return classification_map

def compute_statistics(classification_map):
    """Compute area statistics for each class."""
    print("[INFO] Computing area statistics...")
    
    unique, counts = np.unique(classification_map, return_counts=True)
    stats = {}
    
    # Get class names from config
    class_names = app.config['CLASS_NAMES']
    pixel_size_m2 = app.config['PIXEL_AREA_M2']
    
    stats_list = []
    for class_id, count in zip(unique, counts):
        if class_id in class_names:
            class_name = class_names[class_id]
            area_km2 = (count * pixel_size_m2) / 1e6
            stats[class_name] = {
                'pixel_count': int(count),
                'area_km2': round(area_km2, 2)
            }
            stats_list.append({
                'Class Name': class_name,
                'Pixel Count': int(count),
                'Area (km²)': round(area_km2, 2)
            })
    
    print("[SUCCESS] Statistics computed!")
    return stats, pd.DataFrame(stats_list)

def visualize_classification(classification_map, output_path):
    """Create and save colored classification map."""
    print("[INFO] Creating visualization...")
    
    # الحصول على الألوان من الـ Config وإضافة الأبيض للحواف
    colors_list = [app.config['CLASS_COLORS'][i] for i in range(4)]
    colors_list.append('#FFFFFF')  # كود 4 = Nodata (أبيض)
    
    class_names = app.config['CLASS_NAMES']
    
    custom_cmap = mcolors.ListedColormap(colors_list)
    
    # تعديل vmax لـ 4 عشان يشمل اللون الأبيض بتاع الحواف
    fig, ax = plt.subplots(figsize=(12, 10), dpi=100)
    im = ax.imshow(classification_map, cmap=custom_cmap, vmin=0, vmax=4)
    
    # رسم مفتاح الخريطة (Legend) للكلاسات الأربعة الأساسية فقط
    patches = [plt.plot([], [], marker="s", ms=12, ls="", mec=None, 
                        color=colors_list[i], label=class_names[i])[0] for i in range(4)]
    
    ax.legend(handles=patches, loc='lower right', fontsize=11, framealpha=0.95)
    ax.set_title("Land Cover Classification Map", fontsize=14, fontweight='bold', pad=15)
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] Classification map saved to: {output_path}")

# =========================================================================
# FLASK ROUTES
# =========================================================================

@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')

@app.route('/api/process', methods=['POST'])
def process_image():
    """
    Process uploaded Landsat image with complete pipeline.
    Expects: 7 band files (B1-B7) + MTL metadata file
    """
    try:
        # Get uploaded files
        uploaded_files = request.files.getlist('bands')
        mtl_file = request.files.get('mtl')
        
        if not uploaded_files or not mtl_file:
            return jsonify({'error': 'Missing band files or MTL file'}), 400
        
        if len(uploaded_files) != 7:
            return jsonify({'error': f'Expected 7 band files, got {len(uploaded_files)}'}), 400
        
        # Create session folder
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_folder = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        os.makedirs(session_folder, exist_ok=True)
        
        print(f"\n{'='*60}")
        print(f"[NEW SESSION] {session_id}")
        print(f"{'='*60}")
        
        # Save uploaded files
        band_paths = {}
        for idx, band_file in enumerate(uploaded_files, 1):
            filename = secure_filename(f"B{idx}.TIF")
            filepath = os.path.join(session_folder, filename)
            band_file.save(filepath)
            band_paths[idx] = filepath
            print(f"[SAVED] Band {idx}: {filename}")
        
        mtl_path = os.path.join(session_folder, 'metadata.txt')
        mtl_file.save(mtl_path)
        print(f"[SAVED] MTL metadata file")
        
        # ============================================================
        # STEP 1: Parse MTL and extract calibration coefficients
        # ============================================================
        print("\n[STEP 1] Parsing MTL metadata...")
        mtl_metadata = parse_mtl_file(mtl_path)
        if not mtl_metadata:
            return jsonify({'error': 'Failed to parse MTL file'}), 400
        
        print("[SUCCESS] MTL parsed successfully")
        
        # ============================================================
        # Get crop window from user
        # ============================================================
        try:
            row_start = int(request.form.get('row_start'))
            row_end = int(request.form.get('row_end'))
            col_start = int(request.form.get('col_start'))
            col_end = int(request.form.get('col_end'))
        except (ValueError, TypeError):
            return jsonify({'error': 'Crop window values (row_start, row_end, col_start, col_end) are required and must be valid integers.'}), 400

        try:
            validate_crop_window(row_start, row_end, col_start, col_end)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        warning_message = None
        if (row_start != FIXED_ROW_START or row_end != FIXED_ROW_END or
                col_start != FIXED_COL_START or col_end != FIXED_COL_END):
            warning_message = (
                f"Warning: selected crop window ({row_start}-{row_end}, {col_start}-{col_end}) "
                f"does not match the fixed study area (rows {FIXED_ROW_START}-{FIXED_ROW_END}, "
                f"cols {FIXED_COL_START}-{FIXED_COL_END}). Results may not be comparable to the benchmark subset."
            )

        # ============================================================
        # STEP 2: Radiometric Calibration (DN → TOA Reflectance)
        # ============================================================
        print("\n[STEP 2] Radiometric Calibration (DN → TOA Reflectance)...")
        bands_array = load_and_calibrate_bands(
            band_paths, mtl_metadata,
            row_start=row_start, row_end=row_end,
            col_start=col_start, col_end=col_end
        )
        print(f"[SUCCESS] All bands loaded and calibrated. Shape: {bands_array.shape}")
        
        # ============================================================
        # STEP 3: Atmospheric Calibration (Scale reflectance)
        # ============================================================
        print("\n[STEP 3] Atmospheric Calibration...")
        bands_array = scale_reflectance_bands(bands_array)
        
        # ============================================================
        # STEP 4: Spectral Indices (NDBI, NDWI, NDVI)
        # ============================================================
        print("\n[STEP 4] Computing Spectral Indices...")
        ndvi, mndwi, ndbi = compute_spectral_indices(bands_array)
        
        # ============================================================
        # STEP 5: Layer Stacking
        # ============================================================
        # ============================================================
        # STEP 5: Layer Stacking
        # ============================================================
        print("\n[STEP 5] Layer Stacking...")
        feature_stack = create_feature_stack(bands_array, ndvi, mndwi, ndbi)
        
        # ============================================================
        # STEP 6: Nodata Mask
        # ============================================================
        print("\n[STEP 6] Creating Nodata Mask...")
        nodata_mask = apply_nodata_mask(bands_array)
        
        # ============================================================
        # STEP 7: Load trained model
        # ============================================================
        print("\n[STEP 7] Loading trained model...")
        model_path = app.config.get('MODEL_PATH') or os.path.join(os.path.dirname(__file__), '..', 'Model', 'best_model.pkl')
        if not os.path.exists(model_path):
            return jsonify({'error': 'Trained model not found. Please run training first.'}), 500
        
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        print(f"[SUCCESS] Model loaded: {type(model).__name__}")
        
        # ============================================================
        # STEP 8: Classify image
        # ============================================================
        print("\n[STEP 8] Classifying image...")
        classification_map = classify_image(feature_stack, model)

        # ============================================================
        # STEP 9: Compute statistics
        # ============================================================
        print("\n[STEP 9] Computing statistics...")
        stats, stats_df = compute_statistics(classification_map)
        
        # ============================================================
        # STEP 10: Visualize and save results
        # ============================================================
        print("\n[STEP 10] Creating visualizations...")
        
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], session_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Save classification map
        map_path = os.path.join(output_dir, 'classified_map.png')
        visualize_classification(classification_map, map_path)
        
        # Save statistics to CSV
        stats_csv_path = os.path.join(output_dir, 'statistics.csv')
        stats_df.to_csv(stats_csv_path, index=False)
        print(f"[SUCCESS] Statistics saved: {stats_csv_path}")
        
        # Convert map to base64 for web display
        with open(map_path, 'rb') as f:
            map_base64 = base64.b64encode(f.read()).decode()
        
        print(f"\n{'='*60}")
        print("[SUCCESS] Processing complete!")
        print(f"{'='*60}\n")
        
        response = {
            'success': True,
            'session_id': session_id,
            'map_image': f"data:image/png;base64,{map_base64}",
            'statistics': stats,
            'csv_download': f"/api/download/{session_id}/statistics.csv"
        }
        if warning_message:
            response['warning'] = warning_message

        return jsonify(response), 200
    
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/download/<session_id>/<filename>')
def download_file(session_id, filename):
    """Download result files (CSV, etc)."""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], session_id, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"{session_id}_{filename}"
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({
        'error': 'File size exceeds limit. Maximum allowed upload is 3GB. '
                 'Please split the dataset or upload smaller files if necessary.'
    }), 413

if __name__ == '__main__':
    print("\n" + "="*60)
    print("ECE 435 Remote Sensing - Web Application")
    print("Starting Flask Server...")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
