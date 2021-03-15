import logging
import re

import mudeer.skills as skills

import enum


class Commands(enum.Enum):
    """
    available commands
    """
    MOVE_CHANNEL = 1


class Command():
    def __init__(self, names=[]):
        """
        @param names names, to identify the receiver string
        """
        self.log = logging.getLogger(__name__)

        self.names = sorted([name.lower() for name in names], key=len, reverse=True)
        self.log.debug("got names: {}".format(self.names))

        self.error_message = _("Sorry, I could not understand you.<br />Please ask me for my included vocabulary.")

        self.skill_list = skills.skill_list

        self.skills = []
        self.skills_user = []
        self.skills_text = [self]

        for skill in self.skill_list:
            skill = skill()
            self.skills.append(skill)
            command_types = skill.command_types()
            if "text" in command_types:
                self.skills_text.append(skill)
            if "user" in command_types:
                self.skills_user.append(skill)

    def command_text(self, command_text):
        if _("home") in command_text.lower():
            return [("follow", None)]
        elif _("follow") in command_text.lower():
            match = re.search("@([\w0-9]*)", command_text)
            if match:
                name = match.group(1)
                return [("follow", name)]
            else:
                return [("error", self.error_message)]
        elif _("vocabulary") in command_text.lower():
            return self.gen_help()
        else:
            return [(None, None)]

    def get_available_commands(self):
        available_commands = [_("home"), _("vocabulary"), _("follow")]
        for skill in self.skills:
            available_commands.extend(skill.get_available_commands())
        return available_commands

    def gen_help(self):
        # heimwaerts, wortschatz, folge @username
        available_commands = [
            _("home ... return to home channel"),
            _("vocabulary ... my included vocabulary"),
            _("follow @username ... follow username")]
        for skill in self.skills:
            available_commands.extend(skill.gen_help())
        return [("message", available_commands)]

    def process_text(self, command_text):
        command_text = command_text.lower()
        name_found = False
        for name in self.names:
            if name in command_text:
                # get rid of any command tags, e.g. @Lara
                name_found = True
                command_text = command_text.replace(name, "")

        if name_found:
            ret = []
            for skill in self.skills_text:
                ret.extend(skill.command_text(command_text))
            if ret:
                return ret
            else:
                return [("error", self.error_message)]
        else:
            return [(None, None)]

    def process_user(self, user):
        ret = []
        for skill in self.skills_user:
            ret.extend(skill.command_user(user))
        return ret
