import os
import re
import shutil
import zipfile
import requests
import numpy as np
import streamlit as st
import PIL.Image
from PIL import ImageDraw, ImageFont, ImageFilter, ImageEnhance

# Pillow Resampling Fix
try:
    LANCZOS_FILTER = PIL.Image.Resampling.LANCZOS
except AttributeError:
    LANCZOS_FILTER = PIL.Image.LANCZOS

from moviepy.video.io.VideoFileClip import VideoFileClip

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

def safe_subclip(clip, start, end):
    if hasattr(clip, 'subclipped'):
        return clip.subclipped(start, end)
    return clip.subclip(start, end)

def safe_speedup(clip, factor=1.05):
    try:
        if hasattr(clip, 'speedx'):
            return clip.speedx(factor)
        elif hasattr(clip, 'with_effects'):
            import moviepy.video.fx.all as vfx
            if hasattr(vfx, 'MultiplySpeed'):
                return clip.with_effects([vfx.MultiplySpeed(factor)])
            elif hasattr(vfx, 'speedx'):
                return clip.fx(vfx.speedx, factor)
    except Exception:
        pass
    return clip

def apply_frame_transform(clip, transform_fn):
    if hasattr(clip, 'fl_image'):
        return clip.fl_image(transform_fn)
    elif hasattr(clip, 'image_transform'):
        return clip.image_transform(transform_fn)
    return clip

st.set_page_config(page_title="Pro Reels Clipper", layout="centered")
st.title("🎬 Pro Anti-Copyright Reels Clipper")
st.write("DSLR ব্লার ব্যাকগ্রাউন্ড, অটো-ওয়াটারমার্ক রিমুভার এবং কাস্টম সেটিংস সহ রিলস তৈরি করুন!")

if "zip_data" not in st.session_state:
    st.session_state.zip_data = None

# Input Fields
uploaded_file = st.file_uploader("ভিডিও ফাইল (MP4)", type=["mp4"])
header_text = st.text_input("উপরে ক্যাপশন:", value="শেষের অংশটা মিস করবেন না!")
watermark_text = st.text_input("নিচের ব্যানারের ওয়াটারমার্ক:", value="Follow for More @CineBongo")
brand_logo_text = st.text_input("ডানপাশের নীল রঙের লোগো টেক্সট:", value="CineBongo")

# --- MANUAL SELECTION OPTIONS ---
st.subheader("🎯 ভিডিও কাটিং মোড (Manual Mode Selection)")
clip_mode = st.selectbox(
    "আপনার পছন্দমতো কাটিং অপশন বেছে নিন:",
    [
        "১. মাঝের অংশ থেকে (Middle Body - Auto Cut)",
        "২. কাস্টম টাইম ফ্রেম (Specific Start & End Minutes)",
        "৩. নির্দিষ্ট মিনিট থেকে শুরু (Manual Start Minute)",
        "৪. পুরো ভিডিও থেকে সমান ব্যবধানে (Equal Interval)"
    ]
)

manual_start_min = 0.0
manual_end_min = 0.0

if "২. কাস্টম টাইম ফ্রেম" in clip_mode:
    col_time1, col_time2 = st.columns(2)
    with col_time1:
        manual_start_min = st.number_input("কয় মিনিট থেকে শুরু হবে? (Start Min):", min_value=0.0, value=1.0, step=0.5)
    with col_time2:
        manual_end_min = st.number_input("কয় মিনিটে শেষ হবে? (End Min):", min_value=0.5, value=3.0, step=0.5)

elif "৩. নির্দিষ্ট মিনিট থেকে শুরু" in clip_mode:
    manual_start_min = st.number_input("কয় মিনিট থেকে ক্লিপ নেওয়া শুরু হবে? (Minute):", min_value=0.0, value=1.0, step=0.5)

# Advanced Customization Expandable Options
with st.expander("⚙️ কাস্টম সেটিংস (Clips, Colors & Blur)"):
    total_clips = st.slider("ক্লিপের সংখ্যা (Total Clips):", min_value=1, max_value=10, value=2)
    clip_len = st.slider("প্রতিটি ক্লিপের দৈর্ঘ্য (Seconds):", min_value=5, max_value=30, value=10)
    blur_radius = st.slider("ব্যাকগ্রাউন্ড ব্লার মাত্রা (Blur Amount):", min_value=5, max_value=30, value=15)
    
    col1, col2 = st.columns(2)
    with col1:
        top_color_picker = st.color_picker("উপরের ব্যানারের রঙ", "#FFD700")
    with col2:
        bottom_color_picker = st.color_picker("নিচের ব্যানারের রঙ", "#000000")

remove_watermark = st.checkbox("অটো-ওয়াটারমার্ক/লোগো রিমুভ (Micro-Crop & Zoom)", value=True)

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

