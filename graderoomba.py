"""
todo add docs
"""

import discord
from discord import app_commands
import dotenv
import os
import requests
import time

# Load config
dotenv.load_dotenv()
GRADEROOM_KEY = os.environ.get("GRADEROOM_KEY")
DISCORD_KEY = os.environ.get("DISCORD_KEY")
MAIN_GUILD_ID = os.environ.get("MAIN_GUILD_ID")

# Read blacklist
with open("blacklist.txt", "a+") as f:
    f.seek(0)
    BLACKLIST = f.read().splitlines()

# Set Intents
intents = discord.Intents.default()
intents.message_content = True

# Initialize the client and command tree
activity = discord.Game(name="with your grades")
client = discord.Client(intents=intents, activity=activity)
tree = app_commands.CommandTree(client)

# Set constants for commands
VERIFY_DESC = "Enter your Graderoom username to verify yourself"
ROLES_DESC = "After verification, run this command to get roles"
guild = discord.Object(id=MAIN_GUILD_ID)
API_CONNECT_URL = f'https://graderoom.me/api/internal/discord/connect'
API_USER_INFO_URL = f'https://graderoom.me/api/internal/discord/user-info'
BETA_API_CONNECT_URL = f'https://beta.graderoom.me/api/internal/discord/connect'
BETA_API_USER_INFO_URL = f'https://beta.graderoom.me/api/internal/discord/user-info'
HEADERS = {'x-internal-api-key': GRADEROOM_KEY}
ERROR_CODES = {
    1: "Invalid Discord ID",
    2: "There is no Graderoom account with the given username.",
    3: "You've already linked this Discord account. Use `/roles` to get your roles.",
    4: "The specified Graderoom account already has a different linked Discord account. "
       "If you are trying to link a new Discord account, "
       "first unlink the current account in your Graderoom Settings > Account > Open Discord Panel.",
    5: "You must connect your Discord account before you can get roles."
}
SUCCESS_MSG = "Your pairing code is **{}**. Type it into the notification on your Graderoom account. Your code " \
              "expires in 2 minutes. "
TIMESTAMP_STR = '%a %H:%M:%S'
USER_ROLE_ID = 898395943030906912
CAN_CHANGE_NICKNAME_ROLE_ID = 1228431413989343273
SCHOOL_ROLE_IDS = {
    'bellarmine': 898399066734596106,
    'basis': 898398946118996098,
    'ndsj': 1038570324775686178
}
BETA_TESTER_ROLE_ID = 897624644306239488
DONOR_ROLE_IDS = {
    'premium': 1061786853235249172,
    'plus': 1061786582027337748,
    'donor': 1061786078979297322
}


# Verify command to start pairing between Discord ID and Graderoom account
@tree.command(name="verify", description=VERIFY_DESC, guild=guild)
async def verify_command(interaction, graderoom_username: str, beta: bool = False) -> None:
    discord_id = interaction.user.id
    # Log the request
    site_type = "beta" if beta else "stable"
    timestamp = time.strftime(TIMESTAMP_STR)
    print(f"[{timestamp}] {discord_id} requested {site_type} verification for {graderoom_username}")
    # Set up and call API
    url = BETA_API_CONNECT_URL if beta else API_CONNECT_URL
    body = {'username': graderoom_username, 'discordID': f"{discord_id}"}
    resp = requests.post(url, headers=HEADERS, json=body)
    json_resp = resp.json()

    # Reply with response error
    if not resp.ok:
        message = ERROR_CODES[json_resp['errorCode']]

        timestamp = time.strftime(TIMESTAMP_STR)
        print(f"[{timestamp}] {discord_id} received error: {message}")
        await interaction.response.send_message(message, ephemeral=True)
        return

    # Reply with the 2-digit verification code
    verification_code = json_resp['verificationCode']
    timestamp = time.strftime(TIMESTAMP_STR)
    print(f"[{timestamp}] {discord_id} received pairing code {verification_code}")
    await interaction.response.send_message(SUCCESS_MSG.format(verification_code), ephemeral=True)


# Roles command to give roles to the Discord user
@tree.command(name="roles", description=ROLES_DESC, guild=guild)
async def roles_command(interaction, beta: bool = False) -> None:
    discord_id = interaction.user.id
    # Log the request
    site_type = "beta" if beta else "stable"
    timestamp = time.strftime(TIMESTAMP_STR)
    print(f"[{timestamp}] {discord_id} requested {site_type} roles")
    # Set up and call API
    url = BETA_API_USER_INFO_URL if beta else API_USER_INFO_URL
    body = {'discordID': f"{discord_id}"}
    resp = requests.get(url, headers=HEADERS, json=body)
    json_resp = resp.json()

    # Errors, mainly if user has not linked yet
    if not resp.ok:
        message = ERROR_CODES[json_resp['errorCode']]

        timestamp = time.strftime(TIMESTAMP_STR)
        print(f"[{timestamp}] {discord_id} received error on {site_type}: {message}")
        await interaction.response.send_message(message, ephemeral=True)
        return

    roles_to_add = []
    # Add role for school
    school = json_resp['school']
    role = interaction.guild.get_role(SCHOOL_ROLE_IDS[school])
    roles_to_add.append(role)
    # Add User role
    role = interaction.guild.get_role(USER_ROLE_ID)
    roles_to_add.append(role)
    # Add allow speech role if not in blacklist
    if f"{interaction.user.id}" not in BLACKLIST:
        role = interaction.guild.get_role(CAN_CHANGE_NICKNAME_ROLE_ID)
        roles_to_add.append(role)
    # Add role for beta
    if beta:
        role = interaction.guild.get_role(BETA_TESTER_ROLE_ID)
        roles_to_add.append(role)
    # Add donation roles. Each key is true if amt is above threshold
    dono_data = json_resp['donoData']
    for key, role_id in DONOR_ROLE_IDS.items():
        if dono_data[key]:
            role = interaction.guild.get_role(role_id)
            roles_to_add.append(role)

    # Give roles and respond to message
    for role in roles_to_add:
        await interaction.user.add_roles(role)
    response = "Roles given: " + ", ".join([x.name for x in roles_to_add])
    timestamp = time.strftime(TIMESTAMP_STR)
    print(f"[{timestamp}] {discord_id} received roles, {response}")
    await interaction.response.send_message(response, ephemeral=True)


# Update command tree and log when bot is ready
@client.event
async def on_ready():
    await tree.sync(guild=guild)
    print("Ready!")


# Start the bot
client.run(DISCORD_KEY)
