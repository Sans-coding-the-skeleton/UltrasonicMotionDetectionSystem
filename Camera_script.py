import cv2
import os
import time
from datetime import datetime
from collections import deque
from picamera2 import Picamera2
import RPi.GPIO as GPIO

# Hardware Configuration
TRIG_PIN = 23
ECHO_PIN = 24
CAMERA_ROTATION = cv2.ROTATE_180
SAVE_DIR = os.path.expanduser("~/Security_Captures")

# Detection Parameters
DISTANCE_THRESHOLD = 25
COOLDOWN_PERIOD = 7
READING_WINDOW = 5
STABILIZATION_READINGS = 10

# UI Configuration (BGR color format)
UI_SCALE = 1.0
FONT = cv2.FONT_HERSHEY_SIMPLEX
COLORS = {
    'background': (40, 40, 40),    # Dark gray
    'text': (200, 200, 200),       # White
    'alert': (0, 0, 255),          # Red (BGR format)
    'status': (100, 100, 100)      # Gray
}

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.output(TRIG_PIN, False)
    time.sleep(1)

def initialize_camera():
    picam2 = Picamera2()
    try:
        config = picam2.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"})
        picam2.configure(config)
        picam2.start()
        time.sleep(2)
        return picam2
    except Exception as e:
        print(f"Camera initialization failed: {e}")
        return None

def get_distance():
    """Returns distance in cm (2-400cm) or None for invalid readings"""
    try:
        GPIO.output(TRIG_PIN, True)
        time.sleep(0.00001)
        GPIO.output(TRIG_PIN, False)

        pulse_start = time.time()
        timeout = pulse_start + 0.04

        while GPIO.input(ECHO_PIN) == 0:
            pulse_start = time.time()
            if pulse_start > timeout:
                return None

        pulse_end = time.time()
        while GPIO.input(ECHO_PIN) == 1:
            pulse_end = time.time()
            if pulse_end > timeout:
                return None

        distance = (pulse_end - pulse_start) * 17150
        return round(distance, 1) if 2 < distance < 400 else None
    except Exception as e:
        print(f"Distance measurement error: {e}")
        return None

def draw_interface(frame, distance, last_capture):
    if frame is None:
        return None
        
    try:
        # Header
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), COLORS['background'], -1)
        cv2.putText(frame, "Ultrasonic Motion Detection System", (10, 30), 
                   FONT, 0.8*UI_SCALE, COLORS['text'], 1)

        # Status bar
        status_text = f"Current: {distance}cm | Last trigger: {last_capture} | press 'q' to leave" if distance else "Initializing..."
        cv2.rectangle(frame, (0, frame.shape[0]-40), (frame.shape[1], frame.shape[0]), 
                      COLORS['status'], -1)
        cv2.putText(frame, status_text, (10, frame.shape[0]-10), 
                   FONT, 0.6*UI_SCALE, COLORS['text'], 1)

        # Timestamp
        cv2.putText(frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                   (10, frame.shape[0]-60), FONT, 0.5*UI_SCALE, COLORS['text'], 1)
        return frame
    except Exception as e:
        print(f"Interface drawing error: {e}")
        return None

def main():
    setup_gpio()
    
    # Initialize camera with retry logic
    cam = None
    for _ in range(3):
        cam = initialize_camera()
        if cam is not None:
            break
        time.sleep(1)
    
    if cam is None:
        print("Failed to initialize camera after 3 attempts")
        return

    try:
        os.makedirs(SAVE_DIR, exist_ok=True)
        os.chmod(SAVE_DIR, 0o755)
    except Exception as e:
        print(f"Directory error: {e}")
        return

    readings = deque(maxlen=READING_WINDOW)
    last_capture = 0
    stable_count = 0

    # Discard initial unstable readings
    while stable_count < STABILIZATION_READINGS:
        if get_distance() is not None:
            stable_count += 1
        time.sleep(0.1)

    try:
        while True:
            current_distance = get_distance()
            now = time.time()
            
            # Capture frame with error handling
            try:
                frame = cam.capture_array()
                if frame is None:
                    raise RuntimeError("Received empty frame")
                
                # Rotate
                frame = cv2.rotate(frame, CAMERA_ROTATION)
                
                if frame is None:
                    raise RuntimeError("Frame processing failed")
            except Exception as e:
                print(f"Frame capture error: {e}")
                time.sleep(1)
                continue

            processed_frame = None
            if current_distance is not None:
                readings.append(current_distance)
                
                # Create safe copy for drawing
                try:
                    frame_copy = frame.copy()
                except AttributeError as e:
                    print(f"Frame copy error: {e}")
                    continue
                
                # Draw interface
                processed_frame = draw_interface(
                    frame_copy,
                    current_distance,
                    datetime.fromtimestamp(last_capture).strftime("%H:%M:%S") if last_capture else "None"
                )

                if len(readings) >= READING_WINDOW and (now - last_capture) > COOLDOWN_PERIOD:
                    avg_change = abs(readings[-1] - readings[0])
                    
                    if avg_change > DISTANCE_THRESHOLD:
                        try:
                            filename = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            # Save original frame (already converted to BGR)
                            cv2.imwrite(os.path.join(SAVE_DIR, filename), frame)
                            print(f"Alert! {avg_change}cm change detected. Image saved.")
                            last_capture = now
                            readings.clear()
                        except Exception as e:
                            print(f"Save error: {e}")
# red filter when change is detected
                      #  try:
                      #      overlay = processed_frame.copy()
                      #      cv2.rectangle(overlay, (0,0), (processed_frame.shape[1], processed_frame.shape[0]), 
                      #                  COLORS['alert'], -1)
                      #      cv2.addWeighted(overlay, 0.2, processed_frame, 0.8, 0, processed_frame)
                      #  except Exception as e:
                      #      print(f"Overlay error: {e}")

            # Display handling
            try:
                if processed_frame is not None:
                    cv2.namedWindow("Monitor", cv2.WND_PROP_FULLSCREEN)
                    cv2.setWindowProperty("Monitor", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                    cv2.imshow("Monitor", processed_frame)
            except Exception as e:
                print(f"Display error: {e}")

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(0.1)

    finally:
        if cam is not None:
            cam.stop()
        GPIO.cleanup()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
