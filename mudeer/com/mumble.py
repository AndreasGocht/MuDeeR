import pymumble_py3 as pymumble
import time
import logging
import queue
import numpy
import threading

from pymumble_py3 import mumble_pb2

import mudeer.message
from mudeer.commands import Commands
from mudeer.com.types import Types


class Mumble(threading.Thread):
    """
    processes any Message (Text or speach) and forwards it to the Message pipeline.
    Speech is also processed to text, unsing TTS (e.g. DeepSpeech)
    """
    def __init__(self, com_id: int, settings: dict, name: str, stt, queue_in, queue_out):
        super().__init__()
        self.log = logging.getLogger(__name__)

        self.com_id = com_id
        self.com_type = Types.MUMBLE

        # name
        self.user_name = name

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
        self.cert_file = settings.get("cert_file", None)
        self.key_file = settings.get("key_file", None)
        self.log.debug("self.cert_file: {}".format(self.cert_file))
        self.log.debug("self.key_file: {}".format(self.key_file))

        # set up
        self.log.debug("log into mumule server {}:{} with name {}".format(self.host, self.port, self.user_name))
        self.bot = pymumble.Mumble(self.host, self.user_name, port=self.port,
                                   certfile=self.cert_file, keyfile=self.key_file, debug=False)
        self.bot.set_receive_sound(1)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, self.get_callback_text)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_USERUPDATED, self.get_callback_user)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_USERCREATED, self.get_callback_user)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, self.get_callback_sound)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELCREATED,
                                        self.get_callback_channel_create)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELUPDATED,
                                        self.get_callback_channel_update)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_CHANNELREMOVED,
                                        self.get_callback_channel_delete)

        self.stream_lock = threading.RLock()
        self.stream_frames = {}
        self.stream_last_frames = {}
        self.stream_users = {}

    def check_and_register(self):
        if self.key_file:
            if "user_id" not in self.bot.users.myself:
                self.log.info("Registerd myself.")
                self.bot.users.myself.register()

    def get_tag(self):
        return self.tag

    def connect(self):
        self.bot.start()
        self.bot.is_ready()
        self.bot.set_loop_rate(self.pymumble_loop_rate)
        self.start()

        self.check_and_register()

        self.log.debug("loop rate at: {}".format(self.bot.get_loop_rate()))
        self.move_home()

    def disconncet(self):
        self.running = False
        self.bot.stop()

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
        send_message = ""
        if isinstance(message, list):
            for elem in message:
                send_message += "<br />" + elem
        else:
            send_message = message

        if channel:
            channel.raw_data.send_text_message(send_message)
        else:
            self.bot.my_channel().send_text_message(send_message)

    def move_to_name(self, channel_name):
        try:
            channel = self.bot.channels.find_by_name(channel_name)
            channel.move_in()
            time.sleep(0.1)  # ok for now, but check for callback
            self.log.debug("moved to channel {}".format(self.bot.my_channel()))
        except pymumble.errors.UnknownChannelError as err:
            self.log.error(err)

    def move_to_channel(self, channel: mudeer.message.Channel):
        try:
            channel.raw_data.move_in()
            time.sleep(0.1)  # ok for now, but check for callback
            self.log.debug("moved to channel {}".format(channel))
        except pymumble.errors.UnknownChannelError as err:
            self.log.error(err)

    def move_home(self):
        self.move_to_name(self.home)

    def move_user(self, user: mudeer.message.User, channel: mudeer.message.Channel):
        channel.raw_data.move_in(user.raw_data["session"])
        self.log.debug("move user {} to channel {}".format(user.name, channel.name))

    def update_follow(self, user: mudeer.message.User):
        if user:
            self.follow = user.raw_data["name"]
        else:
            self.follow = None
        self.log.debug("follow user: {}".format(self.follow))

        if self.follow is None:
            self.move_home()
            self.log.debug("Move Home")
        else:
            channel = self.bot.channels[user.raw_data["channel_id"]]
            channel = mudeer.message.Channel(channel["name"], self.com_type, channel)
            self.move_to_channel(channel)

    def get_callback_user(self, user, changes=None):
        self.log.debug("received user change: {}".format(user))
        if self.follow:
            if user["name"] == self.follow:
                self.log.debug("follow user: {}".format(user))
                channel = self.bot.channels[user["channel_id"]]
                channel = mudeer.message.Channel(channel["name"], self.com_type, channel)
                message = mudeer.message.Out(self.com_id, Commands.MOVE_CHANNEL, None, None, channel)
                self.queue_out.put(message)

        user = mudeer.message.User(user["name"], self.com_type, user)
        message = mudeer.message.In(self.com_id, user)
        self.queue_in.put(message)

    def get_callback_text(self, text_message: mumble_pb2.TextMessage):
        self.log.debug("received command: {}".format(text_message.message))

        user = self.bot.users[text_message.actor]
        channel = self.bot.channels[text_message.channel_id[0]]  # why ever this is a list (maybe global comm?)

        user = mudeer.message.User(user["name"], self.com_type, user)
        channel = mudeer.message.Channel(channel["name"], self.com_type, channel)
        message = mudeer.message.In(self.com_id, user, text_message.message, channel)
        self.queue_in.put(message)

    def get_callback_sound(self, user, soundchunk):
        # I am pretty sure the GIL saves us:
        # `self.stream_frames` etc. is accessed by two threads (e.g. `check_audio`)
        session_id = user["session"]
        # self.log.debug("Got something from {}".format(user["name"]))

        with self.stream_lock:
            if session_id not in self.stream_frames:
                self.stream_frames[session_id] = []
                self.stream_users[session_id] = user

            self.stream_frames[session_id].append(numpy.frombuffer(soundchunk.pcm, numpy.int16))
            self.stream_last_frames[session_id] = time.time()  # soundchunk.timestamp does not work

    def get_callback_channel_create(self, channel):
        user = mudeer.message.User(self.user_name, self.com_type, self.bot.users.myself)
        channel = mudeer.message.Channel(channel["name"], self.com_type, channel)
        message = mudeer.message.In(self.com_id, user, None, channel)
        self.queue_in.put(message)

    def get_callback_channel_update(self, channel, action):
        user = mudeer.message.User(self.bot.users.myself["name"], self.com_type, self.bot.users.myself)
        channel = mudeer.message.Channel(channel["name"], self.com_type, channel)
        message = mudeer.message.In(self.com_id, user, None, channel)
        self.queue_in.put(message)

    def get_callback_channel_delete(self, channel):
        self.log.error("deleting channels not implemented!")

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
