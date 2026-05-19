"""
ECE 435: Remote Sensing - Course Project
Phase 1: Model Training & Serialization Script
Zagazig University - Faculty of Engineering (Batch 2026)
Group: 8
"""

import os
import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import accuracy_score, classification_report

def main():
    # -------------------------------------------------------------------------
    # 1. إعداد المسارات الديناميكية (الرجوع خطوتين للوصول للجذر الرئيسي)
    # -------------------------------------------------------------------------
    current_script_dir = os.path.dirname(os.path.abspath(__file__)) # Code/1-Model_Training
    project_root_dir = os.path.dirname(os.path.dirname(current_script_dir)) # Root Folder
    
    csv_path = os.path.join(project_root_dir, 'Data', 'Labeled_ROI.csv')
    output_dir = os.path.join(project_root_dir, 'Outputs')
    output_model_path = os.path.join(output_dir, 'best_model.pkl')
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("==================================================")
    print("[TRAINING MODE] Initiating Pipeline Engine...")
    print("==================================================")

    # -------------------------------------------------------------------------
    # 2. تحميل البيانات الطيفية وبناء مصفوفات التدريب
    # -------------------------------------------------------------------------
    print("[INFO] Loading spectral training data from CSV...")
    if not os.path.exists(csv_path):
        print(f"[ERROR] Could not find ROI file at: {csv_path}")
        return

    df = pd.read_csv(csv_path, comment=';', header=None)
    X = df.iloc[:, 2:12]  # الـ 10 ميزات الطيفية في الـ CSV الجديد  # الـ 10 ميزات الطيفية

    water_n, desert_n, urban_n, veg_n = 5873, 7856, 3266, 541
    y = np.array(['Water'] * water_n + ['Desert'] * desert_n + ['Urban'] * urban_n + ['Vegetation'] * veg_n)

    min_len = min(len(X), len(y))
    X, y = X.iloc[:min_len], y[:min_len]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.30, random_state=42)

    # -------------------------------------------------------------------------
    # 3. تدريب ومقارنة الـ 6 مصنفات
    # -------------------------------------------------------------------------
    print("[INFO] Fine-tuning and evaluating 6 Classifiers...")
    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "SVM": SVC(kernel='rbf', random_state=42),
        "KNN": KNeighborsClassifier(n_neighbors=5),
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Neural Network (MLP)": MLPClassifier(hidden_layer_sizes=(50, 25), max_iter=500, random_state=42),
        "Naive Bayes": GaussianNB()
    }

    best_acc = 0.0
    best_model_name = ""
    best_model_instance = None

    for name, model in models.items():
        print(f"[PROCESS] Training Classifier: {name}...")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        print(f"================ {name} Result ================")
        print(f"Accuracy: {acc*100:.2f}%")
        print(classification_report(y_test, y_pred))

        if acc > best_acc:
            best_acc = acc
            best_model_name = name
            best_model_instance = model

    print("\n" + "="*50)
    print(f"[WINNER] Highest Accuracy achieved by: [{best_model_name}] ({best_acc*100:.2f}%)")
    print("="*50)

    # -------------------------------------------------------------------------
    # 4. حفظ الموديل الفائز أوتوماتيكياً في مجلد Outputs
    # -------------------------------------------------------------------------
    print(f"\n[INFO] Saving [{best_model_name}] brain matrix to disk...")
    with open(output_model_path, 'wb') as f:
        pickle.dump(best_model_instance, f)
    print(f"[SUCCESS] Serialized pre-trained model saved at: {output_model_path}")
    print("==================================================")

if __name__ == '__main__':
    main()