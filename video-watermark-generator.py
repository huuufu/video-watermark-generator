import random
import re
import os
from moviepy.editor import VideoFileClip
from contextlib import contextmanager

target_texts = [
    "Your Watermark Text Here" #ウォーターマーク設定（複数可、自動ローテーション）
    #"Second Watermark",  # 複数のウォーターマークを追加可能
    #"Third Watermark",   # コンマで区切って追加
]

# コンテキストマネージャー
@contextmanager
def video_file_clip(filename):
    clip = VideoFileClip(filename)
    try:
        yield clip
    finally:
        clip.close()

# 解像度を取得
def get_ass_resolution(ass_file_path):
    with open(ass_file_path, "r", encoding="utf-8") as file:
        for line in file:
            if line.startswith("PlayResX:"):
                width = int(line.split(":")[1].strip())
            elif line.startswith("PlayResY:"):
                height = int(line.split(":")[1].strip())
        return width, height

def get_ass_files(directory):
    return [f for f in os.listdir(directory) if f.endswith('.ass')]

# ビデオプロパティを取得
def get_video_properties(mp4_file_path):
    try:
        with video_file_clip(mp4_file_path) as clip:
            duration = clip.duration
            width, height = clip.size
    except UnicodeDecodeError:
        print(f"UnicodeDecodeError: {mp4_file_path}")
        ass_file_path = os.path.splitext(mp4_file_path)[0] + ".ass"
        width, height = get_ass_resolution(ass_file_path)
        duration = 0

    if width >= height:  # 横画面
        aspect_ratio = width / height
        if 1.2 <= aspect_ratio <= 1.3:
            return duration, (1600, 1280)
        elif aspect_ratio > 1.75:
            return duration, (1920, 1080)
        else:
            return duration, (width, height)
    else:  # 縦画面
        return duration, (1080, 1920)

def select_random_point(points, avoid_points=[]):
    while True:
        point = random.choice(points)
        if point not in avoid_points:
            return point

def distance(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

# 対角位置を選択
def select_opposite_point(start_point, points_top, points_bottom, points_left, points_right):
    if start_point in points_top:
        return random.choice(points_bottom)
    elif start_point in points_bottom:
        return random.choice(points_top)
    elif start_point in points_left:
        return random.choice(points_right)
    elif start_point in points_right:
        return random.choice(points_left)

# 斜め位置を選択
def select_diagonal_point(start_point, points_top, points_bottom, points_left, points_right):
    if start_point in points_top:
        return random.choice(points_bottom[int(len(points_bottom)/2):])
    elif start_point in points_bottom:
        return random.choice(points_top[:int(len(points_top)/2)])
    elif start_point in points_left:
        return random.choice(points_right[:int(len(points_right)/2)])
    elif start_point in points_right:
        return random.choice(points_left[int(len(points_left)/2):])

def seconds_to_ass_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:01}:{minutes:02}:{seconds:02}.00"

# 重複チェック
def has_overlapping_dialogue(new_line, new_lines):
    def parse_ass_time(ass_time):
        parts = ass_time.split(':')
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2].split('.')[0])

    new_start, new_end = map(parse_ass_time, new_line.split(',')[1:3])
    for line in new_lines:
        start, end = map(parse_ass_time, line.split(',')[1:3])
        if (new_start < end) and (start < new_end):
            return True
    return False

