# caption tool for video

A Python-based desktop application that replicates the captioning functionality of CapCut, allowing users to add, edit, and export videos with captions. Built with `customtkinter`, `tkinter`, `OpenCV`, and `Pillow`, this tool provides an intuitive interface for video editing with a focus on caption management.

## Features

- **Video Playback**: Upload and play videos (MP4, AVI, MOV, MKV, WMV) with play/pause, speed control (0.25x to 4.0x), and timeline navigation.
- **Caption Management**:
  - Upload captions from `.txt` or `.json` files.
  - Add, edit, and delete captions with customizable text, position, timing, font size, and color.
  - Drag captions on the video preview for precise positioning.
- **Project Management**: Save and load projects as `.json` files to preserve video and caption data.
- **Video Export**: Export videos with embedded captions using the H.264 codec.
- **Responsive UI**: Dark-themed interface with a video preview (960x540), timeline slider, and scrollable caption lists.

## Prerequisites

- **Python**: 3.8 or higher
- **Dependencies**:
  - `customtkinter` (GUI framework)
  - `opencv-python` (video processing)
  - `Pillow` (image and text rendering)
- **System Requirements**:
  - FFmpeg or compatible video codecs for OpenCV video processing.
  - Fonts like Arial or DejaVu Sans for caption rendering (falls back to default if unavailable).

Install dependencies via pip:

```bash
pip install customtkinter opencv-python Pillow
```

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/capcut-caption-clone.git
   cd capcut-caption-clone
   ```

2. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Ensure FFmpeg is installed and accessible for video processing:
   - **Windows**: Download FFmpeg and add it to your system PATH.
   - **Linux/macOS**: Install via package manager (e.g., `sudo apt install ffmpeg` or `brew install ffmpeg`).

4. Run the application:

   ```bash
   python capcut_clone.py
   ```

## Usage

1. **Launch the Application**:
   - Run `python capcut_clone.py` to open the GUI.

2. **Upload a Video**:
   - Click "Upload Video" and select a supported video file.
   - Use the play/pause button, speed controls, and timeline slider to navigate.

3. **Add Captions**:
   - Click "Upload Captions" to load from a `.txt` file (one caption per line) or a `.json` project file.
   - Click a caption button to add it to the video at the current frame.
   - Drag captions on the preview canvas to reposition.
   - Edit caption properties (text, start/end frames, font size, color) in the properties panel.

4. **Manage Projects**:
   - Save your work to a `.json` file using "Save Project".
   - Load a project using "Load Project".

5. **Export Video**:
   - Click "Export Video" to save the video with captions as an MP4 file.
   - Monitor the export progress via the progress bar.

## File Structure

- `capcut_clone.py`: Main application script.
- `requirements.txt`: List of Python dependencies.
- `README.md`: This file.

## Limitations

- **Video Formats**: Depends on system codecs. Unsupported formats may fail to load.
- **Font Rendering**: Uses Arial or DejaVu Sans; falls back to a basic font if unavailable.
- **Aspect Ratio**: Captions may misalign in exported videos with non-16:9 aspect ratios.
- **Performance**: Large videos may slow down export; UI responsiveness may vary.

## Future Improvements

- Add support for more video codecs and formats.
- Implement font selection for captions.
- Enhance export performance with better threading.
- Add support for multiple caption styles (e.g., bold, italic).
- Improve aspect ratio handling for caption positioning.

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [customtkinter](https://github.com/TomSchimansky/CustomTkinter) for the modern UI.
- Uses [OpenCV](https://opencv.org/) for video processing and [Pillow](https://python-pillow.org/) for image handling.

---

*Created by koji | Last updated: September 2025*
