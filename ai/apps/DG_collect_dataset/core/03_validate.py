
import os
import sys
import shutil
import numpy as np
from pathlib import Path
from insightface.app import FaceAnalysis
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
import cv2

# --- BOOTSTRAP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
import utils

def run(slug):
    """
    Step 03: Consensus Validation.
    Uses facial embeddings to identify the subject and prune outliers.
   
    """
    path = utils.get_project_path(slug)
    in_dir = path / utils.DIRS['crop']
    out_dir = path / utils.DIRS['validate']
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🧐 [03_validate] Calculating Identity Consensus for {slug}...")
    app = FaceAnalysis(name='buffalo_l', root='/mnt/c/AI/models/insightface')
    app.prepare(ctx_id=0, det_size=(640, 640))

    files = sorted([f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png'))])
    embeddings = []
    valid_files = []

    # 1. Extraction Pass
    for f in tqdm(files, desc="Analyzing Identities"):
        img = cv2.imread(str(in_dir / f))
        if img is None: continue
        faces = app.get(img)
        if faces:
            # Assume Step 2 already centered the subject
            primary = max(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]))
            embeddings.append(primary.normed_embedding)
            valid_files.append(f)

    if not embeddings:
        print("❌ No faces found to validate.")
        return

    # 2. Consensus Calculation
    # The 'Master Face' is the average embedding of the set
    master_vector = np.mean(embeddings, axis=0).reshape(1, -1)
    
    # 3. Filtering Pass
    kept_count = 0
    for f, emb in zip(valid_files, embeddings):
        score = cosine_similarity(emb.reshape(1, -1), master_vector)[0][0]
        
        # Threshold: 0.45 is usually safe for distinct subjects
        if score > 0.45:
            shutil.copy2(in_dir / f, out_dir / f)
            kept_count += 1
        else:
            print(f"   🗑️ Outlier Removed: {f} (Score: {score:.2f})")

    print(f"✅ Validation Complete. Kept {kept_count}/{len(files)} images in {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])