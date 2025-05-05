"""
Ultrasonic Security System for Raspberry Pi

This script detects motion using an HC-SR04 ultrasonic sensor.
When significant distance changes are detected, it saves timestamped camera captures
in daily folders.
"""

import cv2
import os
import time
from datetime import datetime
from collections import deque
from picamera2 import Picamera2
import RPi.GPIO as GPIO

# ==============================
# CONFIGURATION SETTINGS
# ==============================

# Hardware setup
TRIG_PIN = 23      # GPIO pin for TRIG sensor
ECHO_PIN = 24      # GPIO pin for ECHO sensor
CAMERA_ROTATION = cv2.ROTATE_180  # Camera orientation correction
SAVE_FOLDER = os.path.expanduser("~/Ultrasonic_Motions")  # Main storage directory

# Detection parameters
DISTANCE_THRESHOLD = 25    # Minimum distance change for detection (cm)
COOLDOWN_TIME = 7          # Minimum time between detections (seconds)
MEASUREMENT_WINDOW = 5     # Number of measurements for analysis
STABILIZATION_SAMPLES = 10 # Initial measurements for calibration

# Interface settings
UI_SCALE = 1.0            # UI elements scale
FONT = cv2.FONT_HERSHEY_SIMPLEX  # Font type
COLORS = {
    'background': (40, 40, 40),   # Dark gray background
    'text': (200, 200, 200),      # White text
    'alert': (0, 0, 255),         # Red alert (BGR format)
    'status': (100, 100, 100)     # Gray status bar
}

# ==============================
# HELPER FUNCTIONS
# ==============================

def setup_gpio():
    """Initializes GPIO pins for ultrasonic sensor."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.output(TRIG_PIN, False)
    time.sleep(1)

def initialize_camera():
    """Starts Raspberry Pi camera and returns camera object."""
    try:
        camera = Picamera2()
        config = camera.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"})
        camera.configure(config)
        camera.start()
        time.sleep(2)  # Allow camera initialization
        return camera
    except Exception as error:
        print(f"Camera initialization error: {error}")
        return None

def measure_distance():
    """
    Measures distance using HC-SR04.
    Returns:
        float: Distance in centimeters (2-400 cm)
        None: For invalid measurements
    """
    try:
        # Generate ultrasonic pulse
        GPIO.output(TRIG_PIN, True)
        time.sleep(0.00001)
        GPIO.output(TRIG_PIN, False)

        # Measure echo return time
        start_time = time.time()
        timeout = start_time + 0.04  # Maximum measurement duration

        # Wait for echo pulse start
        while GPIO.input(ECHO_PIN) == 0:
            start_time = time.time()
            if start_time > timeout:
                return None

        # Measure echo pulse end
        end_time = time.time()
        while GPIO.input(ECHO_PIN) == 1:
            end_time = time.time()
            if end_time > timeout:
                return None

        # Calculate distance
        distance = (end_time - start_time) * 17150
        return round(distance, 1) if 2 < distance < 400 else None
    except Exception as error:
        print(f"Measurement error: {error}")
        return None

def create_interface(frame, distance, last_capture):
    """
    Renders user interface onto the frame.
    Parameters:
        frame (np.array): Input image frame
        distance (float): Current measured distance
        last_capture (str): Time of last detection
    Returns:
        np.array: Frame with rendered UI
    """
    if frame is None:
        return None
        
    try:
        # Header
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), COLORS['background'], -1)
        cv2.putText(frame, "Ultrasonic Security System", (10, 30), 
                   FONT, 0.8*UI_SCALE, COLORS['text'], 1)

        # Status bar
        status_text = (f"Current: {distance}cm | Last detection: {last_capture} | "
                       "Press 'q' to quit") if distance else "Initializing..."
        cv2.rectangle(frame, (0, frame.shape[0]-40), (frame.shape[1], frame.shape[0]), 
                      COLORS['status'], -1)
        cv2.putText(frame, status_text, (10, frame.shape[0]-10), 
                   FONT, 0.6*UI_SCALE, COLORS['text'], 1)

        # Timestamp
        cv2.putText(frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                   (10, frame.shape[0]-60), FONT, 0.5*UI_SCALE, COLORS['text'], 1)
        return frame
    except Exception as error:
        print(f"UI rendering error: {error}")
        return None

# ==============================
# MAIN PROGRAM LOOP
# ==============================

def main():
    # Hardware initialization
    setup_gpio()
    
    # Camera startup with retries
    camera = None
    for _ in range(3):
        camera = initialize_camera()
        if camera is not None:
            break
        time.sleep(1)
    
    if camera is None:
        print("Failed to initialize camera after 3 attempts")
        return

    # Create main save directory
    try:
        os.makedirs(SAVE_FOLDER, exist_ok=True)
        os.chmod(SAVE_FOLDER, 0o755)
    except Exception as error:
        print(f"Directory creation error: {error}")
        return

    # Initialize variables
    measurements = deque(maxlen=MEASUREMENT_WINDOW)
    last_capture_time = 0
    stabilization_count = 0

    # Calibration phase
    while stabilization_count < STABILIZATION_SAMPLES:
        if measure_distance() is not None:
            stabilization_count += 1
        time.sleep(0.1)

    try:
        while True:
            current_distance = measure_distance()
            current_time = time.time()
            
            # Capture camera frame
            try:
                frame = camera.capture_array()
                if frame is None:
                    raise RuntimeError("Received empty frame")
                
                # Adjust frame orientation
                frame = cv2.rotate(frame, CAMERA_ROTATION)
                
                if frame is None:
                    raise RuntimeError("Frame processing error")
            except Exception as error:
                print(f"Frame capture error: {error}")
                time.sleep(1)
                continue

            processed_frame = None
            if current_distance is not None:
                measurements.append(current_distance)
                
                # Create UI copy
                try:
                    frame_copy = frame.copy()
                except AttributeError as error:
                    print(f"Frame copy error: {error}")
                    continue
                
                # Render interface
                processed_frame = create_interface(
                    frame_copy,
                    current_distance,
                    datetime.fromtimestamp(last_capture_time).strftime("%H:%M:%S") if last_capture_time else "None"
                )

                # Motion detection
                if len(measurements) >= MEASUREMENT_WINDOW and (current_time - last_capture_time) > COOLDOWN_TIME:
                    avg_change = abs(measurements[-1] - measurements[0])
                    
                    if avg_change > DISTANCE_THRESHOLD:
                        try:
                            # Get current timestamp once
                            now = datetime.now()
                            
                            # Create daily directory
                            date_folder = now.strftime("%Y-%m-%d")
                            daily_path = os.path.join(SAVE_FOLDER, date_folder)
                            os.makedirs(daily_path, exist_ok=True)
                            
                            # Generate filename
                            filename = f"ultrasonic_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                            full_path = os.path.join(daily_path, filename)
                            
                            # Save image
                            cv2.imwrite(full_path, frame)
                            print(f"Alert! Detected {avg_change}cm change. Image saved at {full_path}")
                            
                            # Update last capture time and clear measurements
                            last_capture_time = current_time
                            measurements.clear()
                        except Exception as error:
                            print(f"Save error: {error}")

            # Display window
            try:
                if processed_frame is not None:
                    cv2.namedWindow("Monitor", cv2.WND_PROP_FULLSCREEN)
                    cv2.setWindowProperty("Monitor", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
                    cv2.imshow("Monitor", processed_frame)
            except Exception as error:
                print(f"Display error: {error}")

            # Exit on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            time.sleep(0.1)

    finally:
        if camera is not None:
            camera.stop()
        GPIO.cleanup()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
