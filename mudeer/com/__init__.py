import logging
import queue

import mudeer.com.mumble as mumble
import mudeer.com.telegram as telegram

import mudeer.message

log = logging.getLogger(__name__)


class Coms():
    def __init__(self, coms: dict, name: str, stt, queue_in: queue.Queue, queue_out: queue.Queue) -> None:
        """
        @param dict: Dictonary in the form:
            {"mumble":
                {"host":<host>},
                {"port":<port>},
                {"ssl_cert":<ssl_cert>},
                ...
            }
        @param name: bot name
        @param stt: speech to text enging (e.g. DeepSpeech)
        @param queue_in: any messages that are recived from the bot are written to this queue
        @param queue_out: any messages that are send from the bot are written to this queue
        """
        self._coms = []
        self._queue_out = queue_out
        for com, settings in coms.items():
            if com == "mumble":
                com_id = len(self._coms)
                self._coms.append(mumble.Mumble(com_id, settings, name, stt, queue_in, queue_out))
            elif com == "telegram":
                com_id = len(self._coms)
                self._coms.append(telegram.Telegram(com_id, settings, name, stt, queue_in, queue_out))
            else:
                log.error("Not interface for com \"{}\". Ignoring".format(com))

    def connect(self):
        for com in self._coms:
            com.connect()

    def disconncet(self):
        for com in self._coms:
            com.disconncet()

    def process(self):
        try:
            message: mudeer.message.Out = self._queue_out.get_nowait()
            com_target = self._coms[message.com_target]
            com_target.process(message)
        except queue.Empty:
            pass
