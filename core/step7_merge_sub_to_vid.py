import os, subprocess, time, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config_utils import load_key
from core.step1_ytdlp import find_video_files
from rich import print as rprint
import cv2
import numpy as np
import platform

SRC_FONT_SIZE = 16
TRANS_FONT_SIZE = 18
FONT_NAME = 'Arial'
TRANS_FONT_NAME = 'Arial'

# For Linux systems, install Google Noto fonts to fix Chinese character display issues: apt-get install fonts-noto
if platform.system() == 'Linux':
    FONT_NAME = 'NotoSansCJK-Regular'
    TRANS_FONT_NAME = 'NotoSansCJK-Regular'

SRC_FONT_COLOR = '&HFFFFFF'
SRC_OUTLINE_COLOR = '&H000000'
SRC_OUTLINE_WIDTH = 1
SRC_SHADOW_COLOR = '&H80000000'
TRANS_FONT_COLOR = '&H00FFFF'
TRANS_OUTLINE_COLOR = '&H000000'
TRANS_OUTLINE_WIDTH = 2  
TRANS_BACK_COLOR = '&H00000000'  

def check_gpu_support():
    """Check if NVIDIA GPU encoding is supported"""
    try:
        # Check for NVIDIA GPU encoding support
        result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True)
        return 'h264_nvenc' in result.stdout
    except Exception:
        return False

def merge_subtitles_to_video():
    # Check GPU support
    use_gpu = check_gpu_support()
    if use_gpu:
        rprint("[bold green]NVIDIA GPU encoding support detected, will use GPU acceleration.[/bold green]")
    else:
        rprint("[bold yellow]No GPU encoding support detected, falling back to CPU encoding.[/bold yellow]")

    RESOLUTION = load_key("resolution")
    TARGET_WIDTH, TARGET_HEIGHT = RESOLUTION.split('x')
    video_file = find_video_files()
    output_video = "output/output_video_with_subs.mp4"
    os.makedirs(os.path.dirname(output_video), exist_ok=True)

    # Check resolution
    if RESOLUTION == '0x0':
        rprint("[bold yellow]Warning: A 0-second black video will be generated as a placeholder as Resolution is set to 0x0.[/bold yellow]")
        frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_video, fourcc, 1, (1920, 1080))
        out.write(frame)
        out.release()
        rprint("[bold green]Placeholder video has been generated.[/bold green]")
        return

    en_srt = "output/src_subtitles.srt"
    trans_srt = "output/trans_subtitles.srt"

    if not os.path.exists(en_srt) or not os.path.exists(trans_srt):
        print("Subtitle files not found in the 'output' directory.")
        exit(1)

    # Select encoder and parameters based on GPU support
    if use_gpu:
        encoder = 'h264_nvenc'
        encoding_params = [
            '-c:v', encoder,
            '-preset', 'p4',  # NVENC preset, p4 balances performance and quality
            '-rc:v', 'vbr',   # Variable bitrate
            '-cq:v', '23',    # Quality parameter, similar to CRF
            '-b:v', '0',      # Auto bitrate
            '-maxrate:v', '130M',  # Maximum bitrate
            '-bufsize:v', '130M',  # Buffer size
        ]
    else:
        encoder = 'libx264'
        encoding_params = [
            '-c:v', encoder,
            '-preset', 'medium',
            '-crf', '23',
        ]

    # Define base FFmpeg command parameters
    base_vf = (
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"subtitles={en_srt}:force_style='Fontsize={SRC_FONT_SIZE},FontName={FONT_NAME}," 
        f"PrimaryColour={SRC_FONT_COLOR},OutlineColour={SRC_OUTLINE_COLOR},BorderStyle=1,"
        f"Outline={SRC_OUTLINE_WIDTH}',"
        f"subtitles={trans_srt}:force_style='Fontsize={TRANS_FONT_SIZE},FontName={TRANS_FONT_NAME},"
        f"PrimaryColour={TRANS_FONT_COLOR},OutlineColour={TRANS_OUTLINE_COLOR},BorderStyle=1,"
        f"Outline={TRANS_OUTLINE_WIDTH},Alignment=2,MarginV=25'"
    )

    # Generate 30fps video
    print("🎬 Start merging subtitles to video (30 FPS)...")
    ffmpeg_cmd = [
        'ffmpeg', '-i', video_file,
        '-vf', base_vf.encode('utf-8'),
        '-r', '30',
    ] + encoding_params + [
        '-y',
        output_video
    ]

    def run_ffmpeg(cmd, desc):
        start_time = time.time()
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 universal_newlines=True, encoding='utf-8')
        try:
            for line in process.stdout:
                print(line, end='')
            
            process.wait()
            if process.returncode == 0:
                print(f"\n[{desc} completed in {time.time() - start_time:.2f} seconds.]")
                return True
            else:
                print(f"\n[Error occurred during {desc}.]")
                return False
        except Exception as e:
            print(f"\n[An unexpected error occurred during {desc}: {e}]")
            if process.poll() is None:
                process.kill()
            return False

    # Execute video generation
    if run_ffmpeg(ffmpeg_cmd, "30 FPS video generation"):
        print(f"🎉🎥 Video has been generated successfully! Please check in the `output` folder 👀")
        print(f"Output video: {output_video}")
    else:
        print("⚠️ Some errors occurred during video generation. Please check the logs above.")

if __name__ == "__main__":
    merge_subtitles_to_video()
