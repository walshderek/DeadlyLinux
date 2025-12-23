import sys
import os
import cv2
import shutil

try:
    import utils
except ImportError:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import utils

def crop_face(img_path, save_path):
    try:
        # Load the cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        img = cv2.imread(str(img_path))
        if img is None: return False
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return False
            
        # Get the largest face
        x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
        
        # Add some padding
        padding = 0.4
        h_pad = int(h * padding)
        w_pad = int(w * padding)
        
        y1 = max(0, y - h_pad)
        y2 = min(img.shape[0], y + h + h_pad)
        x1 = max(0, x - w_pad)
        x2 = min(img.shape[1], x + w + w_pad)
        
        face_img = img[y1:y2, x1:x2]
        cv2.imwrite(str(save_path), face_img)
        return True
    except Exception as e:
        print(f"Crop error: {e}")
        return False

def run(slug):
    path = utils.get_project_path(slug)
    
    in_dir = path / utils.DIRS.get('scrape', '01_setup_scrape')
    out_dir = path / utils.DIRS.get('crop', '02_crop')
    out_dir.mkdir(parents=True, exist_ok=True)
    
    if not in_dir.exists():
        print(f"❌ Step 1 (Scrape) folder missing: {in_dir}")
        return

    print(f"✂️  Cropping faces from {in_dir}...")
    
    files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    count = 0
    
    for f in files:
        src = in_dir / f
        dst = out_dir / f
        
        if crop_face(src, dst):
            count += 1
        else:
            # Fallback: Copy original if no face found (user can manually crop later)
            # define a fallback policy: skip or copy? Let's skip to keep dataset clean.
            pass

    print(f"✅ Cropped {count} images to {out_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
