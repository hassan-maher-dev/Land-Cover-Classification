"""
Test Suite for Landsat Classification Web Application
ECE 435 Remote Sensing - Group 8
"""

import os
import sys
import pickle
import numpy as np
from pathlib import Path

def test_project_structure():
    """Verify all required files and directories exist."""
    print("\n" + "="*60)
    print("TEST 1: Project Structure Validation")
    print("="*60)
    
    required_files = {
        'Code/app.py': 'Flask application',
        'Code/requirements.txt': 'Python dependencies',
        'Code/templates/index.html': 'Web interface',
        'Code/static/style.css': 'CSS styling',
        'Code/static/script.js': 'JavaScript code',
        'Outputs/best_model.pkl': 'Trained ML model',
        'Data/Labeled_ROI.csv': 'Training dataset',
        'README.md': 'Documentation',
        'TECHNICAL_DOCS.md': 'Technical documentation'
    }
    
    all_exist = True
    for filepath, description in required_files.items():
        full_path = Path(filepath)
        exists = full_path.exists()
        status = "✓" if exists else "✗"
        print(f"{status} {filepath:<35} ({description})")
        if not exists:
            all_exist = False
    
    return all_exist

def test_model_loading():
    """Test if the trained model can be loaded."""
    print("\n" + "="*60)
    print("TEST 2: Model Loading")
    print("="*60)
    
    model_path = Path('Outputs/best_model.pkl')
    
    if not model_path.exists():
        print(f"✗ Model file not found: {model_path}")
        return False
    
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        print(f"✓ Model loaded successfully")
        print(f"  Model type: {type(model).__name__}")
        print(f"  Model classes: {model.classes_}")
        print(f"  Number of features: {model.n_features_in_}")
        
        # Test prediction on dummy data
        dummy_data = np.random.random((1, 10))
        prediction = model.predict(dummy_data)
        print(f"✓ Model prediction test: {prediction[0]}")
        
        return True
    
    except Exception as e:
        print(f"✗ Error loading model: {str(e)}")
        return False

def test_dependencies():
    """Test if all required Python packages are installed."""
    print("\n" + "="*60)
    print("TEST 3: Python Dependencies")
    print("="*60)
    
    required_packages = {
        'flask': 'Web framework',
        'werkzeug': 'WSGI utilities',
        'numpy': 'Numerical computing',
        'pandas': 'Data analysis',
        'rasterio': 'Geospatial raster data',
        'sklearn': 'Machine learning',
        'matplotlib': 'Plotting library'
    }
    
    all_installed = True
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package:<15} - {description}")
        except ImportError:
            print(f"✗ {package:<15} - MISSING ({description})")
            all_installed = False
    
    return all_installed

def test_data_files():
    """Test if training data is accessible."""
    print("\n" + "="*60)
    print("TEST 4: Data Files Validation")
    print("="*60)
    
    csv_path = Path('Data/Labeled_ROI.csv')
    
    if not csv_path.exists():
        print(f"✗ CSV file not found: {csv_path}")
        return False
    
    try:
        import pandas as pd
        df = pd.read_csv(csv_path, comment=';', header=None)
        
        print(f"✓ CSV file loaded successfully")
        print(f"  Shape: {df.shape}")
        print(f"  Columns: {df.shape[1]}")
        print(f"  Rows: {df.shape[0]}")
        print(f"  Features (B1-B10): Columns 7-16")
        
        return True
    
    except Exception as e:
        print(f"✗ Error loading CSV: {str(e)}")
        return False

def test_calibration_formulas():
    """Test radiometric calibration formulas."""
    print("\n" + "="*60)
    print("TEST 5: Radiometric Calibration Formulas")
    print("="*60)
    
    try:
        # Test values from MTL
        dn_value = 5000.0
        ml = 1.2225e-02  # RADIANCE_MULT_BAND_1
        al = -61.12637  # RADIANCE_ADD_BAND_1
        mr = 2.0000e-05  # REFLECTANCE_MULT_BAND_1
        ar = -0.100000  # REFLECTANCE_ADD_BAND_1
        
        # DN to Radiance
        radiance = ml * dn_value + al
        print(f"✓ DN → Radiance conversion")
        print(f"  DN = {dn_value}")
        print(f"  L = {ml:.4e} × {dn_value} + {al:.5f}")
        print(f"  L = {radiance:.5f} W/(m² × sr × μm)")
        
        # Radiance to TOA Reflectance
        toa_reflectance = mr * radiance + ar
        toa_reflectance = np.clip(toa_reflectance, 0, 1)
        print(f"\n✓ Radiance → TOA Reflectance conversion")
        print(f"  ρ = {mr:.4e} × {radiance:.5f} + {ar:.6f}")
        print(f"  ρ = {toa_reflectance:.5f} (clipped to [0, 1])")
        
        return True
    
    except Exception as e:
        print(f"✗ Error in calibration test: {str(e)}")
        return False

