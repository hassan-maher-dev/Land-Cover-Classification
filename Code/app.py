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

# IMPORTANT FOR SERVER ENVIRONMENT
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import base64
from config import get_config

# =========================================================================
# CONFIGURATION
# =========================================================================

# REDUCED FOR SERVER STABILITY
TARGET_HEIGHT = 500
TARGET_WIDTH = 500

REFLECTANCE_SCALE = 10000.0

FIXED_ROW_START = 1000
FIXED_ROW_END = 1500

FIXED_COL_START = 1000
FIXED_COL_END = 1500

# =========================================================================
# FLASK APP
# =========================================================================

app = Flask(__name__)

# ALLOW LARGE UPLOADS
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024 * 1024

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

        for band in range(1, 10):

            mult_key = f"RADIANCE_MULT_BAND_{band}"
            add_key = f"RADIANCE_ADD_BAND_{band}"

            mult_match = re.search(f"{mult_key}\\s*=\\s*([0-9.E+-]+)", content)
            add_match = re.search(f"{add_key}\\s*=\\s*([0-9.E+-]+)", content)

            if mult_match and add_match:
                metadata[f'ML_{band}'] = float(mult_match.group(1))
                metadata[f'AL_{band}'] = float(add_match.group(1))

        for band in range(1, 9):

            mult_key = f"REFLECTANCE_MULT_BAND_{band}"
            add_key = f"REFLECTANCE_ADD_BAND_{band}"

            mult_match = re.search(f"{mult_key}\\s*=\\s*([0-9.E+-]+)", content)
            add_match = re.search(f"{add_key}\\s*=\\s*([0-9.E+-]+)", content)

            if mult_match and add_match:
                metadata[f'MR_{band}'] = float(mult_match.group(1))
                metadata[f'AR_{band}'] = float(add_match.group(1))

        sun_elev_match = re.search(r"SUN_ELEVATION\s*=\s*([0-9.E+-]+)", content)

        if sun_elev_match:
            metadata['SUN_ELEVATION'] = float(sun_elev_match.group(1))

        esd_match = re.search(r"EARTH_SUN_DISTANCE\s*=\s*([0-9.E+-]+)", content)

        if esd_match:
            metadata['EARTH_SUN_DISTANCE'] = float(esd_match.group(1))

        return metadata

    except Exception as e:
        print(f"[ERROR] Failed to parse MTL file: {str(e)}")
        return None


def calibrate_to_toa(dn_value, ml, al, mr, ar, sun_elevation=None):

    radiance = ml * dn_value + al

    toa_reflectance = mr * dn_value + ar

    if sun_elevation is not None:
        toa_reflectance = toa_reflectance / np.sin(np.deg2rad(sun_elevation))

    toa_reflectance = np.clip(toa_reflectance, 0, 1)

    return toa_reflectance


def validate_crop_window(row_start, row_end, col_start, col_end):

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

    height, width = image.shape

    validate_crop_window(row_start, row_end, col_start, col_end)

    if row_end > height or col_end > width:
        raise ValueError(
            f"Requested crop window {row_start}:{row_end}, {col_start}:{col_end} "
            f"does not fit inside image size ({height}, {width})."
        )

    cropped = image[row_start:row_end, col_start:col_end]

    print(
        f"[INFO] Cropped band from ({height}, {width}) to {cropped.shape}"
    )

    return cropped


def scale_reflectance_bands(bands_array, scale=REFLECTANCE_SCALE):

    print(f"[STEP] Atmospheric Calibration (DOS + Scaling by {scale})...")

    corrected_bands = np.zeros_like(bands_array)

    for i in range(7):

        band = bands_array[i]

        valid_mask = band > 0

        if np.any(valid_mask):

            dark_pixel = np.percentile(band[valid_mask], 1)

            print(f"[DEBUG] Band {i+1} Dark Pixel: {dark_pixel:.4f}")

            band_dos = band - dark_pixel

            band_dos = np.clip(band_dos, 0, 1)

            corrected_bands[i] = band_dos

        else:
            corrected_bands[i] = band

    scaled = corrected_bands * scale

    print(f"[SUCCESS] Reflectance scaled.")

    return scaled


def apply_nodata_mask(bands_array):

    print("[STEP] Applying nodata mask...")

    mask = ~(np.sum(bands_array, axis=0) == 0)

    return mask


