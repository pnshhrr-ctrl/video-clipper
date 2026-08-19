import os
import zipfile
import streamlit as st
import PIL.Image

# Pillow 10+ compatibility fix for MoviePy
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.video.io.VideoFileClip import VideoFileClip
import moviepy.video.fx.all as vfx

st.set_page_config(page_title="Auto Video Clipper & Editor", layout="centered")
st.title("🎬 Auto Video Clipper & Transformer")
st.write("আপনার ভিডিও ফাইলটি আপলোড করুন, অটোমেটিক ১০ সেকেন্ডের এডিটেড ক্লিপস তৈরি হয়ে যাবে!")

uploaded_file = st.file_uploader("ভিডিও ফাইল সিলেক্ট করুন (MP4)", type=["mp4"])

if uploaded_file is not None:
    if st.button("Process & Cut Video"):
        try:
            st.info("১. ভিডিও ফাইল প্রসেস করা হচ্ছে...")
            with open("input_video.mp4", "wb") as f:
                f.write(uploaded_file.read())

            st.info("২. ১০ সেকেন্ডের ক্লিপ কাটা এবং ইফেক্ট যুক্ত করা হচ্ছে...")
            clip = VideoFileClip("input_video.mp4")
            duration = int(clip.duration)

            output_dir = "output_clips"
            os.makedirs(output_dir, exist_ok=True)
            clip_files = []

            for i in range(0, duration, 10):
                end_time = min(i + 10, duration)
                if end_time - i < 3:
                    continue

                subclip = clip.subclip(i, end_time)

                # Auto Zoom
                w, h = subclip.size
                subclip = vfx.crop(subclip, x1=int(w*0.05), y1=int(h*0.05), x2=int(w*0.95), y2=int(h*0.95))
                subclip = vfx.resize(subclip, (w, h))

                # Color Change
                subclip = subclip.fx(vfx.colorx, 1.15)

                clip_filename = os.path.join(output_dir, f"clip_{i//10 + 1}.mp4")
                subclip.write_videofile(clip_filename, codec="libx264", audio_codec="aac", logger=None)
                clip_files.append(clip_filename)

            clip.close()

            # Zip File
            zip_filename = "all_clips.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for file in clip_files:
                    zipf.write(file, os.path.basename(file))

            st.success("সব ক্লিপ তৈরি সম্পন্ন!")

            with open(zip_filename, "rb") as f:
                st.download_button("Download All Clips (ZIP)", f, file_name="clips.zip")

        except Exception as e:
            st.error(f"একটি সমস্যা হয়েছে: {e}")
