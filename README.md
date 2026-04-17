# Similar Image Finder

Made entirely by Google Gemini, 100% certified farm fresh slop coded.

A GUI-based Python application that scans a directory for visually similar or duplicate images. Built with **PyQt6** and **qt-material**, it uses perceptual hashing to analyze visual similarity rather than relying on exact byte-for-byte matches.

## Features

- **Visual Similarity Hashing:** Uses `imagehash` to find images that look similar, even if they have different resolutions, formats, or slight alterations.
- **Dynamic Thresholding:** Adjust the similarity percentage threshold on the fly using a slider. The groups instantly update without requiring a full directory rescan!
- **Side-by-Side Comparison:** Compare the reference image of a group against any selected duplicate with dedicated, synchronized preview panes.
- **Multithreaded Scanning:** Directory scanning happens in the background, keeping the user interface smooth and responsive during large file loads.
- **Integrated File Management:** Easily delete duplicate or unwanted images directly from the preview pane (with confirmation prompts).

## Installation

1. Ensure you have Python 3 installed.
2. Clone or download this project to your local machine.
3. Run the included `install_requirements.bat` (Windows) or `install_requirements.sh` (macOS/Linux) script. This will automatically install the necessary dependencies via pip:
   - `PyQt6`
   - `qt-material`
   - `Pillow`
   - `ImageHash`

*Alternatively, you can manually install them using: `pip install -r requirements.txt`*

## Usage

1. **Windows:** Double-click the `run_me.bat` file. This uses `pythonw` to silently launch the graphical interface without leaving an open terminal window in the background.
   **macOS/Linux:** Run `./run_me.sh` in your terminal to launch the app in the background.
2. Click **Select Directory to Scan** in the top left and pick a folder containing images.
3. Wait for it finish analysing your images.
4. Adjust the **Similarity Threshold** slider in the top right to fine-tune how strict the matching should be.
5. Click through the tree list on the left to review grouped images. The first image in the group acts as the "Reference" (green pane), while the image you click on acts as the "Selected" comparison (red pane).
6. Use the **Delete Image** buttons under the preview panes to remove duplicates from your hard drive.

## License
MIT License. Feel free to modify and use as needed.