def load_and_calibrate_bands(
    band_paths,
    mtl_metadata,
    row_start,
    row_end,
    col_start,
    col_end
):

    bands = []

    expected_shape = None

    for band_idx in range(1, 8):

        band_path = band_paths.get(band_idx)

        if not band_path or not os.path.exists(band_path):
            raise FileNotFoundError(f"Band {band_idx} file not found")

        print(f"[INFO] Loading Band {band_idx}...")

        with rasterio.open(band_path) as src:

            dn_data = src.read(1).astype(np.float32)

        ml = mtl_metadata.get(f'ML_{band_idx}')
        al = mtl_metadata.get(f'AL_{band_idx}')
        mr = mtl_metadata.get(f'MR_{band_idx}')
        ar = mtl_metadata.get(f'AR_{band_idx}')

        toa_band = calibrate_to_toa(
            dn_data,
            ml,
            al,
            mr,
            ar,
            sun_elevation=mtl_metadata.get('SUN_ELEVATION')
        )

        if expected_shape is None:
            expected_shape = toa_band.shape

        elif toa_band.shape != expected_shape:
            raise ValueError("Band dimensions mismatch")

        toa_band = crop_to_target(
            toa_band,
            row_start,
            row_end,
            col_start,
            col_end
        )

        bands.append(toa_band)

    return np.array(bands)


def compute_spectral_indices(bands_array):

    print("[STEP] Computing Spectral Indices...")

    B3 = bands_array[2]
    B4 = bands_array[3]
    B5 = bands_array[4]
    B6 = bands_array[5]

    ndvi = (B5 - B4) / (B5 + B4 + 1e-8)
    ndvi = np.clip(ndvi, -1, 1)

    mndwi = (B3 - B6) / (B3 + B6 + 1e-8)
    mndwi = np.clip(mndwi, -1, 1)

    ndbi = (B6 - B5) / (B6 + B5 + 1e-8)
    ndbi = np.clip(ndbi, -1, 1)

    return ndvi, mndwi, ndbi


def create_feature_stack(bands_array, ndvi, mndwi, ndbi):

    print("[STEP] Layer Stacking...")

    return np.vstack([
        bands_array[:7],
        ndvi[np.newaxis, :, :],
        mndwi[np.newaxis, :, :],
        ndbi[np.newaxis, :, :]
    ])


