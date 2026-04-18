# MC-Discord-Bot
Discord Bot to manage a minecraft server hosted on the same machine.

It will show as Playing: the status of the server
- ONLINE
- OFFLINE
- STARTING

Alongside the number of players logged in, as well as max players

## Dependencies
- mcstatus

So it can look into the server

- discord.py

Its a discord bot so...

- tmux

The server runs in a dettached process from the bot, so a failure or restart of the MCBot wont cause lost of access to the process


## Commands (md or channel msg)
- /start (Allowed users only)

Start the server
- /reload (Admins only)

Reloads configs
- /stop (Admins only)

Stops the server

## Auto-stop
After STOP_DELAY_MINUTES minutes with no one on the server it will auto-stop so you're not wasting resources.

## WIP
I want to integrate it with a lesser bot to wake up the pc and interact with this one so it can work without me interfering, and that the pc can start and stop automatically.

## TMUX
You can access the server console locally using tmux, with the session_name in the config file
