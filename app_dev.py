import asyncio
from fasthtml.common import *
from starlette.responses import StreamingResponse
import pandas as pd
import altair as alt
from fh_altair import altair2fasthtml, altair_headers
from pid.pid import PIDController

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

# Load external CSS
custom_styles = Link(rel="stylesheet", href="/static/styles.css")

# HTMX SSE support
sselink = Script(src="https://unpkg.com/htmx-ext-sse@2.2.1/sse.js")

app, rt = fast_app(hdrs=(sselink, altair_headers, custom_styles, sselink))

# Initialize PID Manager
pid_manager = PIDManager()

def create_input_form(name, placeholder):
    return Div(
        Form(
            Input(type="number", name="data", placeholder=placeholder),
            Button("Submit", hx_post=f"/update/{name}", hx_trigger="click", hx_target=f"#{name}"),
        ),
        Div(id=name),
        id="input-container"
    )

@app.get("/")
def home(request):
    return Title("PID Demo"), Main(
        H1("PID demo"),
        Div(
            Div("chart", sse_swap="graph_update_event", hx_ext="sse", sse_connect="/graph"),
            Div(
                create_input_form("KP", "Enter KP"),
                create_input_form("KI", "Enter KI"),
                create_input_form("KD", "Enter KD"),
                create_input_form("setpoint", "Enter setpoint"),
                create_input_form("window_length", "Enter window length"),
                Div(
                    Form(Button("Clear Data", hx_post="/clear", hx_trigger="click", hx_target="#handle-response")),
                    Div(id="handle-response"),
                    id="input-container"
                ),
                id="input_div"
            ),
            id="main_div"
        )
    )

@app.post("/update/{param}")
def update_param(param: str, data: float = Form(...)):
    msg = pid_manager.update_value(param.upper(), data)
    return P(msg, id=param)

@app.post("/clear")
def clear():
    pid_manager.clear_data()
    return P("Data cleared!", id="handle-response")

@app.get("/graph")
async def graph_call(request):
    return StreamingResponse(graph_generator(), media_type="text/event-stream")

async def graph_generator():
    while True:
        control_output = pid_manager.pid.compute(process_variable=pid_manager.value)
        pid_manager.value += control_output * pid_manager.dt - 0.1 * (pid_manager.value - 20) * pid_manager.dt  
        pid_manager.plotdata.append(pid_manager.value)
        # plotted_data = pid_manager.plotdata[-pid_manager.window_length:]
        plotted_data = pid_manager.plotdata[-pid_manager.window_length:] if len(pid_manager.plotdata) > pid_manager.window_length else pid_manager.plotdata

        pltr = pd.DataFrame({"x": range(len(plotted_data)), "y": plotted_data, "setpoint": [pid_manager.pid.setpoint] * len(plotted_data)})
        chart = alt.Chart(pltr).mark_line().encode(x="x", y="y").properties(title="PID Response")
        setpoint_line = alt.Chart(pltr).mark_line(strokeDash=[5, 5], color='red').encode(x="x", y="setpoint")

        out = sse_message(Div(altair2fasthtml(chart + setpoint_line), sse_swap="graph_update_event"), event="graph_update_event")
        yield out
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    serve()
