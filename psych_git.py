import os
import gspread
import google.generativeai as genai
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
import time
import random
from moviepy.editor import *
from moviepy.config import change_settings
from google.generativeai.types import GenerationConfig
from upload_video import get_authenticated_service, upload_video, update_video_details
import sys

# --- SETUP AND AUTHENTICATION ---
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'credentials.json'
load_dotenv()
try:
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini AI Authenticated Successfully.")
except Exception as e: exit(f"❌ ERROR: Gemini AI Auth Failed. {e}")
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    gspread_client = gspread.authorize(creds)
    sheet = gspread_client.open("yt_story").sheet1 # Consider changing "yt_story" to a new sheet name if needed
    print("✅ Google Sheets Authenticated and Opened Successfully.")
except Exception as e: exit(f"❌ ERROR: Google Sheets Auth Failed. {e}")


# --- GITHUB ACTIONS & ENVIRONMENT FUNCTIONS ---

def setup_environment():
    """Configure environment for GitHub Actions or local development."""
    if os.getenv('GITHUB_ACTIONS'):
        print("🤖 Running in GitHub Actions automation mode")
        try:
            change_settings({"IMAGEMAGICK_BINARY": "/usr/bin/convert"})
            print("✅ ImageMagick configured for Linux")
        except Exception as e:
            print(f"⚠️ ImageMagick setup warning: {e}")
        return True
    else:
        print("💻 Running in local development mode")
        try:
            # You can keep your local Windows path here for testing
            change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})
        except Exception:
            print("⚠️ ImageMagick path not configured for Windows. Text may fail.")
        return False

def get_user_choice():
    """Get user choice, auto-select for automation."""
    if os.getenv('GITHUB_ACTIONS'):
        print("🚀 Auto-selecting option 2: Generate, Upload, and Update video")
        return '2'
    else:
        print("\n--- AI YouTube Shorts Factory ---")
        print("1: Generate a new video and save it locally.")
        print("2: Generate, Upload, and Update a new video on YouTube.")
        return input("Enter your choice (1 or 2): ")

def verify_media_files():
    """Verify that media files are available in the correct folders."""
    music_files = [f for f in os.listdir('psych_music') if f.endswith('.mp3')] if os.path.exists('psych_music') else []
    video_files = [f for f in os.listdir('psych_temp') if f.endswith('.mp4')] if os.path.exists('psych_temp') else []
    
    print(f"📁 Found {len(music_files)} music files and {len(video_files)} video templates")
    
    if len(music_files) == 0 or len(video_files) == 0:
        print("❌ ERROR: Missing media files!")
        return False
    return True

# --- AI CONTENT GENERATION ---

def create_quote_content() -> tuple[str, str, str]:
    """Generates a new, unique two-part psychology quote."""
    print("🧠 Activating AI Psychology quote generator...")
    
    try:
        used_quotes = sheet.col_values(1)[1:] 
        history_list = "\n".join(f"- {quote}" for quote in used_quotes)
    except Exception as e:
        print(f"⚠️ Could not read sheet history: {e}")
        history_list = "None."
        
    MAX_ATTEMPTS = 5
    for attempt in range(MAX_ATTEMPTS):
        print(f"🤖 Attempt {attempt + 1}/{MAX_ATTEMPTS}...")
        
        themes = [
            "Cognitive Dissonance", "Confirmation Bias", "The Dunning-Kruger Effect",
            "Imposter Syndrome", "The Paradox of Choice", "Cognitive Biases",
            "The Placebo Effect", "Emotional Intelligence", "The Subconscious Mind",
            "Memory and Perception", "Neuroplasticity", "Behavioral Psychology"
        ]
        chosen_theme = random.choice(themes)
        print(f"  Chosen Theme: {chosen_theme}")

        master_prompt = f"""
        You are an AI that creates insightful, two-part quotes about human psychology.
        Your quote MUST be about the specific theme of: **{chosen_theme}**.
        CRITICAL RULES:
        1. Your language MUST be simple and easy to understand. Avoid jargon.
        2. The first part is a "hook". The second part is the "reveal".
        3. Do NOT generate a quote similar to any in the "PREVIOUSLY USED QUOTES" list.
        4. Your ENTIRE response MUST be in the format below, with nothing else.

        **GOOD EXAMPLES:**
        * EXAMPLE 1: `PART_1: The most uncomfortable feeling…\nPART_2: …is holding two contradictory beliefs at the same time.\nTITLE: The Battle In Your Mind`
        * EXAMPLE 2: `PART_1: We don't see the world as it is…\nPART_2: …we see it as we already believe it to be.\nTITLE: Your Personal Echo Chamber`

        **PREVIOUSLY USED QUOTES:**
        {history_list}

        **YOUR REQUIRED OUTPUT FORMAT:**
        PART_1: [The first part of the quote]
        PART_2: [The second part of the quote]
        TITLE: [The video title]
        """
        
        generation_config = GenerationConfig(temperature=0.8)
        response = gemini_model.generate_content(master_prompt, generation_config=generation_config)
        
        try:
            part1 = response.text.split("PART_2:")[0].replace("PART_1:", "").strip()
            part2 = response.text.split("TITLE:")[0].split("PART_2:")[1].strip()
            title = response.text.split("TITLE:")[1].strip()
            print("✅ New, unique quote generated!")
            return part1, part2, title
        except Exception as e:
            print(f"⚠️ Could not parse the AI's response. Retrying... Error: {e}")
            
    print(f"❌ Failed to generate a unique quote after {MAX_ATTEMPTS} attempts.")
    return "Error", "Could not generate unique quote.", "Error"

