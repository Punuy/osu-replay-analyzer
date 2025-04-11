from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from osrparse import Replay, parse_replay_data
import os
import json
import base64
import matplotlib.pyplot as plt
import io
import numpy as np
from pathlib import Path

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def parse_osu_file(content):
    """Parse .osu file content to extract hit objects"""
    hit_objects = []
    reading_hitobjects = False
    
    for line in content.split('\n'):
        line = line.strip()
        if line == '[HitObjects]':
            reading_hitobjects = True
            continue
        if reading_hitobjects and line:
            try:
                parts = line.split(',')
                x = int(parts[0])
                time = int(parts[2])
                
                # Check if it's a LN note
                if len(parts) >= 6 and ':' in parts[5]:
                    end_time = int(parts[5].split(':')[0])
                    # Add start of LN
                    hit_objects.append({
                        'time': time,
                        'is_ln_start': True
                    })
                    # Add end of LN
                    hit_objects.append({
                        'time': end_time,
                        'is_ln_end': True
                    })
                else:
                    # Regular note
                    hit_objects.append({
                        'time': time,
                        'is_regular': True
                    })
            except (IndexError, ValueError):
                continue
    
    return sorted(hit_objects, key=lambda x: x['time'])

def find_matching_hitobject(time, hit_objects, window=50):
    """Find a matching hit object within the timing window"""
    for hit_obj in hit_objects:
        if abs(hit_obj['time'] - time) <= window:
            return hit_obj
    return None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/analyze")
async def analyze_replay(replay_file: UploadFile = File(...), beatmap_file: UploadFile = File(...)):
    # Read and parse replay file
    replay_content = await replay_file.read()
    replay = Replay.from_string(replay_content)
    
    # Read and parse beatmap file
    beatmap_content = (await beatmap_file.read()).decode('utf-8')
    hit_objects = parse_osu_file(beatmap_content)
    
    # Process replay data
    press_times = []
    key_states = [False] * 18  # Support up to 18 keys
    last_press_time = {}
    current_hit_objects = hit_objects.copy()
    
    total_time = 0
    
    for event in replay.replay_data:
        time_delta = event.time_delta
        total_time += time_delta
        keys_pressed = bin(event.keys)[2:].zfill(18)[::-1]
        
        for key_idx, key_state in enumerate(keys_pressed):
            current_state = bool(int(key_state))
            
            if current_state and not key_states[key_idx]:
                # Key press start - check if it matches a hit object
                hit_obj = find_matching_hitobject(total_time, current_hit_objects)
                if hit_obj:
                    last_press_time[key_idx] = total_time
                    if hit_obj.get('is_regular') or hit_obj.get('is_ln_start') or hit_obj.get('is_ln_end'):
                        current_hit_objects.remove(hit_obj)
            elif not current_state and key_states[key_idx]:
                # Key release
                if key_idx in last_press_time:
                    press_duration = total_time - last_press_time[key_idx]
                    press_times.append(press_duration)
                    del last_press_time[key_idx]
            
            key_states[key_idx] = current_state

    # Generate histogram data
    if press_times:
        hist, bins = np.histogram(press_times, bins=50)
        plt.figure(figsize=(10, 6))
        plt.hist(press_times, bins=50, color='#4a4a4a', edgecolor='#2d2d2d')
        plt.title('Note Hit Duration Distribution', color='white')
        plt.xlabel('Press Time (ms)', color='white')
        plt.ylabel('Count', color='white')
        plt.grid(True, alpha=0.3)
        
        # Set dark theme
        plt.style.use('dark_background')
        plt.gca().set_facecolor('#1e1e1e')
        plt.gcf().set_facecolor('#1e1e1e')
        
        # Save plot to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', facecolor='#1e1e1e')
        plt.close()
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode()
        
        stats = {
            'total_presses': len(press_times),
            'avg_press_time': sum(press_times) / len(press_times),
            'min_press_time': min(press_times),
            'max_press_time': max(press_times),
            'plot': plot_base64
        }
        
        return JSONResponse(content=stats)
    
    return JSONResponse(content={"error": "No valid note hits found in replay"})