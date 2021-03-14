import mudeer.com.com_mumble as com_mumble
import logging
import queue

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
        for com, settings in coms.items():
            if com == "mumble":
                com_id = len(self._coms)
                self._coms.append(com_mumble.ComMumble(com_id, settings, name, stt, queue_in, queue_out))
            else:
                log.error("Not interface for com \"{}\". Ignoring".format(com))
