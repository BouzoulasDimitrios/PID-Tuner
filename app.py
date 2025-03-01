import asyncio
from fasthtml.common import *
from starlette.responses import StreamingResponse
import pandas as pd
import altair as alt
from fh_altair import altair2fasthtml, altair_headers
from pid.pid import PIDController

# from functools import partial

custom_styles = Style("""
    button {
        padding: 10px 16px;
        font-size: 12px;
        min-width: 100px;
        max-height: 50px;
    }
    form{
        display: flex; 
        gap: 10px;
    }
    input{
        max-width: 150px;
    }
    #input-container {
        display: flex;
        gap: 10px;  /* Adds spacing between the form and div */
    }
    #main_div {
        display: flex; 
        gap: 10px;
    }
""")


sselink = Script(src="https://unpkg.com/htmx-ext-sse@2.2.1/sse.js")

app, rt = fast_app(hdrs=(sselink, altair_headers, custom_styles))

pid = PIDController(Kp=1, Ki=0.1, Kd=0.05, setpoint=50)
value = 0
dt = 0.1
setpoint = 50
plotdata = []
window_length = 50  

@app.get("/")
def home(request):

    return Title("PID Demo"), Main(

        H1("PID demo"),

        Div (
            Div(
                "chart",
                sse_swap="graph_update_event",
                hx_ext="sse",
                sse_connect="/graph"
            ),

            Div(
                Div(
                    Form(
                        Input(type="number", name="data", placeholder="Enter KP"),
                        Button("Submit", hx_post="/set_KP", hx_trigger="click", hx_target="#kp"),
                    ),
                    Div(id="kp"),
                    id="input-container",
                ),
                Div(
                    Form(
                        Input(type="number", name="data", placeholder="Enter KI"),
                        Button("Submit", hx_post="/set_KI", hx_trigger="click", hx_target="#ki"),
                    ),
                    Div(id="ki"),
                    id="input-container",                
                ),        
                Div(
                    Form(
                        Input(type="number", name="data", placeholder="Enter KD"),
                        Button("Submit", hx_post="/set_KD", hx_trigger="click", hx_target="#kd"),
                    ),
                    Div(id="kd"),  
                    id="input-container",                
                ),  
                Div(
                    Form(
                        Input(type="number", name="data", placeholder="Enter setpoint"),
                        Button("Submit", hx_post="/set_setpoint", hx_trigger="click", hx_target="#setpoint"),
                    ),
                    Div(id="setpoint"),
                    id="input-container",                
                ),  
                Div(
                    Form(
                        Input(type="number", name="data", placeholder="Enter window length"),
                        Button("Submit", hx_post="/update_window", hx_trigger="click", hx_target="#window_length"),
                    ),
                    Div(id="window_length"),  
                    id="input-container",                
                ),
                Div(
                    Form(
                        Button("Clear Data", hx_post="/clear", hx_trigger="click", hx_target="#handle-response"),
                    ),
                    Div(id="handle-response")
                ),
                id="inputs"
            ),

            id = "main_div"
        ),

    )

@app.post("/clear")
def clear():
    global plotdata
    plotdata = []    
    return 

@app.post("/set_KP")
def set_kp(data:float):
    global pid
    pid.Kp = data
    print(f"reset kp {data}")
    return P(f"KP set to: {data}", id="KP")

@app.post("/set_KI")
def set_ki(data:float):
    global pid
    pid.Ki = data
    print(f"reset ki {data}")
    return P(f"KI set to: {data}", id="KI")

@app.post("/set_KD")
def set_kd(data:float):
    global pid
    pid.Kd = data
    print(f"reset kd {data}")
    return P(f"KD set to: {data}", id="kd")

@app.post("/set_setpoint")
def reset(data:float):
    global setpoint, pid
    pid.setpoint = data
    print(f"reset setpoint {data}")
    return P(f"Setpoint set to: {data}", id="setpoint")
    
@app.post("/update_window")
async def update_window(data: int = Form(...)):
    global window_length 
    window_length = data
    print(f"Received data = {data}")
    return P(f"Window length updated to {data}", id="window_length")

@app.get("/graph")
async def graph_call(request):
    return StreamingResponse(graph_generator(), media_type="text/event-stream")

async def graph_generator():
    global value, window_length
    while True:
        control_output = pid.compute(process_variable=value)
        value += control_output * dt - 0.1 * (value - 20) * dt  # Heat loss
    
        plotdata.append(value)
        plotted_data = plotdata[-window_length:] if len(plotdata) > window_length else plotdata

        pltr = pd.DataFrame({
            "x": range(len(plotted_data)),
            "y": plotted_data,
            "setpoint": [pid.setpoint] * len(plotted_data)
        })

        chart = alt.Chart(pltr).mark_line().encode(x="x", y="y").properties(title="PID Response")
        setpoint_line = alt.Chart(pltr).mark_line(strokeDash=[5, 5], color='red').encode(x="x", y="setpoint")

        final_chart = (chart + setpoint_line).interactive()
        
        out = sse_message(Div(altair2fasthtml(final_chart), sse_swap="graph_update_event"),
                        event="graph_update_event")
        yield out
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    serve()
