"""
ECE 435: Remote Sensing - Course Project
Phase 2: Independent Testing & Inference Script
Zagazig University - Faculty of Engineering (Batch 2026)
Group: 8
"""

import os
import pickle
import rasterio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

def main():
    # -------------------------------------------------------------------------
    # 1. إعداد المسارات الديناميكية (الرجوع خطوتين للوصول للجذر الرئيسي)
    # -------------------------------------------------------------------------
    current_script_dir = os.path.dirname(os.path.abspath(__file__)) # Code/2-Model_Testing
    project_root_dir = os.path.dirname(os.path.dirname(current_script_dir)) # Root Folder
    
    # ⚠️ اسم الصورة الجديدة المراد تلوينها واختبارها (موجودة داخل فولدر Data)
    new_image_name = 'Final_Feature_Stack.tif' 
    
    new_tif_path = os.path.join(project_root_dir, 'Data', new_image_name)
    model_path = os.path.join(project_root_dir, 'Outputs', 'best_model.pkl')
    output_dir = os.path.join(project_root_dir, 'Outputs')
    
    output_image_path = os.path.join(output_dir, f'Classified_{new_image_name.split(".")[0]}.png')
    output_stats_path = os.path.join(output_dir, f'Stats_{new_image_name.split(".")[0]}.csv')

    print("==================================================")
    print("[INFERENCE MODE] Testing New Satellite Scene...")
    print("==================================================")

    # -------------------------------------------------------------------------
    # 2. تحميل الموديل الجاهز من مجلد Outputs دون إعادة تدريب
    # -------------------------------------------------------------------------
    print("[INFO] Loading pre-trained AI model binary...")
    if not os.path.exists(model_path):
        print(f"[ERROR] Found no model file at: {model_path}\nPlease execute the training script inside '1-Model_Training' first.")
        return

    with open(model_path, 'rb') as f:
        loaded_model = pickle.load(f)
    print("[SUCCESS] Operational model matrix successfully mounted.")

    # -------------------------------------------------------------------------
    # 3. قراءة الصورة وعزل الهوامش
    # -------------------------------------------------------------------------
    print(f"[INFO] Accessing target GeoTIFF array: {new_image_name}")
    if not os.path.exists(new_tif_path):
        print(f"[ERROR] Target image missing at: {new_tif_path}")
        return

    with rasterio.open(new_tif_path) as src:
        img = src.read() 
        height, width = src.height, src.width

    nodata_mask = (img[0] == 0)
    img_reshaped = img.reshape(10, -1).T

    # -------------------------------------------------------------------------
    # 4. التنبؤ وتلوين الصورة
    # -------------------------------------------------------------------------
    print("[RUNNING] Running spatial mapping classification cells...")
    predicted_labels = loaded_model.predict(img_reshaped)

    class_mapping = {'water': 0, 'vegetation': 1, 'urban': 2, 'desert': 3}
    predicted_numeric = np.array([class_mapping[label.lower()] for label in predicted_labels])

    classification_map = predicted_numeric.reshape(height, width)
    classification_map[nodata_mask] = 4

    # -------------------------------------------------------------------------
    # 5. حساب الإحصائيات وحفظ الـ CSV
    # -------------------------------------------------------------------------
    print("[INFO] Exporting area statistics calculations...")
    unique, counts = np.unique(classification_map, return_counts=True)
    stats = dict(zip(unique, counts))

    inv_mapping = {0: 'Water', 1: 'Vegetation', 2: 'Urban', 3: 'Desert'}
    stats_list = []
    
    print("\n--- Target Scene Spatial Quantification ---")
    print(f"{'Class Name':<15} | {'Pixel Count':<12} | {'Area (km²)':<10}")
    print("-" * 45)

    for code, count in stats.items():
        if code in inv_mapping:
            class_name = inv_mapping[code]
            area_km2 = (count * 900) / 1e6
            print(f"{class_name:<15} | {count:<12} | {area_km2:.2f} km²")
            stats_list.append({"Class Name": class_name, "Pixel Count": count, "Area (km2)": round(area_km2, 2)})

    pd.DataFrame(stats_list).to_csv(output_stats_path, index=False)

    # -------------------------------------------------------------------------
    # 6. رسم الخريطة الملونة وحفظها
    # -------------------------------------------------------------------------
    colors = ['#0055FF', '#228B22', '#E60000', '#FFD700', '#FFFFFF']
    custom_cmap = mcolors.ListedColormap(colors)

    plt.figure(figsize=(10, 10))
    plt.imshow(classification_map, cmap=custom_cmap, vmin=0, vmax=4)

    real_classes = {0: 'Water', 1: 'Vegetation', 2: 'Urban', 3: 'Desert'}
    patches = [plt.plot([],[], marker="s", ms=10, ls="", mec=None, color=colors[i], 
                                label=real_classes[i])[0] for i in range(4)]
    plt.legend(handles=patches, loc='lower right', facecolor='white', fontsize=12)

    plt.title(f"Classification Map Output - Test Scene", fontsize=14, pad=15)
    plt.axis('off') 

    plt.savefig(output_image_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SUCCESS] Visual thematic png map exported to Outputs folder.")
    print("==================================================")

if __name__ == '__main__':
    main()