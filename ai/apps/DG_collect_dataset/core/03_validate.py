
import sys
import os
import shutil
import time
from pathlib import Path

import sys
import os
import shutil
import numpy as np
from PIL import Image
from pathlib import Path

# --- BOOTSTRAP PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

# Use insightface for validation
from insightface.app import FaceAnalysis
from sklearn.cluster import DBSCAN

def run(slug):
    config = utils.load_config(slug)
    if not config:
        return

    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['validate']
    out_dir.mkdir(parents=True, exist_ok=True)

    if not in_dir.exists():
        print(f"❌ Error: Input directory not found: {in_dir}")
        return

    print(f"🔍 Validating images in '{in_dir}' using face clustering...")

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))])
    if not files:
        print("❌ No images to validate.")
        return

    face_app = FaceAnalysis()
    face_app.prepare(ctx_id=0)

    embeddings = []
    valid_files = []

    for i, f in enumerate(files, 1):
        img_path = in_dir / f
        try:
            img_pil = Image.open(img_path).convert("RGB")
            img_np = np.array(img_pil)
            faces = face_app.get(img_np)
            if not faces:
                continue
            # Use the largest face
            face = max(faces, key=lambda x: x.bbox[2]*x.bbox[3])
            embeddings.append(face.embedding)
            valid_files.append(f)
        except Exception as e:
            print(f"   [!] Error processing {f}: {e}")

    if not embeddings:
        print("❌ No faces detected in any image.")
        return

    embeddings = np.stack(embeddings)
    # Cluster faces: DBSCAN with cosine metric
    clustering = DBSCAN(eps=0.6, min_samples=2, metric='cosine').fit(embeddings)
    labels = clustering.labels_

    # Find the largest cluster (the main person)
    from collections import Counter
    counts = Counter(labels)
    if -1 in counts:
        del counts[-1]  # Remove noise
    if not counts:
        print("❌ No valid clusters found.")
        return
    majority_label = counts.most_common(1)[0][0]
    print(f"   Majority cluster: {majority_label} (size: {counts[majority_label]})")

    kept = 0
    for f, label in zip(valid_files, labels):
        src = in_dir / f
        dst = out_dir / f
        if label == majority_label:
            shutil.copy(src, dst)
            kept += 1

    print(f"✅ Validation Complete. {kept} images passed (kept from largest cluster).")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])

    # Step 2: Cluster embeddings (find dominant person)
    from sklearn.cluster import DBSCAN
    X = np.stack(embeddings)
    # DBSCAN: eps=0.7 is typical for face embeddings, min_samples=2
    clustering = DBSCAN(eps=0.7, min_samples=2, metric='euclidean').fit(X)
    labels = clustering.labels_

    # Find the largest cluster (excluding noise label -1)
    from collections import Counter
    counts = Counter(labels)
    if -1 in counts:
        del counts[-1]
    if not counts:
        print("❌ No clusters found (all faces are outliers).")
    majority_label = counts.most_common(1)[0][0]
    print(f"   Majority cluster: {majority_label} (size: {counts[majority_label]})")

    # Step 3: Copy only images in the majority cluster
    valid_count = 0
    for f, label in zip(file_list, labels):
        src = in_dir / f
        dst = out_dir / f
        if label == majority_label:
            shutil.copy(src, dst)
            valid_count += 1
        else:
            print(f"   [03_validate] Rejected (not in cluster): {f}")

    print(f"✅ Validation Complete. {valid_count} images passed (majority cluster).")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])