def test_spectral_indices():
    """Test spectral indices computation."""
    print("\n" + "="*60)
    print("TEST 6: Spectral Indices Computation")
    print("="*60)
    
    try:
        # Test data
        B4 = np.array([[0.2, 0.3], [0.4, 0.5]])  # Red
        B5 = np.array([[0.5, 0.6], [0.7, 0.8]])  # NIR
        B6 = np.array([[0.4, 0.5], [0.6, 0.7]])  # SWIR1
        
        # NDVI = (B5 - B4) / (B5 + B4)
        ndvi = (B5 - B4) / (B5 + B4 + 1e-8)
        ndvi = np.clip(ndvi, -1, 1)
        print(f"✓ NDVI computation")
        print(f"  Range: [{ndvi.min():.3f}, {ndvi.max():.3f}]")
        print(f"  Sample value: {ndvi[0, 0]:.3f}")
        
        # NDWI = (B5 - B6) / (B5 + B6)
        ndwi = (B5 - B6) / (B5 + B6 + 1e-8)
        ndwi = np.clip(ndwi, -1, 1)
        print(f"\n✓ NDWI computation")
        print(f"  Range: [{ndwi.min():.3f}, {ndwi.max():.3f}]")
        print(f"  Sample value: {ndwi[0, 0]:.3f}")
        
        # NDBI = (B6 - B5) / (B6 + B5)
        ndbi = (B6 - B5) / (B6 + B5 + 1e-8)
        ndbi = np.clip(ndbi, -1, 1)
        print(f"\n✓ NDBI computation")
        print(f"  Range: [{ndbi.min():.3f}, {ndbi.max():.3f}]")
        print(f"  Sample value: {ndbi[0, 0]:.3f}")
        
        return True
    
    except Exception as e:
        print(f"✗ Error in spectral indices test: {str(e)}")
        return False

def test_feature_stacking():
    """Test feature stacking logic."""
    print("\n" + "="*60)
    print("TEST 7: Feature Stacking (B1-B7 + Indices)")
    print("="*60)
    
    try:
        # Create dummy bands
        shape = (2000, 2000)
        bands_array = np.random.random((7, *shape))  # 7 spectral bands
        ndvi = np.random.random(shape)
        ndwi = np.random.random(shape)
        ndbi = np.random.random(shape)
        
        # Stack B1-B7 + 3 indices
        b1_to_b7 = bands_array[:7]
        feature_stack = np.vstack([
            b1_to_b7,
            ndvi[np.newaxis, :, :],
            ndwi[np.newaxis, :, :],
            ndbi[np.newaxis, :, :]
        ])
        
        print(f"✓ Feature stacking successful")
        print(f"  Input bands (B1-B7): {b1_to_b7.shape}")
        print(f"  Spectral indices: 3 arrays of {ndvi.shape}")
        print(f"  Output feature stack: {feature_stack.shape}")
        print(f"  Features: B1, B2, B3, B4, B5, B6, B7, NDVI, NDWI, NDBI")
        
        # Test reshape for classification
        height, width = feature_stack.shape[1], feature_stack.shape[2]
        features_reshaped = feature_stack.reshape(10, -1).T
        print(f"\n✓ Reshaping for classification")
        print(f"  Reshaped to: {features_reshaped.shape}")
        print(f"  Pixels × Features: {height * width} × 10")
        
        return True
    
    except Exception as e:
        print(f"✗ Error in feature stacking test: {str(e)}")
        return False

def run_all_tests():
    """Run all tests and generate report."""
    print("\n" + "="*60)
    print("🧪 LANDSAT CLASSIFICATION APP - TEST SUITE")
    print("ECE 435 Remote Sensing - Group 8")
    print("="*60)
    
    tests = [
        ("Project Structure", test_project_structure),
        ("Model Loading", test_model_loading),
        ("Dependencies", test_dependencies),
        ("Data Files", test_data_files),
        ("Calibration Formulas", test_calibration_formulas),
        ("Spectral Indices", test_spectral_indices),
        ("Feature Stacking", test_feature_stacking)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:<12} {test_name}")
    
    print("\n" + "-"*60)
    print(f"Total: {passed}/{total} tests passed")
    print("-"*60)
    
    if passed == total:
        print("\n🎉 All tests passed! Application is ready to run.")
        print("\nTo start the application:")
        print("  python Code/app.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix issues before running.")
        return 1

if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
