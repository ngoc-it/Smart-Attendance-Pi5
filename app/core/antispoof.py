import cv2
import numpy as np
import onnxruntime as ort
import os

class CropImage:
    def crop(self, org_img, bbox, scale, out_w, out_h, crop=True):
        if not crop:
            dst_img = cv2.resize(org_img, (out_w, out_h))
        else:
            x, y, w, h = bbox
            center_x = x + w / 2.0
            center_y = y + h / 2.0
            b_w = max(w, h)
            b_h = max(w, h)
            size = int(b_w * scale)
            x0 = int(center_x - size / 2.0)
            y0 = int(center_y - size / 2.0)
            x1 = x0 + size
            y1 = y0 + size
            
            src = np.array([
                [x0, y0],
                [x0, y1],
                [x1, y1],
                [x1, y0]
            ], np.float32)
            dst = np.array([
                [0, 0],
                [0, out_h - 1],
                [out_w - 1, out_h - 1],
                [out_w - 1, 0]
            ], np.float32)
            m = cv2.getPerspectiveTransform(src, dst)
            dst_img = cv2.warpPerspective(org_img, m, (out_w, out_h))
        return dst_img


class AntiSpoofDetector:
    def __init__(self, model_path="models/minifasnet_v2.onnx"):
        self.model_path = model_path
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Anti-spoofing model not found at {self.model_path}")
        
        # Initialize ONNX Runtime Session using CPU provider
        self.session = ort.InferenceSession(self.model_path, providers=['CPUExecutionProvider'])
        self.input_name = self.session.get_inputs()[0].name
        self.cropper = CropImage()

    def predict(self, frame, bbox_xyxy, scale=1.5, threshold=0.6):
        """
        Predict if the face in the bounding box is Real or Spoof.
        
        Parameters:
        - frame: Original BGR image (numpy array).
        - bbox_xyxy: Face bounding box in [x1, y1, x2, y2] format.
        - scale: Scaling factor for cropping context (MiniFASNetV2 default is 2.7).
        - threshold: Minimum confidence for the "Live" class to be considered Real.
        
        Returns:
        - is_real: Boolean indicating if it's a real face.
        - live_score: Confidence score of the live class (0.0 to 1.0).
        - label: String label ("Live", "Print-attack", or "Replay-attack").
        """
        # Convert bbox from [x1, y1, x2, y2] to [x, y, w, h]
        x1, y1, x2, y2 = bbox_xyxy
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        center_x = x1 + w / 2.0
        center_y = y1 + h / 2.0
        
        # Heuristically adapt InsightFace bbox (which includes whole head) 
        # to match OpenCV SSD bbox (which is tighter on height but slightly wider on width)
        # This matches the training data of MiniFASNet.
        new_w = w * 1.17
        new_h = h * 0.87
        new_center_y = center_y + (h * 0.11)
        
        new_x = int(center_x - new_w / 2.0)
        new_y = int(new_center_y - new_h / 2.0)
        new_w = int(new_w)
        new_h = int(new_h)
        
        bbox_xywh = [new_x, new_y, new_w, new_h]

        # Crop and resize
        cropped_face = self.cropper.crop(frame, bbox_xywh, scale, out_w=80, out_h=80)

        # Preprocess: DO NOT normalize by 255.0! The original model was trained on 0-255 range.
        img = cropped_face.astype(np.float32)
        img = img.transpose((2, 0, 1))  # (80, 80, 3) -> (3, 80, 80)
        img = np.expand_dims(img, axis=0)  # Add batch dim -> (1, 3, 80, 80)

        # Run inference
        outputs = self.session.run(None, {self.input_name: img})
        raw_outputs = outputs[0][0]  # First batch output

        # Apply softmax to get probabilities
        exp_outputs = np.exp(raw_outputs - np.max(raw_outputs))
        probabilities = exp_outputs / np.sum(exp_outputs)

        # Index 1 is Live (Real Face), Index 0 and 2 are Spoof
        live_score = float(probabilities[1])

        # Get predicted label
        pred_class = np.argmax(probabilities)
        labels = ["Spoof", "Live", "Spoof"]
        label = labels[pred_class]

        # If threshold <= 0, anti-spoofing is disabled (always consider real)
        if threshold <= 0:
            return True, live_score, "Disabled"

        # A face is considered real if it classifies as Live and has score above threshold
        is_real = (pred_class == 1) and (live_score >= threshold)

        return is_real, live_score, label
