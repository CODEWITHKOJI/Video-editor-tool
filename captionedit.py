import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, Scale
import cv2
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import json
from datetime import timedelta
import numpy as np
import threading
import platform
import subprocess
import pygame  # Added for audio playback

# Initialize pygame for audio
pygame.mixer.init()

# App setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("1400x900")
app.title("Caption tool")

# Global variables
video_path = None
cap = None
total_frames = 0
video_fps = 0
current_frame = 0
is_playing = False
captions = []
caption_buttons = []
selected_caption = None
playback_speed = 1.0
available_fonts = []
volume_level = 1.0  # Default volume (max)
audio_thread = None
stop_audio = False

# Get available fonts
def get_system_fonts():
    fonts = []
    try:
        if platform.system() == "Windows":
            # Windows font directory
            font_dir = os.path.join(os.environ['WINDIR'], 'Fonts')
            for font_file in os.listdir(font_dir):
                if font_file.endswith(('.ttf', '.ttc', '.otf')):
                    fonts.append(font_file)
        elif platform.system() == "Darwin":  # macOS
            font_dirs = [
                '/Library/Fonts',
                '/System/Library/Fonts',
                os.path.expanduser('~/Library/Fonts')
            ]
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    for font_file in os.listdir(font_dir):
                        if font_file.endswith(('.ttf', '.ttc', '.otf')):
                            fonts.append(font_file)
        else:  # Linux
            font_dirs = [
                '/usr/share/fonts',
                '/usr/local/share/fonts',
                os.path.expanduser('~/.fonts')
            ]
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    for root, dirs, files in os.walk(font_dir):
                        for font_file in files:
                            if font_file.endswith(('.ttf', '.ttc', '.otf')):
                                fonts.append(font_file)
    except Exception as e:
        print(f"Error loading fonts: {e}")
    
    # Add default fonts as fallback
    fonts.extend(['arial.ttf', 'DejaVuSans.ttf'])
    return sorted(list(set(fonts)))

# Initialize available fonts
available_fonts = get_system_fonts()

# Caption class
class Caption:
    def __init__(self, text, x, y, start_frame, end_frame, font_size=24, color="white", font_name="arial.ttf"):
        self.text = text
        self.x = x
        self.y = y
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.font_size = font_size
        self.color = color
        self.font_name = font_name
        self.canvas_id = None
        self.selected = False
    
    def to_dict(self):
        return {
            "text": self.text,
            "x": self.x,
            "y": self.y,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "font_size": self.font_size,
            "color": self.color,
            "font_name": self.font_name
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            data["text"],
            data["x"],
            data["y"],
            data["start_frame"],
            data["end_frame"],
            data.get("font_size", 24),
            data.get("color", "white"),
            data.get("font_name", "arial.ttf")
        )

# Font handling
def get_font(font_name, size):
    try:
        if platform.system() == "Windows":
            font_path = os.path.join(os.environ['WINDIR'], 'Fonts', font_name)
        else:
            # Try to find the font in common directories
            font_path = None
            font_dirs = [
                '/Library/Fonts',
                '/System/Library/Fonts',
                os.path.expanduser('~/Library/Fonts'),
                '/usr/share/fonts',
                '/usr/local/share/fonts',
                os.path.expanduser('~/.fonts')
            ]
            
            for font_dir in font_dirs:
                if os.path.exists(font_dir):
                    potential_path = os.path.join(font_dir, font_name)
                    if os.path.exists(potential_path):
                        font_path = potential_path
                        break
            
            if not font_path:
                # Fallback to default font
                return ImageFont.truetype("arial.ttf", size) if "arial.ttf" in available_fonts else ImageFont.load_default()
        
        return ImageFont.truetype(font_path, size)
    except:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except:
            return ImageFont.load_default()

# Mouse wheel scrolling
def on_mousewheel(event, canvas):
    delta = event.delta
    if platform.system() == "Linux":
        if event.num == 4:
            delta = 120
        elif event.num == 5:
            delta = -120
    canvas.yview_scroll(int(-1 * (delta / 120)), "units")

def bind_mousewheel(widget, canvas):
    widget.bind("<MouseWheel>", lambda e: on_mousewheel(e, canvas))
    if platform.system() == "Linux":
        widget.bind("<Button-4>", lambda e: on_mousewheel(e, canvas))
        widget.bind("<Button-5>", lambda e: on_mousewheel(e, canvas))

