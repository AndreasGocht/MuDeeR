import com_mumble
import logging
import queue

log = logging.getLogger(__name__)


class Coms():
    __init__(self, coms: dict, name: str, queue_in: queue.Queue, queue_out: queue.Queue):
    """
    @param dict: Dictonary in the form:
        {"mumble":
            {"host":<host>},
            {"port":<port>},
            {"ssl_cert":<ssl_cert>},
            ...
        }
    """
    self._coms = []
    for com, settings in coms.items():
        if com == "mumble":
            com_id = len(self._coms)
            self._coms.append(com_mumble.ComMumble(com_id, name, queue_in, queue_out, settings))
        else:
            log.error("Not interface for com \"{}\". Ignoring".format(com))
