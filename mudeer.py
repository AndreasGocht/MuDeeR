import configparser
import logging
import time
import collections
import traceback
import gettext
import os

import com.com_mumble as com_mumble
import voice.voice_deep_speech as voice_deep_speech
import commands

config = configparser.ConfigParser()

try:
    with open("config.cfg") as f:
        config.read_file(f)
except FileNotFoundError as e:
    logging.fatal("did not find config file:\n{}".format(e))
    exit(-1)

logging.basicConfig(level=config["logging"].get("level", "INFO"))

local_path = os.path.realpath(__file__)
local_path = os.path.split(local_path)[0] + "/locales"

text = gettext.translation("commands", localedir=local_path, languages=[config["server"]["lang"]], fallback=True)
text.install()


class MuDeer():
    def __init__(self):
        self.log = logging.getLogger(__name__)

        self.name = config["server"]["user"]
        self.log.debug("Init Mumble")
        self.com = com_mumble.ComMumble(
            self.name,
            config["server"]["host"],
            int(config["server"]["port"]),
            config["server"]["home_channel"])
        self.tag = self.com.get_tag()
        self.tag_len = len(self.tag)

        self.log.debug("Init DeepSpeech")
        self.voice = voice_deep_speech.VoiceDeepSpeech(
            config["deepspeech"]["model"],
            config["deepspeech"]["scorer"],
            config["deepspeech"]["record_wav"].lower() == "true",
            config["deepspeech"]["record_user"].split(","))

        self.commands = commands.Command([self.name, self.tag])
        self.commands_to_process = collections.deque()

        available_commands = self.commands.get_available_commands()
        self.voice.add_hot_words(available_commands)
        self.voice.add_hot_words([self.name.lower()], 20)

        self.follow = config["users"].get("follow", None)

    def connect(self):
        self.com.start()
        self.com.connect()
        self.com.move_home()

    def disconncet(self):
        self.com.disconncet()

    def update_follow(self, user):
        if user:
            self.follow = user["name"]
        else:
            self.follow = None
        self.log.debug("follow user: {}".format(self.follow))

        if self.follow is None:
            self.com.move_home()
            self.log.debug("Move Home")
        else:
            self.com.move_to_id(user["channel_id"])

        # TODO save changes

    def send_error(self, channel_id, message=None):
        if message:
            self.com.send_to_channels(channel_id, message)
        else:
            self.com.send_to_channels(channel_id, "Fatal Error")

    def excecute_command(self, command_items=[], channel_id=None, user=None):
        self.commands_to_process.extend(command_items)
        while True:
            try:
                command_item = self.commands_to_process.popleft()
            except IndexError:
                break

            try:
                command, item = command_item
                if command == "message":
                    if channel_id:
                        self.com.send_to_channels(channel_id, item)
                    else:
                        self.com.send_to_my_channel(item)  # quick fix
                elif command == "error":
                    self.send_error(channel_id, item)
                elif command == "follow":
                    self.update_follow(item)
                elif command == "wait":
                    time.sleep(item)
                    return  # return to main loop for any processing
                elif command is None:
                    pass
            except Exception as e:
                tb = traceback.format_exc()
                self.log.error("Can not process Command {}.\nGot Exception: {}\n{}".format(command_item, e, tb))

    def process_messages(self, item):
        self.log.debug("Message ({}): {}".format(item.channel_id, item))
        new_commands = self.commands.process_text(item.message)
        self.log.debug("Message commands {}".format(new_commands))
        self.excecute_command(new_commands, channel_id=item.channel_id)

    def process_users(self, user):
        if self.follow:
            if user["name"] == self.follow:
                self.log.debug("follow user: {}".format(user))
                self.com.move_to_id(user["channel_id"])
        new_commands = self.commands.process_user(user)
        self.log.debug("User commands {}".format(new_commands))
        self.excecute_command(new_commands)

    def process_sound(self, user, sound_chunk):
        text = self.voice.process_voice(user, sound_chunk)
        new_commands = self.commands.process_text(text)
        self.log.debug("Sound commands {}".format(new_commands))
        self.excecute_command(new_commands)

    def run(self):
        while True:
            if len(self.commands_to_process) > 0:
                self.excecute_command()
            command = self.com.get_next_command(timeout=0.01)
            if command:
                t, item = command
                if t == "message":
                    self.process_messages(item)
                elif t == "user":
                    self.process_users(item)
                elif t == "sound":
                    self.process_sound(*item)


if __name__ == "__main__":
    mu_deer = MuDeer()
    mu_deer.connect()
    try:
        mu_deer.run()
    except KeyboardInterrupt:
        pass
    finally:
        mu_deer.disconncet()
