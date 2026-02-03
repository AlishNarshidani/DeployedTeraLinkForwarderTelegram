import asyncio
import os
from telethon import TelegramClient, events
from telethon.sync import TelegramClient


# === CONFIGURATION ===
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

source_channels = os.getenv("SOURCE_CHANNELS").split(",")
target_channels = os.getenv("TARGET_CHANNELS").split(",")
link_bot_username = os.getenv("LINK_BOT_USERNAME")
video_bot_username = os.getenv("VIDEO_BOT_USERNAME")

# Optional: Track pending messages if needed
pending_messages = {}
pending_video_requests = {}

# Create the Telegram client
client = TelegramClient("multi_forward_session_cloud", api_id, api_hash)

# with TelegramClient('find_my_chats', api_id, api_hash) as client:
#     for dialog in client.iter_dialogs():
#         print(f"{dialog.name} → {dialog.id}")

# PART 1: Listen to source channels and forward messages to bot
@client.on(events.NewMessage(chats=source_channels))
async def forward_to_link_bot(event):
    msg = event.message
    if not msg:
        return

    # ---- CASE 1: VIDEO (native OR document video) ----
    is_video = bool(msg.video)
    is_video_file = (
        bool(msg.document) and
        msg.document.mime_type and
        msg.document.mime_type.startswith("video/")
    )

    if is_video or is_video_file:
        print("🎥 Video detected. Sending to video bot...")

        bot_entity = await client.get_entity(video_bot_username)
        sent = await client.send_message(bot_entity, msg)

        pending_video_requests[sent.id] = {
            "source": event.chat_id
        }
        
        return

    original_msg = event.raw_text

    if not original_msg:
        print("[!] Empty message — skipping.")
        return

    if "terabox" not in original_msg.lower():
        print("[!] Message does not contain 'terabox' — skipping.")
        return

    try:
        bot_entity = await client.get_entity(link_bot_username)

        # Send message to link bot
        sent = await client.send_message(bot_entity, original_msg)
        pending_messages[sent.id] = {
            "source_channel": event.chat_id,
            "original_msg": original_msg
        }

        print(f"[✓] Forwarded to bot: {original_msg[:60]}...")

    except Exception as e:
        print(f"[!] Error forwarding to bot: {e}")

# PART 2: Listen for bot replies and forward them to target channels
@client.on(events.NewMessage(from_users=link_bot_username))
async def handle_bot_reply(event):
    try:
        reply_text = event.raw_text

        if not reply_text or "http" not in reply_text:
            print("[!] Bot reply doesn't look like a valid link — skipping.")
            return

        print(f"[✓] Bot replied: {reply_text[:60]}...")

        # Forward the converted message to all target channels
        for target in target_channels:
            await client.send_message(target, reply_text)
            print(f"[→] Forwarded to target: {target}")

    except Exception as e:
        print(f"[!] Error handling bot reply: {e}")

# ================= PART 3 =================
# Listen to Video Bot replies
@client.on(events.NewMessage(from_users=video_bot_username))
async def handle_video_bot_reply(event):
    try:
        reply_msg = event.message
        reply_text = event.raw_text

        if not reply_text or "http" not in reply_text:
            print("[!] Bot reply doesn't look like a valid link — skipping.")
            return

        print(f"[✓] Video Bot replied: {reply_text[:60]}...")

        for target in target_channels:
            await client.send_message(target, reply_msg)
            print(f"➡️ Video forwarded to {target}")

    except Exception as e:
        print(f"[!] Error handling video bot reply: {e}")

# Start the bot
print("👂 Listening for source messages and bot replies...")
with client:
    client.run_until_disconnected()
