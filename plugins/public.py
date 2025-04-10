import re
import asyncio 
from .utils import STS
from database import db
from config import temp 
from translation import Translation
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait 
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified, ChannelPrivate
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
 
@Client.on_message(filters.private & filters.command(["fwd", "forward"]))
async def run(bot, message):
    user_id = message.from_user.id
    bots = await db.get_bots(user_id)
    if not bots:
        return await message.reply("<code>You didn't add any bot. Please add a bot using /settings!</code>")

    # Select a bot if multiple exist
    if len(bots) > 1:
        buttons = [[KeyboardButton(f"{_bot['name']}")] for _bot in bots]
        buttons.append([KeyboardButton("cancel")])
        bot_choice = await bot.ask(
            message.chat.id,
            "Choose a bot to use for forwarding:\n/cancel - Cancel this process",
            reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
        )
        if bot_choice.text.startswith(('/', 'cancel')):
            return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
        selected_bot = next((b for b in bots if b['name'] == bot_choice.text), None)
        if not selected_bot:
            return await message.reply_text("Invalid bot chosen!", reply_markup=ReplyKeyboardRemove())
    else:
        selected_bot = bots[0]

    # Select target channel
    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply_text("Please set a target channel in /settings before forwarding")
    if len(channels) > 1:
        buttons = [[KeyboardButton(f"{channel['title']}")] for channel in channels]
        buttons.append([KeyboardButton("cancel")])
        _toid = await bot.ask(
            message.chat.id,
            Translation.TO_MSG.format(selected_bot['name'], selected_bot['username']),
            reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
        )
        if _toid.text.startswith(('/', 'cancel')):
            return await message.reply_text(Translation.CANCEL, reply_markup=ReplyKeyboardRemove())
        to_title = _toid.text
        toid = next((c['chat_id'] for c in channels if c['title'] == to_title), None)
        if not toid:
            return await message.reply_text("Wrong channel chosen!", reply_markup=ReplyKeyboardRemove())
    else:
        toid = channels[0]['chat_id']
        to_title = channels[0]['title']

    # Rest of the logic remains similar, but use selected_bot
    fromid = await bot.ask(message.chat.id, Translation.FROM_MSG, reply_markup=ReplyKeyboardRemove())
    if fromid.text and fromid.text.startswith('/'):
        await message.reply(Translation.CANCEL)
        return
    if fromid.text and not fromid.forward_date:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(fromid.text.replace("?single", ""))
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int(("-100" + chat_id))
    elif fromid.forward_from_chat.type in [enums.ChatType.CHANNEL]:
        last_msg_id = fromid.forward_from_message_id
        chat_id = fromid.forward_from_chat.username or fromid.forward_from_chat.id
        if last_msg_id is None:
            return await message.reply_text("This may be a forwarded message from a group and sent by an anonymous admin. Instead, send the last message link from the group.")
    else:
        await message.reply_text("**invalid!**")
        return

    try:
        title = (await bot.get_chat(chat_id)).title
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = "private" if fromid.text else fromid.forward_from_chat.title
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')

    skipno = await bot.ask(message.chat.id, Translation.SKIP_MSG)
    if skipno.text.startswith('/'):
        await message.reply(Translation.CANCEL)
        return
    forward_id = f"{user_id}-{skipno.id}-{selected_bot['id']}"
    buttons = [
        [InlineKeyboardButton('Yes', callback_data=f"start_public_{forward_id}"),
         InlineKeyboardButton('No', callback_data="close_btn")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text(
        text=Translation.DOUBLE_CHECK.format(botname=selected_bot['name'], botuname=selected_bot['username'], from_chat=title, to_chat=to_title, skip=skipno.text),
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )
    STS(forward_id).store(chat_id, toid, int(skipno.text), int(last_msg_id), selected_bot)