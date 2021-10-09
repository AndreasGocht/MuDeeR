import collections
import logging
import queue

import mudeer.message

from .weisheiten import weisheiten
from .channel import channel

skill_list = [weisheiten, channel]


class Skills():
    def __init__(self, name, queue_in, queue_out, stt, config):
        """
        @param names names, to identify the receiver string
        """
        self.log = logging.getLogger(__name__)

        self.name = name

        self.queue_in = queue_in
        self.queue_out = queue_out

        self.stt = stt

        self.error_message = _("Sorry, I could not understand you.<br />Please ask me for my included vocabulary.")

        self.skill_list = skill_list

        self.skills = []
        self.key_words = collections.defaultdict(list)
        self.users = collections.defaultdict(list)

        for skill in self.skill_list:
            skill_name = skill.__name__.split(".")[-1]
            skill_config = config["skills." + skill_name]
            skill = skill.Skill(self, self.queue_out, skill_config)
            self.skills.append(skill)

            key_words = skill.get_inital_key_words()
            for k in key_words:
                self.log.debug("add kyword {} for skill {}".format(k, skill))
                self.register_key_word(skill, k)

            users = skill.get_inital_users()
            for u in users:
                self.log.debug("add special user {} for skill {}".format(u, skill))
                self.register_user(skill, u)

    def register_key_word(self, skill, key_word):
        self.key_words[key_word].append(skill)
        self.stt.add_hot_words([key_word])
        # TODO update Keywords

    def unregister_key_word(self, skill, key_word):
        self.key_words[key_word].remove(skill)
        if len(self.key_words[key_word]) == 0:
            del self.key_words[key_word]
            self.stt.remove_hot_words([key_word])

    def register_user(self, skill, user_name):
        self.users[user_name].append(skill)

    def unregister_user(self, skill, user_name):
        self.users[user_name].remove(skill)
        if len(self.users[user_name]) == 0:
            del self.users[user_name]

    def process(self):
        try:
            message: mudeer.message.In = self.queue_in.get_nowait()
            skills_to_process = set()
            if message.message:
                self.log.debug("got message {}".format(message.message))
                if message.message.lower().startswith(self.name.lower()):
                    self.log.debug("message is for me")
                    for k in self.key_words:
                        if k in message.message:
                            self.log.debug("keyword to process {}".format(k))
                            skills_to_process.update(self.key_words[k])
            if message.user:
                self.log.debug("got user {}".format(message.user.name))
                if message.user.name in self.users:
                    self.log.debug("user to process {}".format(message.user.name))
                    skills_to_process.update(self.users[message.user.name])
            for s in skills_to_process:
                s.process(message)

        except queue.Empty:
            pass

    def get_available_key_words(self):
        return self.key_words.keys()

    # def command_text(self, command_text):
    #     if _("home") in command_text.lower():
    #         return [("follow", None)]
    #     elif _("follow") in command_text.lower():
    #         match = re.search("@([\w0-9]*)", command_text)
    #         if match:
    #             name = match.group(1)
    #             return [("follow", name)]
    #         else:
    #             return [("error", self.error_message)]
    #     elif _("vocabulary") in command_text.lower():
    #         return self.gen_help()
    #     else:
    #         return [(None, None)]

    # def get_available_commands(self):
    #     available_commands = [_("home"), _("vocabulary"), _("follow")]
    #     for skill in self.skills:
    #         available_commands.extend(skill.get_available_commands())
    #     return available_commands

    # def gen_help(self):
    #     # heimwaerts, wortschatz, folge @username
    #     available_commands = [
    #         _("home ... return to home channel"),
    #         _("vocabulary ... my included vocabulary"),
    #         _("follow @username ... follow username")]
    #     for skill in self.skills:
    #         available_commands.extend(skill.gen_help())
    #     return [("message", available_commands)]

    # def process_text(self, command_text):
    #     command_text = command_text.lower()
    #     name_found = False
    #     for name in self.names:
    #         if name in command_text:
    #             # get rid of any command tags, e.g. @Lara
    #             name_found = True
    #             command_text = command_text.replace(name, "")

    #     if name_found:
    #         ret = []
    #         for skill in self.skills_text:
    #             ret.extend(skill.command_text(command_text))
    #         if ret:
    #             return ret
    #         else:
    #             return [("error", self.error_message)]
    #     else:
    #         return [(None, None)]

    # def process_user(self, user):
    #     ret = []
    #     for skill in self.skills_user:
    #         ret.extend(skill.command_user(user))
    #     return ret