# Audio functions
def play_audio():
    global stop_audio, volume_level
    
    if not video_path:
        return
        
    # Extract audio from video using ffmpeg
    temp_audio = "temp_audio.wav"
    try:
        subprocess.run([
            'ffmpeg', '-i', video_path, '-vn', '-acodec', 'pcm_s16le', 
            '-ar', '44100', '-ac', '2', '-y', temp_audio
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Load and play audio with pygame
        pygame.mixer.music.load(temp_audio)
        pygame.mixer.music.set_volume(volume_level)
        pygame.mixer.music.play()
        
        # Keep the thread alive while audio is playing
        while pygame.mixer.music.get_busy() and not stop_audio:
            pygame.time.wait(100)
            
    except Exception as e:
        print(f"Audio error: {e}")
    finally:
        # Clean up temporary file
        if os.path.exists(temp_audio):
            os.remove(temp_audio)

def stop_audio_playback():
    global stop_audio
    stop_audio = True
    pygame.mixer.music.stop()

def set_volume(vol):
    global volume_level
    volume_level = float(vol) / 100.0
    volume_label.configure(text=f"Volume: {int(volume_level * 100)}%")
    pygame.mixer.music.set_volume(volume_level)

# Video functions
def upload_video():
    global video_path, cap, total_frames, video_fps, current_frame, is_playing, stop_audio
    
    if is_playing:
        toggle_playback()
    
    # Stop any audio playback
    stop_audio_playback()
    
    file_path = filedialog.askopenfilename(
        filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv")]
    )
    if not file_path:
        return
    
    video_path = file_path
    if cap:
        cap.release()
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        messagebox.showerror("Error", "Failed to load video. Ensure the file format is supported or install required codecs.")
        return
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = int(cap.get(cv2.CAP_PROP_FPS))
    duration = total_frames / video_fps
    time_label.configure(text=f"Duration: {timedelta(seconds=int(duration))}")
    
    timeline_slider.configure(to=1000)
    current_frame = 0
    timeline_slider.set(0)
    
    show_frame(0)
    update_timeline_display()

def show_frame(frame_index):
    global cap, current_frame
    
    if cap is None:
        return
    
    frame_index = max(0, min(frame_index, total_frames-1))
    current_frame = frame_index
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    
    if not ret:
        return
    
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame)
    img = img.resize((960, 540), Image.Resampling.LANCZOS)
    
    draw = ImageDraw.Draw(img)
    
    for caption in captions:
        if caption.start_frame <= current_frame <= caption.end_frame:
            font = get_font(caption.font_name, caption.font_size)
            outline_color = "yellow" if caption.selected else None
            if outline_color:
                draw.text((caption.x-1, caption.y-1), caption.text, font=font, fill=outline_color)
                draw.text((caption.x+1, caption.y-1), caption.text, font=font, fill=outline_color)
                draw.text((caption.x-1, caption.y+1), caption.text, font=font, fill=outline_color)
                draw.text((caption.x+1, caption.y+1), caption.text, font=font, fill=outline_color)
            
            draw.text((caption.x, caption.y), caption.text, font=font, fill=caption.color)
    
    imgtk = ImageTk.PhotoImage(img)
    
    preview_canvas.imgtk = imgtk
    preview_canvas.create_image(0, 0, anchor="nw", image=imgtk)
    update_timeline_display()

def on_slider_change(value):
    frame_index = int(float(value) * total_frames / 1000)
    show_frame(frame_index)

def update_timeline_display():
    if video_fps > 0:
        current_time = current_frame / video_fps
        total_time = total_frames / video_fps
        time_display = f"{timedelta(seconds=int(current_time))} / {timedelta(seconds=int(total_time))}"
        time_label.configure(text=time_display)

def toggle_playback():
    global is_playing, audio_thread, stop_audio
    
    is_playing = not is_playing
    play_button.configure(text="Pause" if is_playing else "Play")
    
    if is_playing:
        # Start audio playback in a separate thread
        stop_audio = False
        audio_thread = threading.Thread(target=play_audio, daemon=True)
        audio_thread.start()
        play_video()
    else:
        # Stop audio playback
        stop_audio_playback()

def play_video():
    global is_playing, current_frame
    
    if not is_playing or cap is None:
        return
    
    if current_frame >= total_frames - 1:
        current_frame = 0
        is_playing = False
        play_button.configure(text="Play")
        stop_audio_playback()
        return
    
    show_frame(current_frame)
    current_frame += int(playback_speed)
    timeline_slider.set(current_frame * 1000 / total_frames)
    
    delay = int(1000 / (video_fps * playback_speed))
    app.after(delay, play_video)

def set_playback_speed(speed):
    global playback_speed
    playback_speed = speed
    speed_label.configure(text=f"Speed: {playback_speed}x")

def go_to_start():
    global current_frame
    current_frame = 0
    timeline_slider.set(0)
    show_frame(0)
    # Restart audio from beginning if playing
    if is_playing:
        stop_audio_playback()
        pygame.mixer.music.play(start=0)

def go_to_end():
    global current_frame
    current_frame = total_frames - 1
    timeline_slider.set(1000)
    show_frame(current_frame)
    # Stop audio if playing
    if is_playing:
        stop_audio_playback()

# Caption functions
def upload_captions():
    file_path = filedialog.askopenfilename(
        filetypes=[("Text files", "*.txt"), ("JSON files", "*.json")]
    )
    if not file_path:
        return
    
    if file_path.endswith('.json'):
        load_caption_project(file_path)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            text = line.strip()
            if text:
                add_caption_button(text)

def add_caption_button(text):
    frame = ctk.CTkFrame(caption_frame, fg_color="transparent")
    frame.pack(fill="x", pady=5)
    
    btn = ctk.CTkButton(
        frame,
        text=text,
        width=200,
        height=30,
        command=lambda t=text: add_caption_to_canvas(t)
    )
    btn.pack(side="left", padx=(0, 5))
    
    del_btn = ctk.CTkButton(
        frame,
        text="X",
        width=30,
        height=30,
        fg_color="red",
        hover_color="darkred",
        command=lambda f=frame, b=btn: remove_caption_button(f, b)
    )
    del_btn.pack(side="right")
    
    caption_buttons.append((frame, btn, del_btn))

def remove_caption_button(frame, button):
    frame.destroy()
    caption_buttons[:] = [cb for cb in caption_buttons if cb[1] != button]

def add_caption_to_canvas(text):
    x, y = 480, 270
    new_caption = Caption(text, x, y, current_frame, total_frames-1)
    captions.append(new_caption)
    select_caption(new_caption)
    show_frame(current_frame)
    update_caption_list()

def select_caption(caption):
    global selected_caption
    
    if selected_caption:
        selected_caption.selected = False
    
    selected_caption = caption
    if caption:
        caption.selected = True
        caption_text.delete(0, tk.END)
        caption_text.insert(0, caption.text)
        start_frame_entry.delete(0, tk.END)
        start_frame_entry.insert(0, str(caption.start_frame))
        end_frame_entry.delete(0, tk.END)
        end_frame_entry.insert(0, str(caption.end_frame))
        font_size_slider.set(caption.font_size)
        color_entry.delete(0, tk.END)
        color_entry.insert(0, caption.color)
        
        # Set the font dropdown to the caption's font
        if caption.font_name in available_fonts:
            font_dropdown.set(caption.font_name)
        else:
            font_dropdown.set("arial.ttf")
    
    show_frame(current_frame)

def update_caption_properties():
    if selected_caption:
        try:
            start = int(start_frame_entry.get())
            end = int(end_frame_entry.get())
            if not (0 <= start <= end <= total_frames - 1):
                messagebox.showerror("Error", f"Frames must be between 0 and {total_frames - 1}, with start <= end")
                return
            selected_caption.start_frame = start
            selected_caption.end_frame = end
        except ValueError:
            messagebox.showerror("Error", "Frame values must be integers")
            return
        
        selected_caption.text = caption_text.get()
        selected_caption.font_size = int(font_size_slider.get())
        selected_caption.color = color_entry.get()
        selected_caption.font_name = font_dropdown.get()
        
        show_frame(current_frame)
        update_caption_list()

def update_caption_list():
    for widget in caption_list_frame.winfo_children():
        widget.destroy()
    
    for i, caption in enumerate(captions):
        btn = ctk.CTkButton(
            caption_list_frame,
            text=f"{i+1}. {caption.text[:20]}{'...' if len(caption.text) > 20 else ''}",
            command=lambda c=caption: select_caption(c)
        )
        btn.pack(fill="x", pady=2)
        if caption.selected:
            btn.configure(fg_color="blue")

def delete_selected_caption():
    global selected_caption
    
    if selected_caption:
        captions.remove(selected_caption)
        selected_caption = None
        show_frame(current_frame)
        update_caption_list()
        caption_text.delete(0, tk.END)
        start_frame_entry.delete(0, tk.END)
        end_frame_entry.delete(0, tk.END)
        font_size_slider.set(24)
        color_entry.delete(0, tk.END)
        color_entry.insert(0, "white")
        font_dropdown.set("arial.ttf")

# Dragging captions
drag_data = {"x": 0, "y": 0, "caption": None}

def on_drag_start(event):
    for caption in captions:
        font = get_font(caption.font_name, caption.font_size)
        bbox = font.getbbox(caption.text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        if (caption.x - text_width/2 <= event.x <= caption.x + text_width/2 and
            caption.y - text_height/2 <= event.y <= caption.y + text_height/2):
            drag_data["caption"] = caption
            drag_data["x"] = event.x
            drag_data["y"] = event.y
            select_caption(caption)
            break

def on_drag_motion(event):
    if drag_data["caption"] is not None:
        caption = drag_data["caption"]
        dx = event.x - drag_data["x"]
        dy = event.y - drag_data["y"]
        caption.x += dx
        caption.y += dy
        drag_data["x"] = event.x
        drag_data["y"] = event.y
        show_frame(current_frame)

def on_drag_release(event):
    drag_data["caption"] = None

# Project management
def save_caption_project():
    if not video_path:
        messagebox.showerror("Error", "No video loaded")
        return
    
    file_path = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")]
    )
    if not file_path:
        return
    
    project_data = {
        "video_path": video_path,
        "captions": [caption.to_dict() for caption in captions]
    }
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=4)
    
    messagebox.showinfo("Success", "Project saved successfully")

