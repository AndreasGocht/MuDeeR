import configparser
import pkg_resources
import gettext
import logging

from mudeer.main import MuDeer


def main():
    config_file = pkg_resources.resource_filename(__name__, "/etc/config.cfg")
    local_path = pkg_resources.resource_filename(__name__, "/locales")

    config = configparser.ConfigParser()
    try:
        with open(config_file) as f:
            config.read_file(f)
    except FileNotFoundError as e:
        logging.fatal("did not find config file:\n{}".format(e))
        exit(-1)

    logging.basicConfig(level=config["logging"].get("level", "INFO"))

    text = gettext.translation("commands", localedir=local_path, languages=[config["etc"]["lang"]], fallback=True)
    text.install()

    deer = MuDeer(config)
    deer.connect()
    try:
        deer.run()
    except KeyboardInterrupt:
        pass
    finally:
        deer.disconncet()
