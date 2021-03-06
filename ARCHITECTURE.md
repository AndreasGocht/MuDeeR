# Notes for the upcomming Bot Architecture

## Infrastructure
* 2 Queues
    * incomming
    * outgoing
* Singleton
    * Communication interfaces
    * Users
    * Channels

## Messages Types
* Incomming:
    * Text Message `txt`
    * Voice Message `voc`
    * (Event Message?) `evt`
* Outgoing
    * Text Message `txt`
    * Command `cmd`

## Format
May be message objects (or structs) are simply better ... 
Incomming
```
namedtuple data
data.com_source == commuincaton source (e.g. mumble)
data.user == issuing user
data.message == text representation of Message
data.channel == [optional] channel where message was issued
data.voice == [optional] numpy array of issuers voice recording
```
Outgoing
```
namedtuple data
data.com_target == communication target (e.g. mumble)
data.command == command to execute (e.g. send text, send audio, change channel, ...)
data.user == [optional] depending on command
data.channel == [optional] depending on command
data.message == [optional] depending on command
data.audio == [optional] depending on command
```
Commands (Not all commands are valid for all interfaces)
```
(folow, user)
(move_to, channel)
(create_channel,channel)
(move_user,(user,channel))
...
```