import logging
import time
import collections
import traceback
import os
import queue

import mudeer.com
import mudeer.skills
import mudeer.voice.voice_deep_speech as voice_deep_speech
import mudeer.commands as commands


class MuDeer():
    def __init__(self, config):
        self.log = logging.getLogger(__name__)

        self.name = config["etc"]["name"]

        self.log.debug("Init DeepSpeech")
        self.stt = voice_deep_speech.VoiceDeepSpeech(
            config["deepspeech"]["model"],
            config["deepspeech"]["scorer"],
            config["deepspeech"]["record_wav"].lower() == "true",
            config["deepspeech"]["record_user"].split(","))
        self.stt.add_hot_words([self.name.lower()], 20)

        self.log.debug("Init Mumble")

        self.queue_in = queue.Queue()
        self.queue_out = queue.Queue()
        self.coms = mudeer.com.Coms({"mumble": config["mumble"]}, self.name,
                                    self.stt, self.queue_in, self.queue_out)

        self.skills = mudeer.skills.Skills(self.name, self.queue_in, self.queue_out, self.stt, config)

    def connect(self):
        self.coms.connect()

    def disconncet(self):
        self.coms.disconncet()

        # TODO save changes

    # def send_error(self, channel_id, message=None):
    #     if message:
    #         self.com.send_to_channels(channel_id, message)
    #     else:
    #         self.com.send_to_channels(channel_id, "Fatal Error")

    # def excecute_command(self, command_items=[], channel_id=None, user=None):
    #     pass
    #     self.commands_to_process.extend(command_items)
    #     while True:
    #         try:
    #             command_item = self.commands_to_process.popleft()
    #         except IndexError:
    #             break

    #         try:
    #             command, item = command_item
    #             if command == "message":
    #                 if channel_id:
    #                     self.com.send_to_channels(channel_id, item)
    #                 else:
    #                     self.com.send_to_my_channel(item)  # quick fix
    #             elif command == "error":
    #                 self.send_error(channel_id, item)
    #             elif command == "wait":
    #                 time.sleep(item)
    #                 return  # return to main loop for any processing
    #             elif command is None:
    #                 pass
    #         except Exception as e:
    #             tb = traceback.format_exc()
    #             self.log.error("Can not process Command {}.\nGot Exception: {}\n{}".format(command_item, e, tb))

    # def process_messages(self, item):
    #     self.log.debug("Message ({}): {}".format(item.channel_id, item))
    #     new_commands = self.commands.process_text(item.message)
    #     self.log.debug("Message commands {}".format(new_commands))
    #     self.excecute_command(new_commands, channel_id=item.channel_id)

    # def process_users(self, user):
    #     new_commands = self.commands.process_user(user)
    #     self.log.debug("User commands {}".format(new_commands))
    #     self.excecute_command(new_commands)

    # def process_sound(self, user, sound_chunk):
    #     text = self.voice.process_voice(user, sound_chunk)
    #     new_commands = self.commands.process_text(text)
    #     self.log.debug("Sound commands {}".format(new_commands))
    #     self.excecute_command(new_commands)

    def run(self):
        while True:
            time.sleep(0.01)
            self.coms.process()
            self.skills.process()

            # if len(self.commands_to_process) > 0:
            #     self.excecute_command()
            # command = self.com.get_next_command(timeout=0.01)
            # if command:
            #     t, item = command
            #     if t == "message":
            #         self.process_messages(item)
            #     elif t == "user":
            #         self.process_users(item)
            #     elif t == "sound":
            #         self.process_sound(*item)
