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
    * Text Message
    * Voice Message
    * (Event Message?)
* Outgoing
    * Text Message
    * Command

## Format
Incomming
```
([Mumble|Telegram], ([User|Channel], ([Text|Voice|...],[...])))
```
Outgoing
```
([Mumble|Telegram], ([User|Channel], ([Text|Command|...],[...])))
```
Commands (Not all commands are valid for all interfaces)
```
(folow, user)
(move_to, channel)
(create_channel,channel)
(move_user,(user,channel))
...
```