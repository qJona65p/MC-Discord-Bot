# MC-Discord-Bot
Discord Bot to manage a minecraft server hosted on the same machine.

It will show as Playing: the status of the server
- ONLINE
- OFFLINE
- STARTING

Alongside the number of players logged in, as well as max players

## Commands (md or channel msg)
- /start (Allowed users only)
Start teh server
- /reload (Admins only)
Reloads configs
- /stop (Admins only)
Stops the server

## Auto-stop
After STOP_DELAY_MINUTES minutes with no one on the server it will auto-stop so you're not wasting resources.
