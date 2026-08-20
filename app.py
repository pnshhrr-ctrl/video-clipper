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
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

FONT_FILE = "BanglaFont.ttf"

def get_font(size=40):
    if not os.path.exists(FONT_FILE):
        try:
            font_url = "https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali%5Bwdth%2Cwght%5D.ttf"
            res = requests.get(font_url)
            if res.status_code == 200:
                with open(FONT_FILE, "wb") as f:
                    f.write(res.content)
        except Exception:
            pass
    try:
        return ImageFont.truetype(FONT_FILE, size)
    except Exception:
        return ImageFont.load_default()

# Cross-version compatibility helpers for MoviePy
def resize_clip(clip, **kwargs):
    if hasattr(clip, 'resized'):
        return clip.resized(**kwargs)
    elif hasattr(clip, 'resize'):
        return clip.resize(**kwargs)
    return clip.fx(vfx.resize, **kwargs)

def crop_clip(clip, x1, y1, x2, y2):
    if hasattr(vfx, 'crop'):
        return vfx.crop(clip, x1=x1, y1=y1, x2=x2, y2=y2)
    elif hasattr(clip, 'cropped'):
        return clip.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
    elif hasattr(clip, 'crop'):
        return clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
    return clip

st.set_page_config(page_title="Pro Reels Clipper", layout="centered")
st.title("🎬 Pro Anti-Copyright Reels Clipper")
st.write("DSLR ব্লার ব্যাকগ্রাউন্ড, অটো-ওয়াটারমার্ক রিমুভার এবং সিনেমাটিক টেক্সট সহ রিলস তৈরি করুন!")

if "zip_data" not in st.session_state:
    st.session_state.zip_data = None

uploaded_file = st.file_uploader("ভিডিও ফাইল (MP4)", type=["mp4"])
header_text = st.text_input("উপরে ক্যাপশন:", value="শেষের অংশটা মিস করবেন না!")
watermark_text = st.text_input("ওয়াটারমার্ক:", value="Follow for More @CineBongo")

remove_watermark = st.checkbox("অটো-ওয়াটারমার্ক/লোগো রিমুভ (Micro-Crop & Zoom)", value=True)

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
            
            clip_len = 10
            total_clips = 10
            step = (duration - clip_len) / (total_clips - 1) if duration > clip_len else clip_len
            
            target_w, target_h = 1080, 1920

            header_font = get_font(48)
            watermark_font = get_font(32)

            for idx in range(total_clips):
                start_t = idx * step
                subclip = clip.subclip(start_t, min(start_t + clip_len, duration))

                # AUTO WATERMARK REMOVAL (Crop 4% borders)
                if remove_watermark:
                    w, h = subclip.size
                    crop_x = int(w * 0.04)
                    crop_y = int(h * 0.04)
                    subclip = crop_clip(subclip, x1=crop_x, y1=crop_y, x2=w-crop_x, y2=h-crop_y)

                # 1. Cinematic Look (Speed + Color + Saturation)
                subclip = vfx.speedx(subclip, factor=1.05)
                subclip = subclip.fx(vfx.colorx, 1.2)
                
                # 2. DSLR Blur Background
                bg_clip = resize_clip(subclip, height=target_h)
                bg_clip = vfx.gaussian_blur(bg_clip, sigma=6)
                bg_clip = bg_clip.fx(vfx.colorx, 0.4)
                
                # Center original clip
                fg_clip = resize_clip(subclip, width=target_w)
                final_subclip = CompositeVideoClip([bg_clip.set_position("center"), fg_clip.set_position("center")], size=(target_w, target_h))

                # 3. Branding & Top/Bottom Overlay with Text
                def add_banners_and_text(frame):
                    img = PIL.Image.fromarray(frame)
                    draw = ImageDraw.Draw(img)
                    w, h = img.size
                    
                    top_banner_h = int(h * 0.09)
                    bottom_banner_h = int(h * 0.06)

                    # Top Banner (Yellow)
                    draw.rectangle([(0, 0), (w, top_banner_h)], fill=(255, 215, 0))
                    # Bottom Banner (Black)
                    draw.rectangle([(0, h - bottom_banner_h), (w, h)], fill=(0, 0, 0))

                    # Top Header Text (Centered)
                    if header_text.strip():
                        bbox = draw.textbbox((0, 0), header_text, font=header_font)
                        text_w = bbox[2] - bbox[0]
                        text_h = bbox[3] - bbox[1]
                        x = (w - text_w) // 2
                        y = (top_banner_h - text_h) // 2 - 5
                        draw.text((x, y), header_text, fill=(0, 0, 0), font=header_font)

                    # Watermark Text (Centered at bottom)
                    if watermark_text.strip():
                        bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
                        text_w = bbox[2] - bbox[0]
                        text_h = bbox[3] - bbox[1]
                        x = (w - text_w) // 2
                        y = h - bottom_banner_h + (bottom_banner_h - text_h) // 2 - 5
                        draw.text((x, y), watermark_text, fill=(255, 255, 255), font=watermark_font)

                    return np.array(img)

                final_subclip = final_subclip.fl_image(add_banners_and_text)
                
                path = os.path.join(output_dir, f"clip_{idx+1}.mp4")
                final_subclip.write_videofile(path, codec="libx264", audio_codec="aac", logger=None)

            # Zip and Finish
            zip_filename = "pro_reels_output.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)

            with open(zip_filename, "rb") as f:
                st.session_state.zip_data = f.read()

            st.success("প্রো-লেভেল রিলস তৈরি সম্পন্ন!")
            st.download_button("📥 Download All Clips (ZIP)", data=st.session_state.zip_data, file_name="pro_reels.zip", mime="application/zip")

        except Exception as e:
            st.error(f"Error: {e}")
