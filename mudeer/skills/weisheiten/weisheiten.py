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


class Weisheiten():
    def __init__(self, skill_main, queue_out):
        self.log = logging.getLogger(__name__)

        self.skill_main = skill_main
        self.queue_out = queue_out

        self.special_user = "jesaa"

        self.database_path = os.path.realpath(__file__)
        self.database_path = os.path.splitext(self.database_path)[0] + ".json"
        try:
            self.log.debug("Read database from {}".format(self.database_path))
            with open(self.database_path, "r") as f:
                self.database = json.load(f)
        except OSError as e:
            self.log.error("Database not read: {}\n reason: {}".format(self.database_path, e))
            self.database = {}

        self.weisheiten = []
        parsing = False

        r = requests.get("https://geistige-steinwueste.de/archiv/")

        for line in r.text.split("\n"):
            if "Liste aller bisher veröffentlichten Weisheiten" in line:
                parsing = True
            if parsing:
                if "<td>" in line:
                    weisheit = line.replace("<td>", "").replace("</td>", "")
                    w = re.sub("([0-9][0-9]/[0-9][0-9])", add_br, weisheit)
                    self.weisheiten.append(html.unescape(w))
        self.log.debug("Got {} weisheiten".format(len(self.weisheiten)))

    def update_database(self):
        with open(self.database_path, "w") as f:
            json.dump(self.database, f, indent=4)

    def send_today(self, name: str):
        last_date_time_stamp = self.database.get(name)

        self.database[name] = time.time()
        self.update_database()

        if last_date_time_stamp:
            today = datetime.date.today()
            last_date = datetime.date.fromtimestamp(last_date_time_stamp)
            return today == last_date
        else:
            return False

    def get_inital_key_words(self):
        return ["weisheit"]

    def get_inital_users(self):
        return [self.special_user]

    def process(self, in_message: mudeer.message.In):
        if in_message.message:
            if "weisheit" in in_message.message:
                weisheit = random.choice(self.weisheiten)
                out_message = mudeer.message.Out(
                    in_message.com_source, Commands.SEND_MESSAGE, None, weisheit, in_message.channel)
                self.queue_out.put(out_message)

        elif in_message.user and in_message.message is None:  # event infos are todo
            if in_message.user.name == self.special_user:
                weisheit = random.choice(self.weisheiten)

                out_message = mudeer.message.Out(in_message.com_source, Commands.FOLLOW, in_message.user)
                self.queue_out.put(out_message)
                time.sleep(1)

                out_message = mudeer.message.Out(in_message.com_source, Commands.SEND_MESSAGE, None,
                                                 "Hallo Felix, schön dich zu sehen<br/>Nur für dich eine Weisheit:")
                self.queue_out.put(out_message)
                time.sleep(0.2)

                out_message = mudeer.message.Out(in_message.com_source, Commands.SEND_MESSAGE, None,
                                                 weisheit)
                self.queue_out.put(out_message)

                out_message = mudeer.message.Out(in_message.com_source, Commands.FOLLOW, None)
                self.queue_out.put(out_message)

    def gen_help(self):
        return ["weisheit - Eine Weisheit von Felix"]
