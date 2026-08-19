import os
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

# Bangla font loader
FONT_FILE = "BanglaFont.ttf"
def get_font():
    if not os.path.exists(FONT_FILE):
        try:
            font_url = "https://github.com/google/fonts/raw/main/ofl/notosansbengali/NotoSansBengali%5Bwdth%2Cwght%5D.ttf"
            res = requests.get(font_url)
            with open(FONT_FILE, "wb") as f:
                f.write(res.content)
        except Exception:
            pass

st.set_page_config(page_title="Anti-Copyright Video Clipper", layout="centered")
st.title("🛡️ Anti-Copyright Video Clipper & Transformer")
st.write("ভিডিও ফাইল আপলোড করুন, কপিরাইট-বাইপাস ফিল্টার সহ ১০ সেকেন্ডের ১০টি অটো ক্লিপ তৈরি হবে!")

if "zip_data" not in st.session_state:
    st.session_state.zip_data = None

uploaded_file = st.file_uploader("ভিডিও ফাইল সিলেক্ট করুন (MP4)", type=["mp4"])
header_text = st.text_input("উপরে ক্যাপশন টেক্সট:", value="শেষের অংশটা মিস করবেন না! 😱")
watermark_text = st.text_input("নিচে পেজের নাম/ওয়াটারমার্ক:", value="Follow for More @MyPage")

if uploaded_file is not None:
    if st.button("Process & Transform Video"):
        try:
            get_font()
            st.info("১. ভিডিও ফাইল প্রসেস করা হচ্ছে...")
            with open("input_video.mp4", "wb") as f:
                f.write(uploaded_file.read())

            st.info("২. ১০টি ক্লিপ (প্রতিটি ১০ সেকেন্ড) ও ফিল্টার প্রয়োগ করা হচ্ছে...")
            clip = VideoFileClip("input_video.mp4")
            duration = clip.duration

            output_dir = "output_clips"
            os.makedirs(output_dir, exist_ok=True)
            clip_files = []

            # Exactly 10 Clips Logic (10 seconds each)
            clip_len = 10
            total_clips = 10
            step = (duration - clip_len) / (total_clips - 1) if duration > clip_len else clip_len

            for idx in range(total_clips):
                start_t = idx * step
                end_t = min(start_t + clip_len, duration)

                subclip = clip.subclip(start_t, end_t)

                # 1. Speed Increase (1.05x)
                subclip = vfx.speedx(subclip, factor=1.05)

                # 2. Horizontal Flip (Mirroring)
                subclip = vfx.mirror_x(subclip)

                # 3. Auto Crop & Zoom (7% Border Cut)
                w, h = subclip.size
                subclip = vfx.crop(subclip, x1=int(w*0.07), y1=int(h*0.07), x2=int(w*0.93), y2=int(h*0.93))
                subclip = vfx.resize(subclip, (w, h))

                # 4. Color Grading
                subclip = subclip.fx(vfx.colorx, 1.12)
                
                # 5. Lower Audio Volume
                if subclip.audio is not None:
                    subclip = subclip.volumex(0.35)

                # 6. Top & Bottom Banners Overlay
                def add_banners(frame):
                    img = PIL.Image.fromarray(frame)
                    draw = ImageDraw.Draw(img)
                    fw, fh = img.size

                    top_banner_h = int(fh * 0.10)
                    bot_banner_h = int(fh * 0.06)

                    # Top Yellow Banner
                    draw.rectangle([(0, 0), (fw, top_banner_h)], fill=(255, 220, 0))
                    # Bottom Black Banner
                    draw.rectangle([(0, fh - bot_banner_h), (fw, fh)], fill=(20, 20, 20))

                    try:
                        font_top = ImageFont.truetype(FONT_FILE, int(top_banner_h * 0.45))
                        font_bot = ImageFont.truetype(FONT_FILE, int(bot_banner_h * 0.45))
                    except Exception:
                        font_top = font_bot = ImageFont.load_default()

                    if header_text.strip():
                        try:
                            bbox = draw.textbbox((0, 0), header_text, font=font_top)
                            tw = bbox[2] - bbox[0]
                            th = bbox[3] - bbox[1]
                        except Exception:
                            tw, th = int(top_banner_h * 0.45) * len(header_text) * 0.5, top_banner_h * 0.45
                        
                        draw.text(((fw - tw)/2, (top_banner_h - th)/2), header_text, fill=(0, 0, 0), font=font_top)

                    if watermark_text.strip():
                        try:
                            bbox_b = draw.textbbox((0, 0), watermark_text, font=font_bot)
                            tw_b = bbox_b[2] - bbox_b[0]
                            th_b = bbox_b[3] - bbox_b[1]
                        except Exception:
                            tw_b, th_b = int(bot_banner_h * 0.45) * len(watermark_text) * 0.5, bot_banner_h * 0.45

                        draw.text(((fw - tw_b)/2, fh - bot_banner_h + (bot_banner_h - th_b)/2), watermark_text, fill=(255, 255, 255), font=font_bot)

                    return np.array(img)

                subclip = subclip.fl_image(add_banners)

                clip_filename = os.path.join(output_dir, f"clip_{idx + 1}.mp4")
                subclip.write_videofile(clip_filename, codec="libx264", audio_codec="aac", logger=None)
                clip_files.append(clip_filename)

            clip.close()

            # Zip Archive
            zip_filename = "all_clips.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for file in clip_files:
                    zipf.write(file, os.path.basename(file))

            with open(zip_filename, "rb") as f:
                st.session_state.zip_data = f.read()

            st.success("১০টি কপিরাইট মুক্ত এডিটেড ক্লিপস তৈরি সম্পন্ন!")

        except Exception as e:
            st.error(f"একটি সমস্যা হয়েছে: {e}")

if st.session_state.zip_data is not None:
    st.download_button(
        label="Download All Clips (ZIP)",
        data=st.session_state.zip_data,
        file_name="clips.zip",
        mime="application/zip"
                        )