def classify_image(feature_stack, model):

    print("[STEP] Running Classification...")

    height, width = feature_stack.shape[1], feature_stack.shape[2]

    features_reshaped = feature_stack.reshape(10, -1).T

    print(f"[INFO] Prediction input shape: {features_reshaped.shape}")

    # MEMORY SAFE BATCH PREDICTION
    batch_size = 50000

    predictions = []

    total = len(features_reshaped)

    for i in range(0, total, batch_size):

        print(f"[BATCH] Processing {i} -> {min(i+batch_size, total)}")

        batch = features_reshaped[i:i + batch_size]

        batch_predictions = model.predict(batch)

        predictions.extend(batch_predictions)

    predictions = np.array(predictions)

    classification_map = np.zeros((height, width), dtype=np.int32)

    class_mapping = {
        name: idx
        for idx, name in app.config['CLASS_NAMES'].items()
    }

    for idx, label in enumerate(predictions):
        classification_map[idx // width, idx % width] = class_mapping.get(label, 0)

    print("[SUCCESS] Classification complete")

    return classification_map


def compute_statistics(classification_map):

    print("[STEP] Computing statistics...")

    unique, counts = np.unique(classification_map, return_counts=True)

    stats = {}

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

    return stats, pd.DataFrame(stats_list)


def visualize_classification(classification_map, output_path):

    print("[STEP] Creating visualization...")

    colors_list = [app.config['CLASS_COLORS'][i] for i in range(4)]

    colors_list.append('#FFFFFF')

    custom_cmap = mcolors.ListedColormap(colors_list)

    fig, ax = plt.subplots(figsize=(10, 8), dpi=100)

    ax.imshow(classification_map, cmap=custom_cmap, vmin=0, vmax=4)

    ax.axis('off')

    plt.tight_layout()

    plt.savefig(output_path, dpi=150, bbox_inches='tight')

    plt.close()

    print(f"[SUCCESS] Visualization saved")


# =========================================================================
# FLASK ROUTES
# =========================================================================

@app.route('/')
def index():

    return render_template('index.html')


@app.route('/api/process', methods=['POST'])
def process_image():

    try:

        uploaded_files = request.files.getlist('bands')

        mtl_file = request.files.get('mtl')

        if not uploaded_files or not mtl_file:
            return jsonify({'error': 'Missing files'}), 400

        if len(uploaded_files) != 7:
            return jsonify({'error': 'Exactly 7 bands required'}), 400

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        session_folder = os.path.join(
            app.config['UPLOAD_FOLDER'],
            session_id
        )

        os.makedirs(session_folder, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"[NEW SESSION] {session_id}")
        print(f"{'='*60}")

        band_paths = {}

        for idx, band_file in enumerate(uploaded_files, 1):

            filename = secure_filename(f"B{idx}.TIF")

            filepath = os.path.join(session_folder, filename)

            band_file.save(filepath)

            band_paths[idx] = filepath

        mtl_path = os.path.join(session_folder, 'metadata.txt')

        mtl_file.save(mtl_path)

        print("[STEP 1] Parsing MTL...")

        mtl_metadata = parse_mtl_file(mtl_path)

        if not mtl_metadata:
            return jsonify({'error': 'MTL parse failed'}), 400

        try:

            row_start = int(request.form.get('row_start'))
            row_end = int(request.form.get('row_end'))

            col_start = int(request.form.get('col_start'))
            col_end = int(request.form.get('col_end'))

        except Exception:
            return jsonify({'error': 'Invalid crop window'}), 400

        validate_crop_window(
            row_start,
            row_end,
            col_start,
            col_end
        )

        print("[STEP 2] Calibration...")

        bands_array = load_and_calibrate_bands(
            band_paths,
            mtl_metadata,
            row_start,
            row_end,
            col_start,
            col_end
        )

        print("[STEP 3] Atmospheric correction...")

        bands_array = scale_reflectance_bands(bands_array)

        print("[STEP 4] Spectral indices...")

        ndvi, mndwi, ndbi = compute_spectral_indices(bands_array)

        print("[STEP 5] Layer stacking...")

        feature_stack = create_feature_stack(
            bands_array,
            ndvi,
            mndwi,
            ndbi
        )

        print("[STEP 6] Nodata mask...")

        apply_nodata_mask(bands_array)

        print("[STEP 7] Loading model...")

        model_path = app.config.get('MODEL_PATH') or os.path.join(
            os.path.dirname(__file__),
            '..',
            'Outputs',
            'best_model.pkl'
        )

        with open(model_path, 'rb') as f:
            model = pickle.load(f)

        print("[STEP 8] Classification...")

        classification_map = classify_image(feature_stack, model)

        print("[STEP 9] Statistics...")

        stats, stats_df = compute_statistics(classification_map)

        print("[STEP 10] Visualization...")

        output_dir = os.path.join(
            app.config['OUTPUT_FOLDER'],
            session_id
        )

        os.makedirs(output_dir, exist_ok=True)

        map_path = os.path.join(output_dir, 'classified_map.png')

        visualize_classification(
            classification_map,
            map_path
        )

        stats_csv_path = os.path.join(
            output_dir,
            'statistics.csv'
        )

        stats_df.to_csv(stats_csv_path, index=False)

        with open(map_path, 'rb') as f:

            map_base64 = base64.b64encode(f.read()).decode()

        print("[SUCCESS] Processing complete")

        return jsonify({
            'success': True,
            'session_id': session_id,
            'map_image': f"data:image/png;base64,{map_base64}",
            'statistics': stats,
            'csv_download': f"/api/download/{session_id}/statistics.csv"
        })

    except Exception as e:

        print(f"[ERROR] {str(e)}")

        import traceback
        traceback.print_exc()

        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<session_id>/<filename>')
def download_file(session_id, filename):

    try:

        file_path = os.path.join(
            app.config['OUTPUT_FOLDER'],
            session_id,
            filename
        )

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

    return jsonify({
        'error': 'File size exceeds limit'
    }), 413


if __name__ == '__main__':

    print("\n" + "="*60)
    print("ECE 435 Remote Sensing - Web Application")
    print("Starting Flask Server...")
    print("="*60 + "\n")

    app.run(
        debug=False,
        host='0.0.0.0',
        port=5000
    )