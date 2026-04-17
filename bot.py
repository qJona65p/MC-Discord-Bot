from mcstatus import JavaServer
import subprocess
import discord
import asyncio
import configparser

config = configparser.ConfigParser()
config.read("config.cfg")

TOKEN               = config["Bot"]["token"]
STOP_DELAY_MINUTES  = config["Bot"].getint("stop_delay_minutes")
TMUX_SESSION_NAME   = config["Bot"]["session_name"]
SERVER_ADRESS       = config["Server"]["address"]
SERVER_DIR          = config["Server"]["dir"]
ADMINS_IDS          = set(int(i) for i in config["Users"]["admin_ids"].split(","))
ALLOWED_USER_IDS    = set(int(i) for i in config["Users"]["allowed_user_ids"].split(","))

ALLOWED_USER_IDS.update(ADMINS_IDS)

intents = discord.Intents.default()

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.empty_since = None
        self.starting = False
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        self.bg_task = asyncio.create_task(self.check_server())

    def is_server_running(self):
        # Check tmux session
        result = subprocess.run([
            "tmux", "has-session", "-t", TMUX_SESSION_NAME], 
            stderr=subprocess.DEVNULL
            )
        return result.returncode == 0
    
    def send_command(self, cmd):
        subprocess.run([
            "tmux", "send-keys",
            "-t", TMUX_SESSION_NAME,
            cmd, "Enter"
        ])

    async def start_minecraft_server(self, interaction: discord.Interaction):
        # If its running its running
        if self.is_server_running():
            print(f"[MCBot] ({interaction.user.name}) Attempted to start a started server")
            await interaction.followup.send("El servidor ya esta iniciado.")
            return
        
        # Launch in a tmux session
        await interaction.followup.send("Iniciando...")
        try:
            subprocess.run([
                "tmux", "new", "-d", 
                "-s", TMUX_SESSION_NAME, 
                "bash", "-c", f"cd {SERVER_DIR} && ./run.sh"
            ])
            self.empty_since = None
            self.starting = True

            print(f"[MCBot] ({interaction.user.name}) Server started with tmux session '{TMUX_SESSION_NAME}'")
            await interaction.followup.send("Server iniciado! Espera un momento para que este online.")
        
        except Exception as e:
            await interaction.followup.send(f"Fallo al iniciar. Intentalo de nuevo mas tarde.")
            print(f"[MCBot] Failed to start server: {e}")

        await self.update_presence(online=True)

    async def reload_minecraft_server(self, interaction: discord.Interaction):
        if not self.is_server_running():
            print(f"[MCBot] ({interaction.user.name}) Attempted to reload a stopped server")
            if interaction:
                await interaction.followup.send("El server no esta iniciado.")
            return

        print(f"[MCBot] ({interaction.user.name}) Reloading server")
        try:
            self.send_command("reload")
            await interaction.followup.send("Server recargado.")
        
        except Exception as e:
            await interaction.followup.send(f"Error recargando el server: {e}.")
            print(f"[MCBot] Error reloading server: {e}")

    async def stop_minecraft_server(self, interaction: discord.Interaction = None, reason="manual stop"):
        if not self.is_server_running():
            print(f"[MCBot] ({interaction.user.name}) Attempted to stop a stopped server: {reason}")
            if interaction:
                await interaction.followup.send("El server no esta iniciado.")
            return

        print(f"[MCBot] Stopping server: {reason}")
        try:
            # Send the 'stop' command to the server
            self.send_command("stop")

            # Give it up to 60 seconds to shut down
            for _ in range(60):
                if not self.is_server_running():
                    if interaction:
                        await interaction.followup.send("Server detenido.")
                        print(f"[MCBot] ({interaction.user.name}) Server stopped")
                    else:
                        print(f"[MCBot] Server stopped: {reason}")
                    break

                await asyncio.sleep(1)

            else:
                # Timeout reached
                raise TimeoutError("Server didn not stop in time")
            
        except TimeoutError:
            print("[MCBot] Server didn't stop in time, killing tmux session.")
            subprocess.run(["tmux", "kill-session", "-t", TMUX_SESSION_NAME])

        except Exception as e:
            if interaction:
                await interaction.followup.send(f"Error deteniendo el server: {e}.")
            print(f"[MCBot] Error stopping server: {e}")

        finally:
            self.empty_since = None
        
        await self.update_presence(online=False)

    async def check_server(self):
        await self.wait_until_ready()
        last_status = None
        last_players = -1

        while not self.is_closed():
            try:
                server = JavaServer.lookup(SERVER_ADRESS)
                status = server.status()
                online = True
                players = status.players.online
                maxplayers = status.players.max
                self.starting = False

            except:
                online = False
                players = 0
                maxplayers = 0
            
            # Auto stop
            if online:
                if players == 0:
                    if self.empty_since is None:
                        self.empty_since = asyncio.get_event_loop().time()
                        print("[MCBot] Server is empty, starting countdown.")

                    elif asyncio.get_running_loop().time() - self.empty_since >= STOP_DELAY_MINUTES*60:
                        print(f"[MCBot] Server empty for {STOP_DELAY_MINUTES} min, shutting down.")
                        await self.stop_minecraft_server(reason=f"no players for {STOP_DELAY_MINUTES} minutes")
                        online = False
                        players = 0

                    else:
                        print(f"[MCBot] Empty for {(asyncio.get_running_loop().time() - self.empty_since)//60} minutes")
                
                else:
                    if self.empty_since is not None:
                        print(f"[MCBot] Players joined, cancelling shutdown countdown.")

                    self.empty_since = None  # Reset timer when players are online

            # Update presence
            if last_status != online or last_players != players:
                await self.update_presence(online, players, maxplayers)

            # If something failed starting or was shutdown early
            if self.starting and not self.is_server_running():
                print(f"[MCBot] Something went wrong, check your server logs")
                self.starting = False
                await self.update_presence(online=False)

            await asyncio.sleep(60)

    async def update_presence(self, online: bool, players: int = 0, maxplayers: int = 0):
        if self.starting == True:
            activity = discord.Game(name=f"INICIANDO")
            await self.change_presence(status=discord.Status.idle, activity=activity)

        else:
            if online:
                activity = discord.Game(name=f"ONLINE ({players}/{maxplayers})")
                await self.change_presence(status=discord.Status.online, activity=activity)

            else:
                activity = discord.Game(name="OFFLINE")
                await self.change_presence(status=discord.Status.dnd, activity=activity)

client = MyClient(intents=intents)

@client.event
async def on_ready():
    print(f"[MCBot] Logged in as {client.user}")

@client.tree.command(name="start", description="Iniciar el server")
async def start(interaction: discord.Interaction):
    if interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("No autorizo.", ephemeral=True)
        print(f"[MCBot] User not in whitelist: {interaction.user.name}")
        return
    
    await interaction.response.defer()
    await client.start_minecraft_server(interaction)

@client.tree.command(name="reload", description="Recargar las configuraciones del server")
async def stop(interaction: discord.Interaction):
    if interaction.user.id not in ADMINS_IDS:
        await interaction.response.send_message("No autorizado.", ephemeral=True)
        print(f"[MCBot] User not admin: {interaction.user.name}")
        return
    
    await interaction.response.defer()
    await client.reload_minecraft_server(interaction=interaction)

@client.tree.command(name="stop", description="Detener el server")
async def stop(interaction: discord.Interaction):
    if interaction.user.id not in ADMINS_IDS:
        await interaction.response.send_message("No autorizado.", ephemeral=True)
        print(f"[MCBot] User not admin: {interaction.user.name}")
        return
    
    await interaction.response.defer()
    await client.stop_minecraft_server(interaction=interaction)

client.run(TOKEN)
