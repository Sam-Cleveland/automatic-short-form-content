from google.cloud import texttospeech
import random
from moviepy.editor import *

FEMALE = 'en-US-Standard-C'
MALE = 'en-US-Standard-D'

sentences = []
title = ''

client = texttospeech.TextToSpeechClient()
male = random.choice([True, False]) # Set 'male' to True or False randomly
if male:
    voice = texttospeech.VoiceSelectionParams(language_code="en-US",name=MALE)
else:
    voice = texttospeech.VoiceSelectionParams(language_code="en-US",name=FEMALE)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3,
    speaking_rate=1.2
)

# Generate title mp3 using tts and save to title.mp3
title_synthesis_input = texttospeech.SynthesisInput(text=title)
response = client.synthesize_speech(input=title_synthesis_input, voice=voice, audio_config=audio_config)
with open("title.mp3", "wb") as out:
    out.write(response.audio_content)
    print('Audio content written to file "title.mp3"')

# Generate audio file for every sentence
# Save to output[i].mp3 and save file names to sentence_files
# Create moviepy AudioFileClip object for each output file and save to audio_clips 
sentence_files =[]
audio_clips = []
print("Using TTS to generate audio files...")
for i, sentence in enumerate(sentences):
    synthesis_input = texttospeech.SynthesisInput(text=sentence)
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)

    with open("output"+str(i)+".mp3", "wb") as out:
        out.write(response.audio_content)
        print('Audio content written to file "output'+str(i)+'.mp3"')
    
    audio_clips.append(AudioFileClip("output"+str(i)+".mp3"))
    sentence_files.append("output"+str(i)+".mp3")

    print("Done with sentence " + str(i) + "/" + str(len(sentences)))

# Create AudioFileClip object for title
title = AudioFileClip("title.mp3")