def generate_extra_tags(title: str, quote_parts: str) -> list:
    """Uses AI to brainstorm a list of relevant SEO tags."""
    print("🤖 Brainstorming additional SEO tags...")
    prompt = f"""
    Based on the following video title and content about psychology, generate a list of 10-15 relevant, popular, and SEO-friendly YouTube tags.
    TITLE: {title}
    CONTENT: {quote_parts}
    RULES: Return ONLY a comma-separated list of tags. Do not use hashtags (#). Include a mix of broad and specific tags (e.g., psychology facts, human behavior, cognitive bias, life hacks, shorts).
    Your comma-separated list of tags:
    """
    generation_config = GenerationConfig(temperature=0.7)
    response = gemini_model.generate_content(prompt, generation_config=generation_config)
    
    tags = [tag.strip() for tag in response.text.split(',')]
    print(f"✅ Generated {len(tags)} extra tags.")
    return tags

# --- VIDEO GENERATION ---

def generate_video_with_music(part1: str, part2: str, output_filename: str):
    """Generates a video with a sequentially chosen background, music, and subtitles."""
    print(f"🎬 Generating video for '{output_filename}'...")
    VIDEO_DURATION = 12

    try:
        music_folder = 'psych_music'
        available_music = [f for f in os.listdir(music_folder) if f.endswith('.mp3')]
        chosen_music_path = os.path.join(music_folder, random.choice(available_music))
        print(f"🎵 Using music: {chosen_music_path}")
        
        background_video_folder = 'psych_temp'
        available_videos = sorted([f for f in os.listdir(background_video_folder) if f.endswith('.mp4')])
        
        if not available_videos:
            exit(f"❌ ERROR: No background videos found in '{background_video_folder}'.")

        state_file = 'psych_temp/last_video_index.txt'
        last_index = -1
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                try: last_index = int(f.read())
                except ValueError: last_index = -1

        next_index = (last_index + 1) % len(available_videos)
        chosen_video_path = os.path.join(background_video_folder, available_videos[next_index])

        with open(state_file, 'w') as f:
            f.write(str(next_index))
        
        print(f"🔄 Sequentially selected video #{next_index + 1}: {chosen_video_path}")

    except Exception as e:
        exit(f"❌ ERROR: Could not find media files. Details: {e}")

    music_clip = AudioFileClip(chosen_music_path).subclip(0, VIDEO_DURATION)
    background_clip = VideoFileClip(chosen_video_path)
    if background_clip.duration < VIDEO_DURATION:
        background_clip = background_clip.loop(duration=VIDEO_DURATION)
    final_background = background_clip.subclip(0, VIDEO_DURATION).resize(height=1920).crop(x_center=background_clip.w/2, width=1080)
    
    final_background = final_background.resize(lambda t: 1 + 0.02 * t)
    final_background = final_background.crop(x_center=final_background.w / 2, y_center=final_background.h / 2, width=1080, height=1920)

    print(" Adding permanent heading...")
    heading_text = "Psychology Says"
    box_width = int(1080 * 0.7)
    box_height = 110
    vertical_pixel_position = int(1920 * 0.20)
    final_position = ('center', vertical_pixel_position)
    font_name = 'Arial-Rounded-MT-Bold' # Use the system-installed font name
    
    heading_bg = ColorClip(size=(box_width, box_height), color=(255, 255, 255)).set_position(final_position).set_duration(VIDEO_DURATION)
    heading_clip = TextClip(heading_text, fontsize=75, color='black', font=font_name, size=heading_bg.size).set_position(final_position).set_duration(VIDEO_DURATION)

    part1_duration = 6
    part2_start_time = 6
    part2_duration = 6
    
    quote_clip1 = TextClip(part1, fontsize=80, color='white', font=font_name, stroke_color='black', stroke_width=3,
                           size=(1080 * 0.9, None), method='caption')
    quote_clip1 = quote_clip1.set_position('center').set_duration(part1_duration).fx(vfx.fadein, 1).fx(vfx.fadeout, 0.5)

    quote_clip2 = TextClip(part2, fontsize=80, color='white', font=font_name, stroke_color='black', stroke_width=3,
                           size=(1080 * 0.9, None), method='caption')
    quote_clip2 = quote_clip2.set_position('center').set_start(part2_start_time).set_duration(part2_duration).fx(vfx.fadein, 0.5)

    print(" Compositing final video...")
    final_video = CompositeVideoClip(
        [final_background, heading_bg, heading_clip, quote_clip1, quote_clip2]
    ).set_duration(VIDEO_DURATION)
    
    final_video = final_video.set_audio(music_clip)
    final_video.write_videofile(output_filename, fps=24, codec='libx264', threads=4)
    print(f"✅ Video saved successfully as {output_filename}")
    
