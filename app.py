import os
import re
import zipfile
import requests
import numpy as np
import streamlit as st
import PIL.Image
from PIL import ImageDraw, ImageFont

# Pillow 10+ compatibility fix
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.video.io.VideoFileClip import VideoFileClip
import moviepy.video.fx.all as vfx
import moviepy.audio.fx.all as afx
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

FONT_FILE = "BanglaFont.ttf"
def get_font():
    if not os.path.exists(FONT_FILE):
        try:
            font_url = "https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali%5Bwdth%2Cwght%5D.ttf"
            res = requests.get(font_url)
            if res.status_code == 200:
                with open(FONT_FILE, "wb") as f:
                    f.write(res.content)
        except Exception:
            pass

def clean_text(text):
    return re.sub(r'[^\w\s\u0980-\u09FF\.,!\?\-@#]', '', text)

st.set_page_config(page_title="Pro Reels Clipper", layout="centered")
st.title("🎬 Pro Anti-Copyright Reels Clipper")
st.write("DSLR ব্লার ব্যাকগ্রাউন্ড এবং সিনেমাটিক কালার গ্রেডিং সহ রিলস তৈরি করুন!")

if "zip_data" not in st.session_state:
    st.session_state.zip_data = None

uploaded_file = st.file_uploader("ভিডিও ফাইল (MP4)", type=["mp4"])
header_text = st.text_input("উপরে ক্যাপশন:", value="শেষের অংশটা মিস করবেন না!")
watermark_text = st.text_input("ওয়াটারমার্ক:", value="Follow for More @CineBongo")

if uploaded_file is not None:
    if st.button("Process Pro Reels"):
        try:
            get_font()
            with open("input_video.mp4", "wb") as f:
                f.write(uploaded_file.read())

            clip = VideoFileClip("input_video.mp4")
            duration = clip.duration
            output_dir = "output_clips"
            os.makedirs(output_dir, exist_ok=True)
            
            # Exactly 10 Clips Logic
            clip_len = 10
            total_clips = 10
            step = (duration - clip_len) / (total_clips - 1) if duration > clip_len else clip_len
            
            target_w, target_h = 1080, 1920

            for idx in range(total_clips):
                start_t = idx * step
                subclip = clip.subclip(start_t, min(start_t + clip_len, duration))

                # 1. Cinematic Look (Speed + Color + Contrast)
                subclip = vfx.speedx(subclip, factor=1.05)
                subclip = subclip.fx(vfx.colorx, 1.2) # Increased Saturation for Mood
                
                # 2. DSLR Blur Background
                bg_clip = subclip.resize(height=target_h)
                bg_clip = vfx.gaussian_blur(bg_clip, sigma=5) # DSLR BLUR EFFECT
                bg_clip = bg_clip.fx(vfx.colorx, 0.4) # Darken background
                
                # Center original clip
                fg_clip = subclip.resize(width=target_w)
                final_subclip = CompositeVideoClip([bg_clip.set_position("center"), fg_clip.set_position("center")], size=(target_w, target_h))

                # 3. Branding
                def add_banners(frame):
                    img = PIL.Image.fromarray(frame)
                    draw = ImageDraw.Draw(img)
                    w, h = img.size
                    # Banner rectangles
                    draw.rectangle([(0, 0), (w, int(h*0.08))], fill=(255, 220, 0))
                    draw.rectangle([(0, h-int(h*0.05)), (w, h)], fill=(0, 0, 0))
                    return np.array(img)

                final_subclip = final_subclip.fl_image(add_banners)
                
                path = os.path.join(output_dir, f"clip_{idx+1}.mp4")
                final_subclip.write_videofile(path, codec="libx264", audio_codec="aac", logger=None)

            # Zip and Finish
            # ... (Zip logic same as before) ...
            st.success("প্রো-লেভেল রিলস তৈরি সম্পন্ন!")
        except Exception as e:
            st.error(f"Error: {e}")
