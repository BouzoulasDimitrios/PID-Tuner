from .pid import PIDController 

class PIDManager:
    def __init__(self):
        self.pid = PIDController(Kp=1, Ki=0.1, Kd=0.05, setpoint=50)
        self.value = 0
        self.dt = 0.1
        self.plotdata = []
        self.window_length = 50
        self.min_window = 10
    
    def update_value(self, param, data):
        if param == "KP":
            self.pid.Kp = data
        elif param == "KI":
            self.pid.Ki = data
        elif param == "KD":
            self.pid.Kd = data
        elif param == "SETPOINT":
            self.pid.setpoint = data
        elif param == "WINDOW_LENGTH":
            if data > self.min_window:
                self.window_length = int(data)
            else:
                return f"{param.lower()} was too low: {data}"
        
        print(f"Updated {param} to {data}")
        return f"{param.lower()} set to: {data}"

    def clear_data(self):
        self.plotdata = []