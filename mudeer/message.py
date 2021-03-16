import collections

"""
data.com_source == commuincaton source (e.g. mumble)
data.user == issuing user
data.message ==  [optional] text representation of Message
data.channel == [optional] channel where message was issued
data.voice == [optional] numpy array of issuers voice recording
"""
In = collections.namedtuple("In",
                            ["com_source", "user", "message", "channel", "voice"],
                            defaults=[None, None, None])

"""
data.com_target == communication target (e.g. mumble)
data.command == command to execute (e.g. send text, send audio, change channel, ...)
data.user == [optional] depending on command
data.channel == [optional] depending on command
data.message == [optional] depending on command
data.audio == [optional] depending on command
"""
Out = collections.namedtuple("Out",
                             ["com_target", "command", "user", "message", "channel", "audio"],
                             defaults=[None, None, None, None])


"""
user.name == string with name
user.com_interface == e.g. "mumble" or "telegram"
user.raw_data == raw data from interface
"""
User = collections.namedtuple("User", ["name", "com_interface", "raw_data"])

"""
channel.name == string with channel name
channel.com_interface == e.g. "mumble" or "telegram"
channel.raw_data == raw data from interface
"""
Channel = collections.namedtuple("Channel", ["name", "com_interface", "raw_data"])
