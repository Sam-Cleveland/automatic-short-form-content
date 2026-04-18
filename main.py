import html
import random
import requests
import re
import os
import sys
import time
import torch
import traceback
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from moviepy.video.fx.all import *
from moviepy.editor import *
from TTS.api import TTS
from PIL import ImageFont, ImageDraw, Image, ImageFilter
# Pillow 10+ removed ANTIALIAS; patch it back for moviepy 1.x compatibility
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

# STOCK = "RPReplay_Final1705472058.MOV"
# TEXT = open("script.txt", "r").read()
# TITLE = 'AITA for telling my sister she is no longer the it-girl?'

def pop(t):
    """fades in"""
    out = (40*t) if t < 0.025 else 1
    out  = 0.1 if out < 0.1 else out
    return out

def wrap_text(text, font, draw, max_width):
    lines = []
    words = text.split(' ')
    current_line = words[0]
    for word in words[1:]:
        # If adding this word to the current line would exceed the max width,
        # start a new line
        if draw.textlength(' '.join([current_line, word]), font=font) > max_width:
            lines.append(current_line)
            current_line = word
        else:
            # Otherwise, add the word to the current line
            current_line = ' '.join([current_line, word])
    lines.append(current_line)
    return lines

def create_title(title):
    W = 720
    RW = W*0.73
    RO = (W-RW)/2
    SW = W*0.75
    SO = (W-SW)/2

    text = title
    font = ImageFont.truetype("/Library/Fonts/SF-Pro-Rounded-Semibold.otf", 55)
    shadow_color = (0, 0, 0, 128)
    rectangle_color = (255, 255, 255, 255)
    radius = 80

    image = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    p_height = 51.2 * len(wrap_text(text, font, draw, RW*0.85))

    # Draw the shadow
    draw.rounded_rectangle([(SO, SO), (SO+SW, SO+p_height+190 + SW-RW)], fill=shadow_color, radius=radius)
    image = image.filter(ImageFilter.GaussianBlur(5))
    draw = ImageDraw.Draw(image)

    # Draw the rectangle
    draw.rounded_rectangle([(RO, RO), (RO+RW, RO+p_height+190)], fill=rectangle_color, radius=radius)

    # Wrap the text
    wrapped_text = wrap_text(text, font, draw, RW*0.85)

    # Draw each line of the wrapped text
    y_text = W*0.3
    x_text = W*0.2
    for line in wrapped_text:
        height = draw.textbbox((0,0), line, font=font)[3]
        draw.text((x_text, y_text), line, font=font, fill=(0, 0, 0, 255))
        y_text += height*0.8

    user = Image.open("user.png")
    user = user.resize((int(user.size[0]*W*0.00115), int(user.size[1]*W*0.00115)))
    image.paste(user, (int(W*0.16), int(W*0.17)), user)

    comments = Image.open("likes_comments.png")
    comments = comments.resize((int(comments.size[0]*W*0.001), int(comments.size[1]*W*0.001)))
    image.paste(comments, (int(W*0.2), int(p_height+230)), comments)

    image = image.crop((SO-10, SO-10, SO+SW+10, SO+p_height+190 + SW-RW+10))
    image.save('post_title.png')