def load_caption_project(file_path=None):
    global video_path, cap, total_frames, video_fps, current_frame, captions, stop_audio
    
    if not file_path:
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if not file_path:
            return
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            project_data = json.load(f)
        
        video_path = project_data["video_path"]
        if cap:
            cap.release()
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            messagebox.showerror("Error", "Failed to load video from project. Ensure the file exists and is supported.")
            return
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_fps = int(cap.get(cv2.CAP_PROP_FPS))
        timeline_slider.configure(to=1000)
        current_frame = 0
        timeline_slider.set(0)
        
        captions = [Caption.from_dict(data) for data in project_data["captions"]]
        
        show_frame(0)
        update_caption_list()
        
        messagebox.showinfo("Success", "Project loaded successfully")
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load project: {str(e)}")

def export_video():
    if not video_path or not cap:
        messagebox.showerror("Error", "No video loaded")
        return
    
    output_path = filedialog.asksaveasfilename(
        defaultextension=".mp4",
        filetypes=[("MP4 files", "*.mp4")]
    )
    if not output_path:
        return
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = video_fps
    
    fourcc = cv2.VideoWriter_fourcc(*'H264')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    progress = ctk.CTkToplevel(app)
    progress.title("Exporting")
    progress.geometry("300x100")
    progress_label = ctk.CTkLabel(progress, text="Exporting video...")
    progress_label.pack(pady=10)
    progress_bar = ctk.CTkProgressBar(progress, width=250)
    progress_bar.pack(pady=10)
    progress_bar.set(0)
    progress.update()
    
    def export_thread():
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        aspect_ratio = width / height
        preview_aspect = 960 / 540
        x_scale = width / 960 if aspect_ratio >= preview_aspect else height / 540 * aspect_ratio
        y_scale = height / 540 if aspect_ratio <= preview_aspect else width / 960 / aspect_ratio
        
        for frame_num in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            draw = ImageDraw.Draw(pil_img)
            
            for caption in captions:
                if caption.start_frame <= frame_num <= caption.end_frame:
                    font = get_font(caption.font_name, caption.font_size)
                    x = int(caption.x * x_scale)
                    y = int(caption.y * y_scale)
                    draw.text((x, y), caption.text, font=font, fill=caption.color)
            
            frame_with_text = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            out.write(frame_with_text)
            
            app.after(0, lambda n=frame_num: progress_bar.set(n / total_frames))
            app.after(0, lambda n=frame_num: progress_label.configure(text=f"Exporting... {int(n / total_frames * 100)}%"))
        
        out.release()
        app.after(0, progress.destroy)
        app.after(0, lambda: messagebox.showinfo("Success", "Video exported successfully"))
    
    threading.Thread(target=export_thread, daemon=True).start()

