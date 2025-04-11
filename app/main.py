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
    """Parse .osu file content to extract hit objects and metadata"""
    hit_objects = []
    reading_hitobjects = False
    metadata = {
        'Artist': '',
        'Title': '',
        'Version': '',
        'Creator': ''
    }
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Extract metadata
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            if key in metadata:
                metadata[key] = value
        
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
    
    return sorted(hit_objects, key=lambda x: x['time']), metadata

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
    hit_objects, metadata = parse_osu_file(beatmap_content)
    
    # Process replay data
    press_times_by_key = {i: [] for i in range(18)}  # Track press times for each key separately
    key_states = [False] * 18
    last_press_time = {}
    current_hit_objects = hit_objects.copy()
    
    # Initialize hit counts and score
    count_300 = replay.count_300
    count_100 = replay.count_100
    count_50 = replay.count_50
    count_miss = replay.count_miss
    count_katu = replay.count_katu
    count_geki = replay.count_geki
    score = replay.score
    combo = replay.max_combo
    
    total_time = 0
    
    # Define colors for each key
    colors = [
        "#ff0000", "#ff8000", "#ffff00", "#7dff00", "#00ff00", "#00ffff",
        "#0000ff", "#7d00ff", "#ff00ff", "#ff9999", "#ffc299", "#ffff99",
        "#c2ff99", "#99ff99", "#99ffff", "#9999ff", "#c299ff", "#ff99ff"
    ]
    
    for event in replay.replay_data:
        time_delta = event.time_delta
        total_time += time_delta
        keys_pressed = bin(event.keys)[2:].zfill(18)[::-1]
        
        for key_idx, key_state in enumerate(keys_pressed):
            current_state = bool(int(key_state))
            
            if current_state and not key_states[key_idx]:
                hit_obj = find_matching_hitobject(total_time, current_hit_objects)
                if hit_obj:
                    last_press_time[key_idx] = total_time
                    if hit_obj.get('is_regular') or hit_obj.get('is_ln_start') or hit_obj.get('is_ln_end'):
                        current_hit_objects.remove(hit_obj)
            elif not current_state and key_states[key_idx]:
                if key_idx in last_press_time:
                    press_duration = total_time - last_press_time[key_idx]
                    press_times_by_key[key_idx].append(press_duration)
                    del last_press_time[key_idx]
            
            key_states[key_idx] = current_state

    # Generate histogram data
    active_keys = [i for i, times in press_times_by_key.items() if times]
    if active_keys:
        # Create figure with more space for legend
        plt.figure(figsize=(12, 8))
        
        # Create histograms for each active key
        for idx, key_idx in enumerate(active_keys):
            if press_times_by_key[key_idx]:
                plt.hist(press_times_by_key[key_idx], bins=50, 
                        alpha=0.5, label=f'Key {key_idx + 1}',
                        color=colors[idx], edgecolor='none')
        
        # Create multi-line title
        title = f"{metadata['Artist']} - {metadata['Title']} [{metadata['Version']}]\n"
        title += f"Beatmap by {metadata['Creator']}\n"
        title += f"Played by {replay.username} on {replay.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        
        plt.title(title, color='white', pad=20)
        plt.xlabel('Press Time (ms)', color='white')
        plt.ylabel('Count', color='white')
        plt.grid(True, alpha=0.3)
        
        # Move legend to center right
        plt.legend(bbox_to_anchor=(1.02, 0.5), 
                  loc='center left',
                  borderaxespad=0.,
                  frameon=False,
                  labelcolor='white',
                  facecolor='#1e1e1e')
        
        # Adjust layout to prevent legend cutoff
        plt.subplots_adjust(right=0.85)
        
        # Set tick colors to white
        plt.gca().tick_params(axis='x', colors='white')
        plt.gca().tick_params(axis='y', colors='white')
        
        # Add hit counts and score
        perfect_hits = count_300 + count_geki
        good_hits = count_100 + count_katu
        total_notes = count_300 + count_100 + count_50 + count_miss + count_geki + count_katu
        
        # Calculate accuracy
        numerator = (perfect_hits * 300) + (good_hits * 100) + (count_50 * 50)
        accuracy = (numerator / (total_notes * 300)) * 100 if total_notes > 0 else 0
        
        hit_counts_text = (
            f"Score : {score:,}\n\n"
            f"300 : {count_300:4}   300g : {count_geki:4}\n"
            f"100 : {count_100:4}   100g : {count_katu:4}\n"
            f"50 : {count_50:4}   Miss : {count_miss:4}\n"
            f"Combo : {combo:4}  Acc : {accuracy:.2f}%"
        )

        # Create background box for text
        plt.text(0.98, 0.98, hit_counts_text,
                transform=plt.gca().transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                fontsize=10,
                bbox=dict(facecolor='#1e1e1e', edgecolor='none', alpha=0.7),
                color='white',
                fontfamily='monospace',
                multialignment='right')

        # Set dark theme
        plt.style.use('dark_background')
        plt.gca().set_facecolor('#1e1e1e')
        plt.gcf().set_facecolor('#1e1e1e')

        # Set grid color
        ax = plt.gca()
        for spine in ax.spines.values():
            spine.set_edgecolor('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
        
        # Save plot to bytes
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', facecolor='#1e1e1e')
        plt.close()
        buf.seek(0)
        plot_base64 = base64.b64encode(buf.getvalue()).decode()
        
        # Calculate statistics for all keys combined
        all_press_times = [time for times in press_times_by_key.values() for time in times]
        
        stats = {
            'total_presses': len(all_press_times),
            'avg_press_time': sum(all_press_times) / len(all_press_times) if all_press_times else 0,
            'min_press_time': min(all_press_times) if all_press_times else 0,
            'max_press_time':   max(all_press_times) if all_press_times else 0,
            'plot': plot_base64,
            'count_300': count_300,
            'count_geki': count_geki,
            'count_100': count_100,
            'count_katu': count_katu,
            'count_50': count_50,
            'count_miss': count_miss,
            'score': score
        }
        
        return JSONResponse(content=stats)
    
    return JSONResponse(content={"error": "No valid note hits found in replay"})