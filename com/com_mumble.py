import pymumble_py3 as pymumble
import time
import logging
import queue
import numpy
import threading
from pymumble_py3 import mumble_pb2


class ComMumble(threading.Thread):
    def __init__(self, user_name, host, port, home_channel, speech_return_delay=0.1, pymumble_loop_rate=0.05):
        super().__init__()
        self.log = logging.getLogger(__name__)

        self.user_name = user_name
        self.bot_name = self.user_name + "Bot"
        self.tag = "@" + self.user_name
        self.tag_len = len(self.tag)
        self.host = host
        self.port = port
        self.home = home_channel
        self.speech_return_delay = speech_return_delay
        self.pymumble_loop_rate = pymumble_loop_rate

        self.commands = queue.Queue()

        self.bot = pymumble.Mumble(self.host, self.bot_name, port=self.port, debug=False)
        self.bot.set_receive_sound(1)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_TEXTMESSAGERECEIVED, self.get_callback_text)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_USERUPDATED, self.get_callback_user)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_USERCREATED, self.get_callback_user)
        self.bot.callbacks.set_callback(pymumble.constants.PYMUMBLE_CLBK_SOUNDRECEIVED, self.get_callback_sound)

        self.stream_frames = {}
        self.stream_last_frames = {}
        self.stream_users = {}

    def get_tag(self):
        return self.tag

    def connect(self):
        self.bot.start()
        self.bot.is_ready()
        self.bot.set_loop_rate(self.pymumble_loop_rate)

        self.log.debug("loop rate at: {}".format(self.bot.get_loop_rate()))
        self.move_home()

    def disconncet(self):
        self.running = False
        self.bot.stop()

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

    def get_callback_user(self, user, changes=None):
        self.log.debug("received user change: {}".format(user))
        self.commands.put_nowait(("user", user))

    def get_callback_text(self, text_message: mumble_pb2.TextMessage):
        if (self.tag == text_message.message[:self.tag_len]):
            self.log.debug("received command: {}".format(text_message.message))
            self.commands.put_nowait(("message", text_message))

    def get_callback_sound(self, user, soundchunk):
        # I am pretty sure the GIL saves us:
        # `self.stream_frames` etc. is accessed by two threads (e.g. `check_audio`)
        session_id = user["session"]
        #self.log.debug("Got something from {}".format(user["name"]))

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
        cur_time = time.time()
        for session_id, old_time in self.stream_last_frames.items():
            if (cur_time - old_time) < self.speech_return_delay or self.stream_frames[session_id] == []:
                continue
            else:
                data = numpy.concatenate(self.stream_frames[session_id], axis=0)
                self.stream_frames[session_id] = []
                self.commands.put_nowait(("sound", (self.stream_users[session_id], data)))

                # # https://stackoverflow.com/questions/30619740/downsampling-wav-audio-file
                # number_of_samples = round(len(data) * float(16000) / 48000)
                # data = scipy.signal.resample(data, number_of_samples)
                # data = numpy.around(data).astype(numpy.int16)
                # self.log.debug("data {} {}".format(data.min(), data.max()))
                # text = self.deepspeech.stt(data)
                # self.log.debug("Understood: {}".format(text))

    def get_next_command(self, timeout):
        """Waits for the next command.

        @param timeout befor the command returns an None
        @return returns one of the following commands:
            ("message", <message_content>)
            ("user", <user_changes>)
            ("sound", (<user>, <numpy_sound_chunk>))
        """
        try:
            command = self.commands.get(timeout=timeout)
        except queue.Empty:
            command = None
        return command

    def run(self):
        self.running = True
        while self.running:
            self.check_audio()
            time.sleep(self.speech_return_delay)