def download_clip():
    if not video_path or not cap:
        messagebox.showerror("Error", "No video loaded")
        return
    
    # Create a simple dialog to select start and end time
    clip_dialog = ctk.CTkToplevel(app)
    clip_dialog.title("Download Clip")
    clip_dialog.geometry("400x200")
    
    ctk.CTkLabel(clip_dialog, text="Start Time (seconds):").pack(pady=5)
    start_time_entry = ctk.CTkEntry(clip_dialog)
    start_time_entry.pack(pady=5)
    start_time_entry.insert(0, "0")
    
    ctk.CTkLabel(clip_dialog, text="End Time (seconds):").pack(pady=5)
    end_time_entry = ctk.CTkEntry(clip_dialog)
    end_time_entry.pack(pady=5)
    end_time_entry.insert(0, str(int(total_frames / video_fps)))
    
    def process_clip():
        try:
            start_time = float(start_time_entry.get())
            end_time = float(end_time_entry.get())
            
            if start_time < 0 or end_time > total_frames / video_fps or start_time >= end_time:
                messagebox.showerror("Error", "Invalid time range")
                return
            
            output_path = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4 files", "*.mp4")]
            )
            if not output_path:
                return
            
            # Use ffmpeg to extract the clip
            cmd = [
                'ffmpeg', '-i', video_path,
                '-ss', str(start_time),
                '-to', str(end_time),
                '-c', 'copy',
                output_path
            ]
            
            # Run the command
            subprocess.run(cmd, check=True)
            messagebox.showinfo("Success", "Clip downloaded successfully")
            clip_dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download clip: {str(e)}")
    
    ctk.CTkButton(clip_dialog, text="Download Clip", command=process_clip).pack(pady=20)

