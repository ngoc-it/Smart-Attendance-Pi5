import cv2
import numpy as np
import onnxruntime as ort
import os

class CropImage:
    @staticmethod
    def _get_new_box(src_w, src_h, bbox, scale):
        # bbox is expected to be [x, y, w, h]
        x = bbox[0]
        y = bbox[1]
        box_w = bbox[2]
        box_h = bbox[3]

        scale = min((src_h-1)/box_h, min((src_w-1)/box_w, scale))

        new_width = box_w * scale
        new_height = box_h * scale
        center_x, center_y = box_w/2+x, box_h/2+y

        left_top_x = center_x-new_width/2
        left_top_y = center_y-new_height/2
        right_bottom_x = center_x+new_width/2
        right_bottom_y = center_y+new_height/2

        if left_top_x < 0:
            right_bottom_x -= left_top_x
            left_top_x = 0

        if left_top_y < 0:
            right_bottom_y -= left_top_y
            left_top_y = 0

        if right_bottom_x > src_w-1:
            left_top_x -= right_bottom_x-src_w+1
            right_bottom_x = src_w-1

        if right_bottom_y > src_h-1:
            left_top_y -= right_bottom_y-src_h+1
            right_bottom_y = src_h-1

        return int(left_top_x), int(left_top_y), int(right_bottom_x), int(right_bottom_y)

    def crop(self, org_img, bbox, scale, out_w, out_h, crop=True):
        if not crop:
            dst_img = cv2.resize(org_img, (out_w, out_h))
        else:
            src_h, src_w, _ = np.shape(org_img)
            left_top_x, left_top_y, right_bottom_x, right_bottom_y = self._get_new_box(src_w, src_h, bbox, scale)

            img = org_img[left_top_y: right_bottom_y+1, left_top_x: right_bottom_x+1]
            dst_img = cv2.resize(img, (out_w, out_h))
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

    def predict(self, frame, bbox_xyxy, scale=2.7, threshold=0.6):
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
        x = x1
        y = y1
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        bbox_xywh = [x, y, w, h]

        # Crop and resize
        cropped_face = self.cropper.crop(frame, bbox_xywh, scale, out_w=80, out_h=80)

        # Preprocess: normalize and transpose to NCHW
        img = cropped_face.astype(np.float32) / 255.0
        img = img.transpose((2, 0, 1))  # (80, 80, 3) -> (3, 80, 80)
        img = np.expand_dims(img, axis=0)  # Add batch dim -> (1, 3, 80, 80)

        # Run inference
        outputs = self.session.run(None, {self.input_name: img})
        raw_outputs = outputs[0][0]  # First batch output

        # Apply softmax to get probabilities
        exp_outputs = np.exp(raw_outputs - np.max(raw_outputs))
        probabilities = exp_outputs / np.sum(exp_outputs)

        live_score = float(probabilities[0])
        print_score = float(probabilities[1])
        replay_score = float(probabilities[2])

        # Get predicted label
        pred_class = np.argmax(probabilities)
        labels = ["Live", "Print-attack", "Replay-attack"]
        label = labels[pred_class]

        # A face is considered real if it classifies as Live and has score above threshold
        is_real = (pred_class == 0) and (live_score >= threshold)

        return is_real, live_score, label