def log_to_sheet(part1: str, part2: str, title: str, filename: str, status: str):
    """Adds the details of the generated video to the Google Sheet."""
    print(f"✍️ Logging details to Google Sheet...")
    try:
        new_row = [part1, part2, title, filename, status]
        sheet.append_row(new_row)
        print("✅ Logged to Google Sheet successfully.")
    except Exception as e:
        print(f"⚠️ Could not log to Google Sheet. Details: {e}")

# --- MAIN EXECUTION BLOCK ---
if __name__ == "__main__":
    print("\n🚀 --- AI YouTube Shorts Factory ---")
    is_automated = setup_environment()
    if not verify_media_files():
        exit("❌ Cannot proceed without media files. Halting execution.")
    choice = get_user_choice()

    if choice in ['1', '2']:
        print("\n--- STAGE 1: GENERATING CONTENT ---")
        part1, part2, title = create_quote_content()
        if part1 == "Error":
            exit("❌ Failed to generate content from AI. Halting execution.")
        print(f"✅ Content Generated: {title}")

        print("\n--- STAGE 2: GENERATING VIDEO ---")
        timestamp = int(time.time())
        output_filename = f"quote_{timestamp}.mp4"
        generate_video_with_music(part1, part2, output_filename)

        upload_status = "Generated Locally"
        if choice == '2':
            print("\n--- STAGE 3: UPLOADING TO YOUTUBE ---")
            try:
                youtube = get_authenticated_service()
                print("✅ YouTube Authentication Successful.")

                description = f"""{part1} {part2}\n\n#shorts #ytshorts #psychology #psychologyfacts #humanbehavior #mindset"""
                base_tags = ["psychology", "facts", "shorts", "human behavior", "mindset", "life lessons"]
                ai_tags = generate_extra_tags(title, f"{part1} {part2}")
                final_tags = list(set(base_tags + ai_tags))

                print(f"🚀 Uploading '{output_filename}' to YouTube...")
                upload_video(
                    youtube,
                    file_path=output_filename,
                    title=title,
                    description=description,
                    tags=final_tags,
                    privacy_status="public"
                )
                upload_status = "Uploaded to YouTube"
                print("✅ Video Uploaded Successfully!")

            except Exception as e:
                print(f"❌ ERROR: YouTube upload failed. Details: {e}")
                upload_status = f"YouTube Upload Failed: {e}"

        print("\n--- STAGE 4: LOGGING TO GOOGLE SHEETS ---")
        log_to_sheet(part1, part2, title, output_filename, upload_status)
        print("\n✅ --- All tasks completed. ---")
    else:
        print("❌ Invalid choice. Please run again and enter 1 or 2.")
