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
IS_BETA = (os.environ.get("IS_BETA").lower() == "true")

# Set Intents, do we need message content for commands?
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
beta_str = 'beta.' if IS_BETA else ''
API_CONNECT_URL = f'https://{beta_str}graderoom.me/api/internal/discord/connect'
API_USER_INFO_URL = f'https://{beta_str}graderoom.me/api/internal/discord/user-info'
HEADERS = {'x-internal-api-key': GRADEROOM_KEY}
ERROR_CODES = {
    1: "Invalid Discord ID",
    2: "There is no Graderoom account with the given username.",
    3: "You've already linked this Discord account. Use `/roles` to get your roles.",
    4: "The specified Graderoom account already has a linked Discord account.",
    5: "You must connect your Discord account before you can get roles."
}
SUCCESS_MSG = "Your pairing code is **{}**. Type it into the notification on your Graderoom account. Your code expires" \
              " in 2 minutes."
TIMESTAMP_STR = '%a %H:%M:%S'
SCHOOL_ROLE_IDS = {
    'bellarmine': 898399066734596106,
    'basis': 898398946118996098,
    'ndsj': 1038570324775686178
}


# Verify command to start pairing between Discord ID and Graderoom account
@tree.command(name="verify", description=VERIFY_DESC, guild=guild)
async def verify_command(interaction, graderoom_username: str) -> None:
    discord_id = interaction.user.id
    timestamp = time.strftime(TIMESTAMP_STR)
    print(f"[{timestamp}] {discord_id} requested verification for {graderoom_username}")
    # Set up and call API
    body = {'username': graderoom_username, 'discordID': discord_id}
    resp = requests.post(API_CONNECT_URL, headers=HEADERS, json=body)
    json_resp = resp.json()

    # Reply with response error or the verification code
    if not resp.ok:
        message = ERROR_CODES[json_resp['errorCode']]

        timestamp = time.strftime(TIMESTAMP_STR)
        print(f"[{timestamp}] {discord_id} received error: {message}")
        await interaction.response.send_message(message, ephemeral=True)
    else:
        verification_code = json_resp['verificationCode']
        timestamp = time.strftime(TIMESTAMP_STR)
        print(f"[{timestamp}] {discord_id} received pairing code {verification_code}")
        await interaction.response.send_message(SUCCESS_MSG.format(verification_code), ephemeral=True)


# Roles command to give roles to the Discord user
@tree.command(name="roles", description=ROLES_DESC, guild=guild)
async def roles_command(interaction) -> None:
    discord_id = interaction.user.id
    timestamp = time.strftime(TIMESTAMP_STR)
    print(f"[{timestamp}] {discord_id} requested roles")
    # Set up and call API
    body = {'discordID': discord_id}
    resp = requests.get(API_USER_INFO_URL, headers=HEADERS, json=body)
    json_resp = resp.json()

    roles_to_add = []
    # Add role for school
    school = json_resp['school']
    role = interaction.guild.get_role(SCHOOL_ROLE_IDS[school])
    roles_to_add.append(role)
    # todo add roles for donations

    # Give roles and respond to message
    for role in roles_to_add:
        await interaction.user.add_roles(role)
    response = "Roles given: " + ", ".join([x.name for x in roles_to_add])
    timestamp = time.strftime(TIMESTAMP_STR)
    print(f"[{timestamp}] {discord_id} received roles: {response}")
    await interaction.response.send_message(response, ephemeral=True)


# Update command tree and log when bot is ready
@client.event
async def on_ready():
    await tree.sync(guild=guild)
    print("Ready!")


# Start the bot
client.run(DISCORD_KEY)
