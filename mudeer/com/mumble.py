import pymumble_py3 as pymumble
import time
import logging
import queue
import numpy
import threading

from pymumble_py3 import mumble_pb2

import mudeer.message
from mudeer.commands import Commands


class Mumble(threading.Thread):
    def __init__(self, com_id: int, settings: dict, name: str, stt, queue_in, queue_out):
        super().__init__()
        self.log = logging.getLogger(__name__)

        self.com_id = com_id

        # name
        self.user_name = name
        self.bot_name = self.user_name + "Bot"
        self.tag = "@" + self.user_name
        self.tag_len = len(self.tag)

        # stt
        self.stt = stt

        # in and out
        self.queue_in = queue_in  # queue.Queue()
        self.queue_out = queue_out

        # settings
        self.host = settings.get("host", "")
        self.port = settings.getint("port", 64738)
        self.home = settings.get("home_channel", "Bot Home")
        self.speech_return_delay = settings.getfloat("speech_return_delay", 0.1)
        self.pymumble_loop_rate = settings.getfloat("pymumble_loop_rate", 0.05)
        self.follow = settings.get("follow", None)

        # set up
        self.bot = pymumble.Mumble(self.host, self.bot_name, port=self.port, debug=False)
        self.bot.set_receive_sound(1)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, self.get_callback_text)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_USERUPDATED, self.get_callback_user)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_USERCREATED, self.get_callback_user)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, self.get_callback_sound)

        self.stream_lock = threading.RLock()
        self.stream_frames = {}
        self.stream_last_frames = {}
        self.stream_users = {}

    def get_tag(self):
        return self.tag

    def connect(self):
        self.bot.start()
        self.bot.is_ready()
        self.bot.set_loop_rate(self.pymumble_loop_rate)
        self.start()

        self.log.debug("loop rate at: {}".format(self.bot.get_loop_rate()))
        self.move_home()

    def disconncet(self):
        self.running = False
        self.bot.stop()

    def process(self, message: mudeer.message.Out):
        if message.command == Commands.MOVE_CHANNEL:
            self.move_to_id(message.channel)
            # check if this works

    def move_to_name(self, channel_name):
        try:
            channel = self.bot.channels.find_by_name(channel_name)
            channel.move_in()
            time.sleep(0.1)  # ok for now, but check for callback
            self.log.debug("moved to channel {}".format(self.bot.my_channel()))
        except pymumble.errors.UnknownChannelError as err:
            self.log.error(err)

    def move_to_id(self, channel_id):
        try:
            channel = self.bot.channels[channel_id]
            channel.move_in()
            time.sleep(0.1)  # ok for now, but check for callback
            self.log.debug("moved to channel {}".format(self.bot.my_channel()))
        except pymumble.errors.UnknownChannelError as err:
            self.log.error(err)

    def move_home(self):
        self.move_to_name(self.home)

    def update_follow(self, user):
        if user:
            self.follow = user["name"]
        else:
            self.follow = None
        self.log.debug("follow user: {}".format(self.follow))

        if self.follow is None:
            self.move_home()
            self.log.debug("Move Home")
        else:
            self.move_to_id(user["channel_id"])

    def get_callback_user(self, user, changes=None):
        self.log.debug("received user change: {}".format(user))
        if self.follow:
            if user["name"] == self.follow:
                self.log.debug("follow user: {}".format(user))
                message = mudeer.message.Out(self.com_id, Commands.MOVE_CHANNEL, None, None, user["channel_id"])
                self.queue_out.put(message)
        message = mudeer.message.In(self.com_id, user)
        self.queue_in.put(message)

    def get_callback_text(self, text_message: mumble_pb2.TextMessage):
        if (self.tag == text_message.message[:self.tag_len]):
            self.log.debug("received command: {}".format(text_message.message))
            user = text_message.actor
            channel = text_message.channel_id

            # TODO From Here
            message = mudeer.message.In(self.com_id, user, text_message, channel)
            self.queue_in.put(message)

    def get_callback_sound(self, user, soundchunk):
        # I am pretty sure the GIL saves us:
        # `self.stream_frames` etc. is accessed by two threads (e.g. `check_audio`)
        session_id = user["session"]
        #self.log.debug("Got something from {}".format(user["name"]))

        with self.stream_lock:
            if session_id not in self.stream_frames:
                self.stream_frames[session_id] = []
                self.stream_users[session_id] = user

            self.stream_frames[session_id].append(numpy.frombuffer(soundchunk.pcm, numpy.int16))
            self.stream_last_frames[session_id] = time.time()  # soundchunk.timestamp does not work

    def send_to_channels(self, channels, message):
        send_message = ""
        if isinstance(message, list):
            for elem in message:
                send_message += "<br />" + elem
        else:
            send_message = message

        for channel_id in channels:
            channel = self.bot.channels[channel_id]
            channel.send_text_message(send_message)

    def send_to_my_channel(self, message):
        send_message = ""
        if isinstance(message, list):
            for elem in message:
                send_message += "<br />" + elem
        else:
            send_message = message

        self.bot.my_channel().send_text_message(send_message)

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
            message = mudeer.message.In(self.com_id, user, text, None, data)
            self.queue_in.put(message)

    def run(self):
        self.running = True
        while self.running:
            self.check_audio()
            time.sleep(self.speech_return_delay)