# Cleanup
def cleanup():
    if cap:
        cap.release()
    stop_audio_playback()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", cleanup)

# UI Layout
# Create a top frame for the download button
top_frame = ctk.CTkFrame(app, height=50)
top_frame.pack(side="top", fill="x", padx=10, pady=5)
top_frame.pack_propagate(False)

# Add download button to top right
download_btn = ctk.CTkButton(top_frame, text="Download Clip", command=download_clip, 
                            fg_color="purple", hover_color="darkpurple", height=40)
download_btn.pack(side="right", padx=5)

# Add export button next to it
export_btn = ctk.CTkButton(top_frame, text="Export Video", command=export_video, 
                          fg_color="green", hover_color="darkgreen", height=40)
export_btn.pack(side="right", padx=5)

left_frame = ctk.CTkFrame(app, width=300)
left_frame.pack(side="left", fill="y", padx=10, pady=10)
left_frame.pack_propagate(False)

upload_btn = ctk.CTkButton(left_frame, text="Upload Video", command=upload_video)
upload_btn.pack(pady=5)

play_button = ctk.CTkButton(left_frame, text="Play", command=toggle_playback)
play_button.pack(pady=5)

control_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
control_frame.pack(pady=5)

start_btn = ctk.CTkButton(control_frame, text="<<", width=30, command=go_to_start)
start_btn.pack(side="left", padx=2)

speed_down_btn = ctk.CTkButton(control_frame, text="-", width=30, 
                              command=lambda: set_playback_speed(max(0.25, playback_speed - 0.25)))
speed_down_btn.pack(side="left", padx=2)

speed_label = ctk.CTkLabel(control_frame, text="Speed: 1.0x")
speed_label.pack(side="left", padx=5)

speed_up_btn = ctk.CTkButton(control_frame, text="+", width=30, 
                            command=lambda: set_playback_speed(min(4.0, playback_speed + 0.25)))
speed_up_btn.pack(side="left", padx=2)

end_btn = ctk.CTkButton(control_frame, text=">>", width=30, command=go_to_end)
end_btn.pack(side="left", padx=2)

# Volume control
volume_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
volume_frame.pack(pady=5)