# メイン処理
def add_watermark_to_ass():
    current_dir = os.getcwd()
    ass_files = [f for f in os.listdir(current_dir) if f.endswith('.ass')]

    for ass_file in ass_files:
        ass_file_path = os.path.join(current_dir, ass_file)
        mp4_file_path = os.path.splitext(ass_file_path)[0] + ".mp4"

        if not os.path.exists(mp4_file_path):
            continue

        with video_file_clip(mp4_file_path) as clip:
            video_duration, (video_width, video_height) = get_video_properties(mp4_file_path)

            min_move_distance = min(video_width, video_height) / 2
            edge_buffer = 10

            subtitle_height = min(70 if video_width < video_height else 55, video_height // 10)
            average_char_width = 40
            average_english_num_width = 20
            num_hanzi = 10
            num_english_num = 10
            subtitle_width = min(num_hanzi * average_char_width + num_english_num * average_english_num_width, video_width - 2 * edge_buffer)

            step = 50
            points_top = [(x, subtitle_height + edge_buffer) for x in range(subtitle_width // 2 + edge_buffer, video_width - subtitle_width // 2 - edge_buffer, step)]
            points_bottom = [(x, video_height - subtitle_height - edge_buffer) for x in range(subtitle_width // 2 + edge_buffer, video_width - subtitle_width // 2 - edge_buffer, step)]
            points_left = [(subtitle_width // 2 + edge_buffer, y) for y in range(subtitle_height + edge_buffer, video_height - subtitle_height - edge_buffer, step)]
            points_right = [(video_width - subtitle_width // 2 - edge_buffer, y) for y in range(subtitle_height + edge_buffer, video_height - subtitle_height - edge_buffer, step)]

            def select_random_point(avoid_points=[]):
                points = points_top + points_bottom + points_left + points_right
                available_points = [p for p in points if p not in avoid_points]
                if not available_points:
                    return None
                return random.choice(available_points)

            def select_opposite_point(start_point):
                if start_point in points_top:
                    return random.choice(points_bottom)
                elif start_point in points_bottom:
                    return random.choice(points_top)
                elif start_point in points_left:
                    return random.choice(points_right)
                elif start_point in points_right:
                    return random.choice(points_left)

            def select_diagonal_point(start_point):
                if start_point in points_top:
                    return random.choice(points_bottom[int(len(points_bottom)/2):])
                elif start_point in points_bottom:
                    return random.choice(points_top[:int(len(points_top)/2)])
                elif start_point in points_left:
                    return random.choice(points_right[:int(len(points_right)/2)])
                elif start_point in points_right:
                    return random.choice(points_left[int(len(points_left)/2):])

            with open(ass_file_path, "r", encoding="utf-8") as file:
                lines = file.readlines()

            if not lines[-1].endswith("\n"):
                lines[-1] += "\n"

            interval = 20  # ウォーターマークの移動間隔（秒）
            positions = []
            current_time = 0
            start_point = select_random_point()

            for i in range(int(video_duration // interval)):
                if i % 6 == 5:
                    end_point = select_opposite_point(start_point)
                elif i % 3 == 2:
                    end_point = select_diagonal_point(start_point)
                else:
                    attempts = 0
                    while attempts < 10:
                        end_point = select_random_point(avoid_points=[start_point])
                        if end_point and distance(start_point, end_point) >= min_move_distance:
                            break
                        attempts += 1
                    if attempts == 10:
                        end_point = start_point

                if end_point:
                    positions.append((current_time, start_point, end_point))
                    start_point = end_point
                current_time += interval

            remaining_time = video_duration - current_time
            if remaining_time > 0:
                if current_time % 6 == 5:
                    end_point = select_opposite_point(start_point)
                elif current_time % 3 == 2:
                    end_point = select_diagonal_point(start_point)
                else:
                    while True:
                        end_point = select_random_point(avoid_points=[start_point])
                        if distance(start_point, end_point) >= min_move_distance:
                            break
                positions.append((current_time, start_point, end_point))

            if positions:
                last_position = positions[-1]
                last_start_time = last_position[0]
                last_duration = video_duration - last_start_time
                final_end_time = last_start_time + int(last_duration / 2) if last_duration <= interval else last_start_time + int(interval / 2)
                positions[-1] = (last_start_time, last_position[1], last_position[2])

                new_lines = []
                for i, (start_time, start_point, end_point) in enumerate(positions):
                    end_time = min(start_time + interval, video_duration)
                    if i == len(positions) - 1:
                        end_time = final_end_time
                    move_duration = end_time - start_time
                    target_text = random.choice(target_texts)
                    new_line = f"Dialogue: 0,{seconds_to_ass_time(start_time)},{seconds_to_ass_time(end_time)},SY,,0000,0000,0000,,{{\\move({start_point[0]},{start_point[1]},{end_point[0]},{end_point[1]})}}{target_text}\n"
                    if not has_overlapping_dialogue(new_line, new_lines):
                        if start_time != end_time:
                            new_lines.append(new_line)

                with open(ass_file_path, "w", encoding="utf-8") as file:
                    events_found = False
                    styles_written = False
                    for line in lines:
                        if line.startswith("[Script Info]"):
                            file.write(line)
                            file.write(f"PlayResX: {video_width}\n")
                            file.write(f"PlayResY: {video_height}\n")
                        elif line.startswith("[V4+ Styles]"):
                            file.write(line)
                            styles_written = True
                        elif styles_written and line.startswith("Format:") and not "Style: SY" in lines:
                            file.write(line)
                            file.write("Style: SY,Noto Sans SC Black,55,&H99FFFFFF,&H99FFFFFF,&H00000000,&H1E6A5149,1,0,0,0,100.00,100.00,0.00,0.00,1,2.5,0.0,8,0,0,0,1\n")
                            styles_written = False
                        elif not (line.startswith("PlayResX:") or line.startswith("PlayResY:")):
                            file.write(line)
                        if "[Events]" in line:
                            events_found = True
                        elif events_found and line.startswith("Format:"):
                            for new_line in new_lines:
                                file.write(new_line)
                            events_found = False

                if events_found:
                    with open(ass_file_path, "a", encoding="utf-8") as file:
                        for new_line in new_lines:
                            file.write(new_line)

if __name__ == "__main__":
    add_watermark_to_ass() 