top_banner_rgb = hex_to_rgb(top_color_picker)
bottom_banner_rgb = hex_to_rgb(bottom_color_picker)

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
            
            target_w, target_h = 1080, 1920
            header_font = get_font(48)
            watermark_font = get_font(34)
            brand_font = get_font(36)

            for idx in range(total_clips):
                # Manual Logic Calculations
                if "১. মাঝের অংশ থেকে" in clip_mode:
                    intro_margin = duration * 0.15
                    usable_duration = duration * 0.70
                    step = (usable_duration - clip_len) / (total_clips - 1) if (usable_duration > clip_len and total_clips > 1) else 0
                    start_t = intro_margin + (idx * step)

                elif "২. কাস্টম টাইম ফ্রেম" in clip_mode:
                    start_sec = manual_start_min * 60
                    end_sec = min(manual_end_min * 60, duration)
                    time_range = max(end_sec - start_sec, clip_len)
                    step = (time_range - clip_len) / (total_clips - 1) if (time_range > clip_len and total_clips > 1) else 0
                    start_t = start_sec + (idx * step)

                elif "৩. নির্দিষ্ট মিনিট থেকে শুরু" in clip_mode:
                    base_start = manual_start_min * 60
                    start_t = base_start + (idx * clip_len)

                else: # ৪. সমান ব্যবধানে
                    step = (duration - clip_len) / (total_clips - 1) if (duration > clip_len and total_clips > 1) else clip_len
                    start_t = idx * step

                end_t = min(start_t + clip_len, duration)
                subclip = safe_subclip(clip, start_t, end_t)
                subclip = safe_speedup(subclip, 1.05)

                def process_frame(frame):
                    img = PIL.Image.fromarray(frame)
                    orig_w, orig_h = img.size

                    if remove_watermark:
                        crop_x = int(orig_w * 0.04)
                        crop_y = int(orig_h * 0.04)
                        img = img.crop((crop_x, crop_y, orig_w - crop_x, orig_h - crop_y))
                    
                    w, h = img.size
                    img = ImageEnhance.Color(img).enhance(1.2)

                    canvas = PIL.Image.new("RGB", (target_w, target_h), (0, 0, 0))

                    # DSLR Blur Background
                    bg_ratio = target_h / float(h)
                    bg_w = int(w * bg_ratio)
                    bg_img = img.resize((bg_w, target_h), LANCZOS_FILTER)
                    bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
                    bg_img = ImageEnhance.Brightness(bg_img).enhance(0.4)
                    bg_x = (target_w - bg_w) // 2
                    canvas.paste(bg_img, (bg_x, 0))

                    # Centered Main Clip
                    fg_ratio = target_w / float(w)
                    fg_h = int(h * fg_ratio)
                    fg_img = img.resize((target_w, fg_h), LANCZOS_FILTER)
                    fg_y = (target_h - fg_h) // 2
                    canvas.paste(fg_img, (0, fg_y))

                    # Banners & Safe Area Overlay
                    draw = ImageDraw.Draw(canvas)
                    top_banner_h = int(target_h * 0.09)
                    
                    # Bottom Banner Safe Space (Facebook Reels UI এর ওপর তুলে দেওয়া হয়েছে)
                    bottom_banner_h = int(target_h * 0.08)
                    bottom_banner_y_start = target_h - int(target_h * 0.22) # Reels UI এর ঠিক ওপরে স্থান দেওয়া হয়েছে

                    # Top Banner
                    draw.rectangle([(0, 0), (target_w, top_banner_h)], fill=top_banner_rgb)
                    
                    # Bottom Banner (Floating Safe Zone)
                    draw.rectangle([(0, bottom_banner_y_start), (target_w, bottom_banner_y_start + bottom_banner_h)], fill=bottom_banner_rgb)

                    # 1. Top Caption Text
                    if header_text.strip():
                        bbox = draw.textbbox((0, 0), header_text, font=header_font)
                        text_w = bbox[2] - bbox[0]
                        text_h = bbox[3] - bbox[1]
                        tx = (target_w - text_w) // 2
                        ty = (top_banner_h - text_h) // 2 - 5
                        draw.text((tx, ty), header_text, fill=(0, 0, 0), font=header_font)

                    # 2. Bottom Banner Watermark Text (Safe Safe Zone)
                    if watermark_text.strip():
                        bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
                        text_w = bbox[2] - bbox[0]
                        text_h = bbox[3] - bbox[1]
                        tx = (target_w - text_w) // 2
                        ty = bottom_banner_y_start + (bottom_banner_h - text_h) // 2 - 2
                        draw.text((tx, ty), watermark_text, fill=(255, 255, 255), font=watermark_font)

                    # 3. Right Corner Blue Watermark (Directly inside Main Video)
                    if brand_logo_text.strip():
                        bbox = draw.textbbox((0, 0), brand_logo_text, font=brand_font)
                        logo_w = bbox[2] - bbox[0]
                        logo_h = bbox[3] - bbox[1]
                        
                        # Positioned inside Main Video frame (Bottom-Right)
                        lx = target_w - logo_w - 40
                        ly = fg_y + fg_h - logo_h - 20

                        # Text Shadow
                        draw.text((lx + 2, ly + 2), brand_logo_text, fill=(0, 0, 0), font=brand_font)
                        # Electric Blue Text
                        draw.text((lx, ly), brand_logo_text, fill=(0, 210, 255), font=brand_font)

                    return np.array(canvas)

                final_subclip = apply_frame_transform(subclip, process_frame)
                
                path = os.path.join(output_dir, f"clip_{idx+1}.mp4")
                final_subclip.write_videofile(path, codec="libx264", audio_codec="aac", logger=None)

            # Zip Output
            zip_filename = "pro_reels_output.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)

            with open(zip_filename, "rb") as f:
                st.session_state.zip_data = f.read()

            st.success("প্রো-লেভেল রিলস তৈরি সম্পন্ন!")
            st.download_button("📥 Download All Clips (ZIP)", data=st.session_state.zip_data, file_name="pro_reels.zip", mime="application/zip")

            # Auto Storage Cleanup
            if os.path.exists("input_video.mp4"):
                os.remove("input_video.mp4")

            if os.path.exists("output_clips"):
                shutil.rmtree("output_clips")

        except Exception as e:
            st.error(f"Error: {e}")
