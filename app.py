import os
import zipfile
import streamlit as st
from yt_dlp import YoutubeDL
from moviepy.video.io.VideoFileClip import VideoFileClip
import moviepy.video.fx.all as vfx

# অ্যাপের টাইটেল ও ইন্টারফেস
st.set_page_config(page_title="Auto Video Clipper & Editor", layout="centered")
st.title("🎬 Auto Video Clipper & Transformer")
st.write("YouTube লিঙ্ক দিন, অটোমেটিক ১০ সেকেন্ডের এডিটেড ক্লিপস তৈরি হয়ে যাবে!")

# লিঙ্ক ইনপুট
video_url = st.text_input("YouTube Video URL এখানে পেস্ট করুন:")

if st.button("Process & Cut Video"):
    if not video_url:
        st.warning("মেহেরবানি করে একটি লিঙ্ক দিন!")
    else:
        try:
            st.info("১. ভিডিও ডাউনলোড হচ্ছে...")
            
            # ১. ইউটিউব ভিডিও ডাউনলোড (yt-dlp)
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': 'input_video.mp4',
                'overwrites': True
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            st.success("ডাউনলোড সম্পন্ন! এডিটিং শুরু হচ্ছে...")
            st.info("২. ১০ সেকেন্ডের ক্লিপ কাটা এবং ইফেক্ট যুক্ত করা হচ্ছে...")

            # ভিডিও লোড করা
            clip = VideoFileClip("input_video.mp4")
            duration = int(clip.duration)

            # আউটপুট ফোল্ডার তৈরি
            output_dir = "output_clips"
            os.makedirs(output_dir, exist_ok=True)
            
            clip_files = []

            # ২. ১০ সেকেন্ড পর পর কেটে ইফেক্ট যোগ করা
            for i in range(0, duration, 10):
                end_time = min(i + 10, duration)
                if end_time - i < 3: # ৩ সেকেন্ডের কম হলে শেষ ক্লিপ স্কিপ করবে
                    continue

                subclip = clip.subclip(i, end_time)

                # --- AUTO EDITING EFFECTS ---
                # A. Auto Zoom (১০% ক্রপ করে জুম)
                w, h = subclip.size
                subclip = subclip.crop(x1=w*0.05, y1=h*0.05, x2=w*0.95, y2=h*0.95).resize((w, h))

                # B. Color Change (ব্রাইটনেস সাময়িক বৃদ্ধি)
                subclip = subclip.fx(vfx.colorx, 1.15) 

                # C. Tone Shift (ভয়েস ভারী করা - Speed/Pitch সামঞ্জস্য)
                if subclip.audio is not None:
                    subclip = subclip.fx(vfx.speedx, 0.93) # গতি সামান্য কমালে টোন ভারী শোনায়

                # ফাইল সেভ
                clip_filename = os.path.join(output_dir, f"clip_{i//10 + 1}.mp4")
                subclip.write_videofile(clip_filename, codec="libx264", audio_codec="aac", logger=None)
                clip_files.append(clip_filename)

            # মূল ভিডিও অবজেক্ট বন্ধ করা
            clip.close()

            # ৩. সব ক্লিপ ZIP ফাইলে রূপান্তর
            zip_filename = "all_clips.zip"
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for file in clip_files:
                    zipf.write(file, os.path.basename(file))

            st.success("সব ক্লিপ তৈরি সম্পন্ন!")

            # ৪. ডাউনলোড বাটন প্রদান
            with open(zip_filename, "rb") as f:
                st.download_button(
                    label="📦 Download All Clips (ZIP)",
                    data=f,
                    file_name="edited_clips.zip",
                    mime="application/zip"
                )

        except Exception as e:
            st.error(f"একটি সমস্যা হয়েছে: {str(e)}")
