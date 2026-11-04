import threading
import cv2
from pyzbar.pyzbar import decode


def scan_barcode_from_camera(on_scanned_callback, stop_event):
    """
    Launches a video capture stream in a background thread.
    Calls `on_scanned_callback(barcode_text)` when a valid barcode is detected.
    """
    def run():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            on_scanned_callback(None, "Could not open camera device.")
            return

        detected_code = None
        try:
            while not stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # Decode barcodes from the current frame
                barcodes = decode(frame)
                if barcodes:
                    for barcode in barcodes:
                        detected_code = barcode.data.decode("utf-8").strip()
                        if detected_code:
                            break
                
                if detected_code:
                    break
        finally:
            cap.release()
            cv2.destroyAllWindows()

        if detected_code and not stop_event.is_set():
            on_scanned_callback(detected_code, None)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()