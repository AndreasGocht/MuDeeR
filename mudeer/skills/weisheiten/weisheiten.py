import requests
import re
import html
import random
import logging
import os
import json
import datetime
import time


def add_br(m):
    return m.group(1) + "<br/>"


class Weisheiten():
    def __init__(self):
        self.log = logging.getLogger(__name__)

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

    def command_types(self):
        return ["text", "user"]

    def command_text(self, command_text):
        if "weisheit" in command_text.lower():
            weisheit = random.choice(self.weisheiten)
            return [("message", weisheit)]
        else:
            return [(None, None)]

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

    def command_user(self, user):
        self.log.debug("got user {}".format(user))
        if user["name"] == "DerReiskocher":
            if self.send_today(user["name"]):
                return [(None, None)]
            weisheit = random.choice(self.weisheiten)
            commands = []
            commands.append(("follow", user))
            commands.append(("wait", 1))
            commands.append(("message", "Hallo Felix, schön dich zu sehen<br/>Nur für dich eine Weisheit:"))
            commands.append(("wait", 0.2))
            commands.append(("message", weisheit))
            commands.append(("follow", None))
            return commands
        else:
            return [(None, None)]

    def get_available_commands(self):
        return ["weisheit"]

    def gen_help(self):
        return ["weisheit - Eine Weisheit von Felix"]