def create_video(script, title, stock):
    censor = {
        'asshole': 'a**hole',
        'porn': 'p*rn',
        'fuck': 'f***',
        'shit': 'sh**',
        'damn': 'd*mn',
        'bitch': 'b*tch',
        'cunt': 'c*nt',
        'dick': 'd***',
        'weed': 'w***',
        'sex': 's*x',
        'suicid': 'suic*d',
        'penis': 'pen*s',
        'cum': 'c*m',
        'horny': 'h*rny',
        'jizz': 'j*zz',
    }
     # Slang replacements
    slang = {
        'AITAH': 'Am I the A-hole here',
        'AITA': 'Am I the A-hole',
        'PP': 'Post Partum',
        'SIL': 'Sister-in-law',
        'MIL': 'Mother-in-law',
        'FIL': 'Father-in-law',
        'DIL': 'Daughter-in-law',
        '[NF]': '',
        'NF': '',
        'TIFU': 'Today I Effed Up'
    }
    tts_fixes = {
        '\.\.[\.]*': ',',
    }
    
    # Replace censor words, slang words and tts fixes
    title_text = title
    for key in slang:
        title = re.sub(r'\b' + re.escape(key) + r'\b', slang[key], title, flags=re.IGNORECASE)
        script = re.sub(r'\b' + re.escape(key) + r'\b', slang[key], script, flags=re.IGNORECASE)
    for key in tts_fixes:
        title = re.sub(key, tts_fixes[key], title)
        script = re.sub(key, tts_fixes[key], script)
    for key in censor:
        title_text = re.sub(re.escape(key), censor[key], title, flags=re.IGNORECASE)

    # Process body text
    script = html.unescape(script)
    script = script.replace('&#x200B;', '')
    script = re.split(r'\n(?:tl[;.\/]?dr|edit|update|info|summary)', script, flags=re.IGNORECASE)[0]
    script.replace('\n', ' ')

    # Split by sentences
    sentences = [sentence.strip() for sentence in re.split(r'(?<=[^A-Z].[.?!])', script) if not (len(sentence) == 0 or sentence.isspace())]
    for sentence in sentences:
        print(sentence)

    # Create title and prepare stock clip
    create_title(title_text)
    title_clip = ImageClip("post_title.png")
    clip = VideoFileClip(stock).without_audio()

    # Config tts client
    os.environ["COQUI_TOS_AGREED"] = "1"
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
    speaker_wav = "en_uk_003.mp3"

    # Config speech to text client
    if torch.cuda.is_available():
        device = "cuda:0"
        torch_dtype = torch.float16
    elif torch.backends.mps.is_available():
        device = "mps"
        torch_dtype = torch.float32
    else:
        device = "cpu"
        torch_dtype = torch.float32
    model_id = "openai/whisper-small"
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)
    processor = AutoProcessor.from_pretrained(model_id)
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        chunk_length_s=30,
        batch_size=16,
        return_timestamps=True,
        torch_dtype=torch_dtype,
        device=device,
    )

    # Generate title mp3 using tts and save to title.mp3
    tts.tts_to_file(
        text=title, 
        speaker_wav=speaker_wav,  # Reference audio file for the speaker
        language="en",  # Set the language to English
        file_path="title.wav"  # Output audio file path
    )
    title = AudioFileClip("title.wav")
    print('Audio content written to file "title.wav"')

    sentence_files = []
    audio_clips = []
    print("Using TTS to generate audio files...")
    for i, sentence in enumerate(sentences):
        tts.tts_to_file(
            text=sentence, 
            speaker_wav=speaker_wav,  # Reference audio file for the speaker
            language="en",  # Set the language to English
            file_path="output"+str(i)+".wav"  # Output audio file path
        )
        print('Audio content written to file "output'+str(i)+'.wav"')
        audio_clips.append(AudioFileClip("output"+str(i)+".wav"))
        sentence_files.append("output"+str(i)+".wav")
        print("Done with sentence " + str(i+1) + "/" + str(len(sentences)))

    # Concatenate audio clips and combine stock and audio
    script = concatenate_audioclips(audio_clips)
    audio = concatenate_audioclips([title, script])
    duration = audio.duration
    if (clip.duration < duration):
        print ("Video is too short for audio. Exiting...")
        sys.exit(1)
    audio = audio.subclip(0, duration)
    clip = clip.subclip(0, duration)
    video = clip.set_audio(audio)

    # Center and set duration for title clip
    title_clip = title_clip.set_duration(title.duration).set_position('center')

    # Run inference on each of sentence_files and show the result
    words = []
    offset = 0
    print("Generating captions for audio files...")
    concat = ''
    for i, sentence in enumerate(sentence_files):
        result = pipe(sentence, return_timestamps="word")
        for word in result['chunks']:
            ts = word['timestamp']
            if ts[0] is None or ts[1] is None:
                continue
            new_timestamp = (ts[0] + offset, ts[1] + offset)
            word['timestamp'] = new_timestamp
            words.append(word)
            concat += word['text'] + ' '
        offset += audio_clips[i].duration

        print("Done with sentence " + str(i+1) + "/" + str(len(sentence_files)))
    # with open('script_out.txt', 'w') as f:
    #     f.write(concat)

    # Clean up output files
    for sentence in sentence_files:
        os.remove(sentence)

    clips = []
    for word in words:
            text = word['text'].strip()
            # Censor if necessary
            for key in censor:
                text = re.sub(re.escape(key), censor[key], text, flags=re.IGNORECASE)
            start = word['timestamp'][0] + title.duration
            end = word['timestamp'][1] + title.duration
            txt_clip = TextClip(text, fontsize=120, color='white', stroke_width=3, stroke_color='black', font='Bangers-Regular.ttf')
            txt_clip = txt_clip.resize(pop);
        
            txt_clip = txt_clip.set_start(start).set_end(end)
            txt_clip = txt_clip.set_pos(("center", "center"))  # Position the text at the center and 70% down the video
            clips.append(txt_clip)


    final = CompositeVideoClip([video, title_clip] + clips)
    final = final.set_audio(audio)
    final.duration = duration
    # Creete file name from title
    title_text = re.sub(r'[^a-zA-Z0-9_.-]', '', title_text)
    final.write_videofile("output/"+title_text+".mp4", fps=60, audio_codec='aac')

def scrape_reddit_page(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    json = requests.get(url + '.json', headers=headers)
    print ('Returned with status: ' + str(json.status_code))
    if json.status_code == 429:
        print('Rate limited. Waiting 3 seconds...')
        time.sleep(3)
        return scrape_reddit_page(url)
    if json.status_code != 200:
        print(json.text)
        sys.exit(1)

    json = json.json()

    title = json[0]['data']['children'][0]['data']['title']
    text = json[0]['data']['children'][0]['data']['selftext']

    return title, text

if __name__ == "__main__":
    # get url from sys args
    if (len(sys.argv) >= 2):
        url = sys.argv[1]
        title, text = scrape_reddit_page(url)

        # pick a random file from stock/
        stock = 'stock/' + random.choice(os.listdir("stock/"))
        print(stock)
        create_video(text, title, stock)
    else:
        with open('urls.txt', 'r') as f:
            urls = f.readlines()
            for url in urls:
                try:
                    print ('Creating video for ' + url)
                    title, text = scrape_reddit_page(url)
                    stock = 'stock/' + random.choice(os.listdir("stock/"))
                    print(stock)
                    create_video(text, title, stock)
                except Exception as e:
                    print("Error with " + url + ":")
                    print(e)
                    print(traceback.format_exc())
                    continue