from moviepy.editor import *
from datetime import datetime

# Get every file with 'stock' in the name
stocks = [f for f in os.listdir("/Users/samcleveland/Documents/Automatic Short-Form Content") if 'stock' in f and '.mp4' in f]
print (stocks)
for stock in stocks:
    try:
        video = VideoFileClip(stock)
        video = video.subclip(30, video.duration)

        video = video.resize(height=1280)  # Resize the video to the desired height while maintaining the aspect ratio
        if video.w > 720:  # If the width is more than 720 after resizing, crop the excess width
            video = video.crop(x_center=video.w/2, width=720)  # Crop the video around the center to the desired width

        clips_num = int(video.duration/150)
        start_inc = (video.duration-300)/clips_num
        for i in range(clips_num):
            try:
                clip = video.subclip(i*start_inc, i*start_inc+300)
                time = datetime.now().strftime('%H%M%S')
                clip.write_videofile(f"stock/clip{time}.mp4", fps=60, threads=10)
            except Exception as e:
                print(e)
                continue
    except Exception as e:
        print(e)
        continue