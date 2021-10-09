import logging
import threading
import time
import numpy
import ffmpeg
import wave
from io import BytesIO


import telegram.ext as tex

import mudeer.message
from mudeer.commands import Commands
from mudeer.com.types import Types


class Telegram(threading.Thread):
    """
    processes any Message (Text or speach) and forwards it to the Message pipeline.
    Speech is also processed to text, unsing TTS (e.g. DeepSpeech)
    """

    def __init__(self, com_id: int, settings: dict, name: str, stt, queue_in, queue_out):
        super().__init__()
        self.log = logging.getLogger(__name__)
        self.log.debug("init")

        tex_log = logging.getLogger("telegram.bot")
        tex_log.setLevel(logging.INFO)
        tex_log = logging.getLogger("telegram.ext.dispatcher")
        tex_log.setLevel(logging.INFO)

        self.com_id = com_id
        self.com_type = Types.MUMBLE

        # name
        self.user_name = name

        # stt
        self.stt = stt

        # in and out
        self.queue_in = queue_in  # queue.Queue()
        self.queue_out = queue_out

        self.log.debug("login with token {}".format(settings.get("token", "")))
        self.updater = tex.Updater(token=settings.get("token", ""), use_context=True)
        self.dispatcher = self.updater.dispatcher

        start_handler = tex.CommandHandler("start", self.get_callback_start)
        self.dispatcher.add_handler(start_handler)
        #stt_handler = tex.CommandHandler("stt", self.get_callback_stt)
        stt_handler = tex.MessageHandler(tex.Filters.voice, self.get_callback_stt)
        self.dispatcher.add_handler(stt_handler)

    def connect(self):
        self.updater.start_polling()

    def disconncet(self):
        self.updater.stop()

    def process(self, message: mudeer.message.Out):
        self.log.debug("got command {}".format(message.command))
        if message.command == Commands.MOVE_CHANNEL:
            self.move_to_channel(message.channel)
        elif message.command == Commands.SEND_MESSAGE:
            self.send_to_channel(message.message, message.channel)
        elif message.command == Commands.FOLLOW:
            self.update_follow(message.user)
        elif message.command == Commands.MOVE_USER:
            self.move_user(message.user, message.channel)

    def send_to_channel(self, message, channel: mudeer.message.Channel):
        pass

    def move_to_name(self, channel_name):
        pass

    def move_to_channel(self, channel: mudeer.message.Channel):
        pass

    def move_home(self):
        pass

    def move_user(self, user: mudeer.message.User, channel: mudeer.message.Channel):
        pass

    def update_follow(self, user: mudeer.message.User):
        pass

    def get_callback_start(self, update, context):
        self.log.debug("got event {}".format(update))
        context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

    def get_callback_stt(self, update, context):
        def normalize_audio(audio):
            out, err = (
                ffmpeg.input("pipe:0", format='ogg')
                .output(
                    "pipe:1",
                    f="WAV",
                    acodec="pcm_s16le",
                    ac=1,
                    ar="16k",
                    loglevel="error",
                    hide_banner=None,
                )
                .run(input=audio, capture_stdout=True, capture_stderr=True)
            )
            if err:
                raise Exception(err)
            return out

        self.log.debug("got event {}".format(update))
        mime = update.message.voice.mime_type
        self.log.debug("got voice:{}".format(mime))
        file_size = float(update.message.voice.file_size)
        self.log.debug("file size: {} MB".format(file_size/1024/1024))
        self.log.debug("get_file")

        file = update.message.voice.get_file()
        data = file.download_as_bytearray()
        self.log.debug("got file")

        audio = normalize_audio(data)
        audio = BytesIO(audio)
        with wave.Wave_read(audio) as wav:
            audio = numpy.frombuffer(wav.readframes(wav.getnframes()), numpy.int16)
        result = self.stt.process_voice_raw({"name": "tbd"}, audio)

        context.bot.send_message(chat_id=update.effective_chat.id, text=result)

    def check_audio(self):
        # I am pretty sure the GIL saves us:
        # `self.stream_frames` etc. is accessed by two threads (e.g. `get_callback_sound`)
        # obviously it isn't ... trying some locking. It might happen, that the dict `self.stream_last_frames`
        # is changed during processing.
        # The lock avoids this, but this does still not look very good.
        cur_time = time.time()
        to_process = []
        with self.stream_lock:
            for session_id, old_time in self.stream_last_frames.items():
                if (cur_time - old_time) < self.speech_return_delay or self.stream_frames[session_id] == []:
                    continue
                else:
                    data = numpy.concatenate(self.stream_frames[session_id], axis=0)
                    self.stream_frames[session_id] = []
                    user = self.stream_users[session_id]
                    to_process.append((data, user))

        for data, user in to_process:
            text = self.stt.process_voice(user, data, 48000)
            m_user = mudeer.message.User(user["name"], self.com_type, user)

            channel = self.bot.channels[user["channel_id"]]
            m_channel = mudeer.message.Channel(channel["name"], self.com_type, channel)
            message = mudeer.message.In(self.com_id, m_user, text, m_channel, data)
            self.queue_in.put(message)

    def run(self):
        self.running = True
        while self.running:
            self.check_audio()
            time.sleep(self.speech_return_delay)