volume_label = ctk.CTkLabel(volume_frame, text="Volume: 100%")
volume_label.pack()

volume_slider = ctk.CTkSlider(volume_frame, from_=0, to=100, command=set_volume)
volume_slider.set(100)
volume_slider.pack(pady=5)

time_label = ctk.CTkLabel(left_frame, text="Duration: 00:00:00 / 00:00:00")
time_label.pack(pady=5)

caption_btn = ctk.CTkButton(left_frame, text="Upload Captions", command=upload_captions)
caption_btn.pack(pady=5)

# Create a scrollable frame for caption buttons
caption_scroll_frame = ctk.CTkScrollableFrame(left_frame, width=280, height=150)
caption_scroll_frame.pack(pady=5, fill="both", expand=True)

caption_frame = ctk.CTkFrame(caption_scroll_frame, fg_color="transparent")
caption_frame.pack(fill="both", expand=True)

props_label = ctk.CTkLabel(left_frame, text="Caption Properties:")
props_label.pack(pady=(10, 5))

# Make the properties frame scrollable
props_scroll_frame = ctk.CTkScrollableFrame(left_frame, width=280, height=250)
props_scroll_frame.pack(fill="x", pady=5)

props_frame = ctk.CTkFrame(props_scroll_frame, fg_color="transparent")
props_frame.pack(fill="x")

ctk.CTkLabel(props_frame, text="Text:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
caption_text = ctk.CTkEntry(props_frame)
caption_text.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

ctk.CTkLabel(props_frame, text="Start Frame:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
start_frame_entry = ctk.CTkEntry(props_frame)
start_frame_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

ctk.CTkLabel(props_frame, text="End Frame:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
end_frame_entry = ctk.CTkEntry(props_frame)
end_frame_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

ctk.CTkLabel(props_frame, text="Font Size:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
font_size_slider = ctk.CTkSlider(props_frame, from_=10, to=72, number_of_steps=62)
font_size_slider.set(24)
font_size_slider.grid(row=3, column=1, sticky="ew", padx=5, pady=2)

ctk.CTkLabel(props_frame, text="Font:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
font_dropdown = ctk.CTkOptionMenu(props_frame, values=available_fonts)
font_dropdown.set("arial.ttf")
font_dropdown.grid(row=4, column=1, sticky="ew", padx=5, pady=2)

ctk.CTkLabel(props_frame, text="Color:").grid(row=5, column=0, sticky="w", padx=5, pady=2)
color_entry = ctk.CTkEntry(props_frame)
color_entry.insert(0, "white")
color_entry.grid(row=5, column=1, sticky="ew", padx=5, pady=2)

update_btn = ctk.CTkButton(props_frame, text="Update", command=update_caption_properties)
update_btn.grid(row=6, column=0, columnspan=2, pady=5)

delete_btn = ctk.CTkButton(props_frame, text="Delete Caption", fg_color="red", 
                          hover_color="darkred", command=delete_selected_caption)
delete_btn.grid(row=7, column=0, columnspan=2, pady=5)

props_frame.columnconfigure(1, weight=1)

list_label = ctk.CTkLabel(left_frame, text="Caption List:")
list_label.pack(pady=(10, 5))

# Create a scrollable frame for caption list
caption_list_frame = ctk.CTkScrollableFrame(left_frame, width=280, height=150)
caption_list_frame.pack(fill="both", expand=True, pady=5)

project_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
project_frame.pack(pady=10)

save_btn = ctk.CTkButton(project_frame, text="Save Project", command=save_caption_project)
save_btn.pack(side="left", padx=5)

load_btn = ctk.CTkButton(project_frame, text="Load Project", command=load_caption_project)
load_btn.pack(side="left", padx=5)

right_frame = ctk.CTkFrame(app)
right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

preview_canvas = tk.Canvas(right_frame, width=960, height=540, bg="black")
preview_canvas.pack(pady=20)

preview_canvas.bind("<Button-1>", on_drag_start)
preview_canvas.bind("<B1-Motion>", on_drag_motion)
preview_canvas.bind("<ButtonRelease-1>", on_drag_release)

timeline_slider = ctk.CTkSlider(
    right_frame, from_=0, to=1000, command=on_slider_change, width=1000
)
timeline_slider.pack(pady=10)

app.mainloop()
