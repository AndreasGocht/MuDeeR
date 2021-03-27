import requests
import re
import html
import random
import logging
import os
import json
import datetime
import time

import mudeer.message
from mudeer.commands import Commands


def add_br(m):
    return m.group(1) + "<br/>"


class Skill():
    def __init__(self, skill_main, queue_out, config):
        self.log = logging.getLogger(__name__)

        self.skill_main = skill_main
        self.queue_out = queue_out

        self.special_user = skill_main.name
        self.channels = {}
        self.channels_com_src = {}

    def get_inital_key_words(self):
        return ["verschiebe", "kanal"]

    def get_inital_users(self):
        return [self.special_user]

    def process(self, in_message: mudeer.message.In):
        if in_message.message is None and in_message.channel:
            com_src = in_message.com_source
            ch: mudeer.message.Channel = in_message.channel
            if ch.name not in self.channels:
                self.channels[ch.name] = ch
                self.channels_com_src[ch.name] = com_src  # ok, this is a hack
                self.skill_main.register_key_word(self, ch.name)

        elif in_message.message:
            if "verschiebe" in in_message.message and "kanal" in in_message.message:
                channel_found = False
                for ch_name in self.channels:
                    if ch_name in in_message.message:
                        channel_found = True
                        com_dst = self.channels_com_src[ch_name]
                        ch = self.channels[ch_name]
                        out_msg = mudeer.message.Out(com_dst, Commands.MOVE_USER, in_message.user, None, ch)
                        self.queue_out(out_msg)
                if not channel_found:
                    self.log.error("did not found a known channel in the message \"{}\"".format(in_message.message))
                    self.log.error("known channels are: \"{}\"".format(self.channels.keys()))

    def gen_help(self):
        return ["channel - Bewegen in channels"]
