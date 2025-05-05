import json  

def calibrate_sensor(samples=100):  
    """Kalibruje senzor na základě průměru N měření."""  
    baseline = 0  
    for _ in range(samples):  
        baseline += measure_distance()  
    return baseline / samples  

def save_calibration(data, filename="calibration.json"):  
    with open(filename, 'w') as f:  
        json.dump(data, f)  

if __name__ == "__main__":  
    calibration_data = {"baseline": calibrate_sensor()}  
    save_calibration(calibration_data)  
