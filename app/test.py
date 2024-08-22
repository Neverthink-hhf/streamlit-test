import streamlit as st
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import os
import threading
import time


@st.cache_resource
def get_recorder():
    return AudioRecorder()


class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.audio_data = []
        self.fs = 44100  # 采样率
        self.stream = None
        self.record_thread = None
        self.channels = 1  # 单声道
        self.volume = 0  # 用于存储当前音量

    def start_recording(self, device):
        self.is_recording = True
        self.audio_data = []
        try:
            self.stream = sd.InputStream(callback=self.audio_callback, channels=self.channels, samplerate=self.fs,
                                         device=device)
            self.stream.start()
            self.record_thread = threading.Thread(target=self._record)
            self.record_thread.start()
        except sd.PortAudioError as e:
            st.error(f"录音错误: {str(e)}")
            self.is_recording = False

    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        if self.record_thread:
            self.record_thread.join()
        self.save_audio()

    def audio_callback(self, indata, frames, time, status):
        if self.is_recording:
            self.audio_data.append(indata.copy())
            # 计算音量
            volume_norm = np.linalg.norm(indata) * 10
            self.volume = min(100, int(volume_norm))

    def _record(self):
        while self.is_recording:
            time.sleep(0.1)

    def save_audio(self):
        if len(self.audio_data) > 0:
            output_dir = '/Users/heihei/Downloads/test_audio'
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, 'recording.wav')
            audio_data = np.concatenate(self.audio_data)
            write(file_path, self.fs, audio_data)
            st.success(f"录音已保存到 {file_path}")


def get_audio_devices():
    return sd.query_devices()


# 初始化录音状态
if "is_recording" not in st.session_state:
    st.session_state.is_recording = False

recorder = get_recorder()

st.title("录音器")

devices = get_audio_devices()
device_names = [f"{i}: {device['name']}" for i, device in enumerate(devices)]
selected_device = st.selectbox("选择录音设备", device_names)
device_id = int(selected_device.split(":")[0])

if st.button("开始/停止录音"):
    if not st.session_state.is_recording:
        recorder.start_recording(device_id)
        st.session_state.is_recording = True
    else:
        recorder.stop_recording()
        st.session_state.is_recording = False

# 创建一个空的占位符用于显示音量
volume_placeholder = st.empty()
status_placeholder = st.empty()

# 使用一个单独的线程来更新音量显示
def update_volume():
    while st.session_state.is_recording:
        volume_placeholder.progress(recorder.volume)
        status_placeholder.write(f"正在录音... 当前音量: {recorder.volume}")
        time.sleep(0.1)

if st.session_state.is_recording:
    status_placeholder.write("正在录音...")
    if "volume_thread" not in st.session_state:
        st.session_state.volume_thread = threading.Thread(target=update_volume)
        st.session_state.volume_thread.start()
else:
    status_placeholder.write("未在录音")
    volume_placeholder.empty()

# 提供下载按钮
if not st.session_state.is_recording and len(recorder.audio_data) > 0:
    file_path = os.path.join('/Users/heihei/Downloads/test_audio', 'recording.wav')
    if os.path.exists(file_path):
        with open(file_path, 'rb') as file:
            st.download_button(label="下载录音文件", data=file, file_name='recording.wav')
