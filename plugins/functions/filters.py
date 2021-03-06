# SCP-079-CLEAN - Filter specific types of messages
# Copyright (C) 2019-2020 SCP-079 <https://scp-079.org>
#
# This file is part of SCP-079-CLEAN.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import re
from copy import deepcopy
from string import ascii_lowercase
from typing import Match, Optional, Union

from pyrogram import CallbackQuery, Client, Filters, Message, User

from .. import glovar
from .channel import get_content
from .etc import get_channel_link, get_command_type, get_entity_text, get_now, get_links, get_md5sum
from .etc import get_stripped_link, get_text, thread
from .file import delete_file, get_downloaded_path, save
from .group import get_description, get_group_sticker, get_member, get_pinned
from .ids import init_group_id
from .image import get_file_id, get_qrcode
from .telegram import resolve_username

# Enable logging
logger = logging.getLogger(__name__)


def is_aio(_, __) -> bool:
    # Check if the program is under all-in-one mode
    result = False

    try:
        result = glovar.aio
    except Exception as e:
        logger.warning(f"Is aio error: {e}", exc_info=True)

    return result


def is_authorized_group(_, update: Union[CallbackQuery, Message]) -> bool:
    # Check if the message is send from the authorized group
    try:
        if isinstance(update, CallbackQuery):
            message = update.message
        else:
            message = update

        if not message.chat:
            return False

        cid = message.chat.id

        if init_group_id(cid):
            return True
    except Exception as e:
        logger.warning(f"Is authorized group error: {e}", exc_info=True)

    return False


def is_class_c(_, message: Message) -> bool:
    # Check if the message is sent from Class C personnel
    try:
        if not message.from_user:
            return False

        # Basic data
        uid = message.from_user.id
        gid = message.chat.id

        # Check permission
        if uid in glovar.admin_ids[gid] or uid in glovar.bot_ids or message.from_user.is_self:
            return True
    except Exception as e:
        logger.warning(f"Is class c error: {e}", exc_info=True)

    return False


def is_class_d(_, message: Message) -> bool:
    # Check if the message is Class D object
    try:
        if message.from_user:
            if is_class_d_user(message.from_user):
                return True

        if message.forward_from:
            fid = message.forward_from.id

            if fid in glovar.bad_ids["users"]:
                return True

        if message.forward_from_chat:
            cid = message.forward_from_chat.id

            if cid in glovar.bad_ids["channels"]:
                return True
    except Exception as e:
        logger.warning(f"Is class d error: {e}", exc_info=True)

    return False


def is_class_e(_, message: Message) -> bool:
    # Check if the message is Class E object
    try:
        if message.forward_from_chat:
            cid = message.forward_from_chat.id

            if cid in glovar.except_ids["channels"]:
                return True

        if message.game:
            short_name = message.game.short_name

            if short_name in glovar.except_ids["long"]:
                return True

        content = get_content(message)

        if not content:
            return False

        if (content in glovar.except_ids["long"]
                or content in glovar.except_ids["temp"]):
            return True
    except Exception as e:
        logger.warning(f"Is class e error: {e}", exc_info=True)

    return False


def is_declared_message(_, message: Message) -> bool:
    # Check if the message is declared by other bots
    try:
        if not message.chat:
            return False

        gid = message.chat.id
        mid = message.message_id

        return is_declared_message_id(gid, mid)
    except Exception as e:
        logger.warning(f"Is declared message error: {e}", exc_info=True)

    return False


def is_exchange_channel(_, message: Message) -> bool:
    # Check if the message is sent from the exchange channel
    try:
        if not message.chat:
            return False

        cid = message.chat.id

        if glovar.should_hide:
            return cid == glovar.hide_channel_id
        else:
            return cid == glovar.exchange_channel_id
    except Exception as e:
        logger.warning(f"Is exchange channel error: {e}", exc_info=True)

    return False


def is_from_user(_, message: Message) -> bool:
    # Check if the message is sent from a user
    try:
        if message.from_user and message.from_user.id != 777000:
            return True
    except Exception as e:
        logger.warning(f"Is from user error: {e}", exc_info=True)

    return False


def is_hide_channel(_, message: Message) -> bool:
    # Check if the message is sent from the hide channel
    try:
        if not message.chat:
            return False

        cid = message.chat.id

        if cid == glovar.hide_channel_id:
            return True
    except Exception as e:
        logger.warning(f"Is hide channel error: {e}", exc_info=True)

    return False


def is_new_group(_, message: Message) -> bool:
    # Check if the bot joined a new group
    try:
        new_users = message.new_chat_members

        if new_users:
            return any(user.is_self for user in new_users)
        elif message.group_chat_created or message.supergroup_chat_created:
            return True
    except Exception as e:
        logger.warning(f"Is new group error: {e}", exc_info=True)

    return False


def is_test_group(_, update: Union[CallbackQuery, Message]) -> bool:
    # Check if the message is sent from the test group
    try:
        if isinstance(update, CallbackQuery):
            message = update.message
        else:
            message = update

        if not message.chat:
            return False

        cid = message.chat.id

        if cid == glovar.test_group_id:
            return True
    except Exception as e:
        logger.warning(f"Is test group error: {e}", exc_info=True)

    return False


aio = Filters.create(
    func=is_aio,
    name="AIO"
)

authorized_group = Filters.create(
    func=is_authorized_group,
    name="Authorized Group"
)

class_c = Filters.create(
    func=is_class_c,
    name="Class C"
)

class_d = Filters.create(
    func=is_class_d,
    name="Class D"
)

class_e = Filters.create(
    func=is_class_e,
    name="Class E"
)

declared_message = Filters.create(
    func=is_declared_message,
    name="Declared message"
)

exchange_channel = Filters.create(
    func=is_exchange_channel,
    name="Exchange Channel"
)

from_user = Filters.create(
    func=is_from_user,
    name="From User"
)

hide_channel = Filters.create(
    func=is_hide_channel,
    name="Hide Channel"
)

new_group = Filters.create(
    func=is_new_group,
    name="New Group"
)

test_group = Filters.create(
    func=is_test_group,
    name="Test Group"
)


def is_ad_text(text: str, ocr: bool, matched: str = "") -> str:
    # Check if the text is ad text
    try:
        if not text:
            return ""

        for c in ascii_lowercase:
            if c != matched and is_regex_text(f"ad{c}", text, ocr):
                return c
    except Exception as e:
        logger.warning(f"Is ad text error: {e}", exc_info=True)

    return ""


def is_ban_text(text: str, ocr: bool, message: Message = None) -> bool:
    # Check if the text is ban text
    try:
        if is_regex_text("ban", text, ocr):
            return True

        # ad + con
        ad = is_regex_text("ad", text, ocr)
        con = is_con_text(text, ocr)

        if ad and con:
            return True

        # emoji + con
        emoji = is_emoji("ad", text, message)

        if emoji and con:
            return True

        # ad_ + con
        ad = is_ad_text(text, ocr)

        if ad and con:
            return True

        # ad_ + emoji
        if ad and emoji:
            return True

        # ad_ + ad_
        if ad:
            ad = is_ad_text(text, ocr, ad)
            return bool(ad)
    except Exception as e:
        logger.warning(f"Is ban text error: {e}", exc_info=True)

    return False


def is_bio_text(text: str) -> bool:
    # Check if the text is bio text
    try:
        if (is_regex_text("bio", text)
                or is_ban_text(text, False)):
            return True
    except Exception as e:
        logger.warning(f"Is bio text error: {e}", exc_info=True)

    return False


def is_bmd(message: Message) -> bool:
    # Check if the message is bot command:
    try:
        text = get_text(message)
        if (re.search("^/[a-z0-9]|^/$", text, re.I) and "/" not in text.split(" ")[0][1:]
                and not any(re.search(f"^/{c}$", text) for c in glovar.other_commands)):
            if not get_command_type(message):
                return True
    except Exception as e:
        logger.warning(f"Is bmd error: {e}", exc_info=True)

    return False


def is_class_d_user(user: Union[int, User]) -> bool:
    # Check if the user is a Class D personnel
    try:
        if isinstance(user, int):
            uid = user
        else:
            uid = user.id

        if uid in glovar.bad_ids["users"]:
            return True
    except Exception as e:
        logger.warning(f"Is class d user error: {e}", exc_info=True)

    return False


def is_class_e_user(user: Union[int, User]) -> bool:
    # Check if the user is a Class E personnel
    try:
        if isinstance(user, int):
            uid = user
        else:
            uid = user.id

        if uid in glovar.bot_ids:
            return True

        group_list = list(glovar.trust_ids)

        for gid in group_list:
            if uid in glovar.trust_ids.get(gid, set()):
                return True
    except Exception as e:
        logger.warning(f"Is class e user error: {e}", exc_info=True)

    return False


def is_con_text(text: str, ocr: bool) -> bool:
    # Check if the text is con text
    try:
        if (is_regex_text("con", text, ocr)
                or is_regex_text("iml", text, ocr)
                or is_regex_text("pho", text, ocr)):
            return True
    except Exception as e:
        logger.warning(f"Is con text error: {e}", exc_info=True)

    return False


def is_declared_message_id(gid: int, mid: int) -> bool:
    # Check if the message's ID is declared by other bots
    try:
        if mid in glovar.declared_message_ids.get(gid, set()):
            return True
    except Exception as e:
        logger.warning(f"Is declared message id error: {e}", exc_info=True)

    return False


def is_detected_url(message: Message, test: bool = False) -> str:
    # Check if the message include detected url
    try:
        if not test and is_class_c(None, message):
            return ""

        gid = message.chat.id
        links = get_links(message)

        for link in links:
            detected_type = glovar.contents.get(link, "")

            if detected_type and is_in_config(gid, detected_type):
                return detected_type
    except Exception as e:
        logger.warning(f"Is detected url error: {e}", exc_info=True)

    return ""


def is_detected_user(message: Message) -> bool:
    # Check if the message is sent by a detected user
    try:
        if not message.from_user:
            return False

        gid = message.chat.id
        uid = message.from_user.id
        now = message.date or get_now()

        return is_detected_user_id(gid, uid, now)
    except Exception as e:
        logger.warning(f"Is detected user error: {e}", exc_info=True)

    return False


def is_detected_user_id(gid: int, uid: int, now: int) -> bool:
    # Check if the user_id is detected in the group
    try:
        user_status = glovar.user_ids.get(uid, {})

        if not user_status:
            return False

        status = user_status["detected"].get(gid, 0)

        if now - status < glovar.time_punish:
            return True
    except Exception as e:
        logger.warning(f"Is detected user id error: {e}", exc_info=True)

    return False


def is_emoji(the_type: str, text: str, message: Message = None) -> bool:
    # Check the emoji type
    try:
        if message:
            text = get_text(message, False, False)

        emoji_dict = {}
        emoji_set = {emoji for emoji in glovar.emoji_set if emoji in text and emoji not in glovar.emoji_protect}
        emoji_old_set = deepcopy(emoji_set)

        for emoji in emoji_old_set:
            if any(emoji in emoji_old and emoji != emoji_old for emoji_old in emoji_old_set):
                emoji_set.discard(emoji)

        for emoji in emoji_set:
            emoji_dict[emoji] = text.count(emoji)

        # Check ad
        if the_type == "ad":
            if any(emoji_dict[emoji] >= glovar.emoji_ad_single for emoji in emoji_dict):
                return True

            if sum(emoji_dict.values()) >= glovar.emoji_ad_total:
                return True

        # Check many
        elif the_type == "many":
            if sum(emoji_dict.values()) >= glovar.emoji_many:
                return True

        # Check wb
        elif the_type == "wb":
            if any(emoji_dict[emoji] >= glovar.emoji_wb_single for emoji in emoji_dict):
                return True

            if sum(emoji_dict.values()) >= glovar.emoji_wb_total:
                return True
    except Exception as e:
        logger.warning(f"Is emoji error: {e}", exc_info=True)

    return False


def is_exe(message: Message) -> bool:
    # Check if the message contain a exe
    try:
        extensions = ["apk", "bat", "cmd", "com", "exe", "msi", "pif", "scr", "vbs"]

        if message.document:
            if message.document.file_name:
                file_name = message.document.file_name

                for file_type in extensions:
                    if re.search(f"[.]{file_type}$", file_name, re.I):
                        return True

            if message.document.mime_type:
                mime_type = message.document.mime_type

                if "application/x-ms" in mime_type or "executable" in mime_type:
                    return True

        extensions.remove("com")
        links = get_links(message)

        for link in links:
            for file_type in extensions:
                if re.search(f"[.]{file_type}$", link, re.I):
                    return True
    except Exception as e:
        logger.warning(f"Is exe error: {e}", exc_info=True)

    return False


def is_friend_username(client: Client, gid: int, username: str, friend: bool, friend_user: bool = False) -> bool:
    # Check if it is a friend username
    try:
        username = username.strip()

        if not username:
            return False

        if username[0] != "@":
            username = "@" + username

        if not re.search(r"\B@([a-z][0-9a-z_]{4,31})", username, re.I | re.M | re.S):
            return False

        peer_type, peer_id = resolve_username(client, username)

        if peer_type == "channel":
            if glovar.configs[gid].get("friend") or friend:
                if peer_id in glovar.except_ids["channels"] or glovar.admin_ids.get(peer_id, {}):
                    return True

        if peer_type == "user":
            if friend and friend_user:
                return True

            if friend or glovar.configs[gid].get("friend"):
                if is_class_e_user(peer_id):
                    return True

            member = get_member(client, gid, peer_id)

            if member and member.status in {"creator", "administrator", "member"}:
                return True
    except Exception as e:
        logger.warning(f"Is friend username: {e}", exc_info=True)

    return False


def is_high_score_user(user: User) -> float:
    # Check if the message is sent by a high score user
    try:
        if is_class_e_user(user):
            return 0.0

        uid = user.id
        user_status = glovar.user_ids.get(uid, {})

        if not user_status:
            return 0.0

        score = sum(user_status["score"].values())

        if score >= 3.0:
            return score
    except Exception as e:
        logger.warning(f"Is high score user error: {e}", exc_info=True)

    return 0.0


def is_in_config(gid: int, the_type: str) -> bool:
    # Check if the type is in the group's config
    try:
        if glovar.configs.get(gid, {}):
            return glovar.configs[gid].get(the_type, False)
    except Exception as e:
        logger.warning(f"Is in config error: {e}", exc_info=True)

    return False


def is_limited_user(gid: int, user: User, now: int, short: bool = True) -> bool:
    # Check the user is limited
    try:
        if is_class_e_user(user):
            return False

        if glovar.configs[gid].get("new"):
            if is_new_user(user, now, gid):
                return True

        uid = user.id

        if not glovar.user_ids.get(uid, {}):
            return False

        if not glovar.user_ids[uid].get("join", {}):
            return False

        if is_high_score_user(user) >= 1.8:
            return True

        join = glovar.user_ids[uid]["join"].get(gid, 0)

        if short and now - join < glovar.time_short:
            return True

        track = [gid for gid in glovar.user_ids[uid]["join"]
                 if now - glovar.user_ids[uid]["join"][gid] < glovar.time_track]

        if len(track) >= glovar.limit_track:
            return True
    except Exception as e:
        logger.warning(f"Is limited user error: {e}", exc_info=True)

    return False


def is_new_user(user: User, now: int, gid: int = 0, joined: bool = False) -> bool:
    # Check if the message is sent from a new joined member
    try:
        if is_class_e_user(user):
            return False

        uid = user.id

        if not glovar.user_ids.get(uid, {}):
            return False

        if not glovar.user_ids[uid].get("join", {}):
            return False

        if joined:
            return True

        if gid:
            join = glovar.user_ids[uid]["join"].get(gid, 0)

            if now - join < glovar.time_new:
                return True
        else:
            for gid in list(glovar.user_ids[uid]["join"]):
                join = glovar.user_ids[uid]["join"].get(gid, 0)

                if now - join < glovar.time_new:
                    return True
    except Exception as e:
        logger.warning(f"Is new user error: {e}", exc_info=True)

    return False


def is_nm_text(text: str) -> bool:
    # Check if the text is nm text
    try:
        if (is_regex_text("nm", text)
                or is_regex_text("bio", text)
                or is_ban_text(text, False)):
            return True
    except Exception as e:
        logger.warning(f"Is nm text error: {e}", exc_info=True)

    return False


def is_not_allowed(client: Client, message: Message, text: str = None, image_path: str = None) -> str:
    # Check if the message is not allowed in the group
    if image_path:
        need_delete = [image_path]
    else:
        need_delete = []

    try:
        if not message.chat:
            return ""

        # Basic data
        gid = message.chat.id
        now = message.date or get_now()

        # Regular message
        if not (text or image_path):
            # Bypass
            message_content = get_content(message)
            message_text = get_text(message)
            description = get_description(client, gid)

            if (description and message_text) and message_text in description:
                return ""

            pinned_message = get_pinned(client, gid)
            pinned_content = get_content(pinned_message)

            if (pinned_content and message_content) and message_content in pinned_content:
                return ""

            pinned_text = get_text(pinned_message)

            if (pinned_text and message_text) and message_text in pinned_text:
                return ""

            group_sticker = get_group_sticker(client, gid)

            if message.sticker:
                sticker_name = message.sticker.set_name

                if sticker_name and sticker_name == group_sticker:
                    return ""

            # Check detected records
            if not is_class_c(None, message):
                # If the user is being punished
                if is_detected_user(message):
                    return "true"

                # Content
                if message_content:
                    detection = glovar.contents.get(message_content, "")

                    if detection and is_in_config(gid, detection):
                        return detection

                # Url
                detected_url = is_detected_url(message)

                if is_in_config(gid, detected_url):
                    return detected_url

            # Privacy messages

            # Contact
            if is_in_config(gid, "con"):
                if message.contact:
                    return "con"

            # Location
            if is_in_config(gid, "loc"):
                if message.location or message.venue:
                    return "loc"

            # Video note
            if is_in_config(gid, "vdn"):
                if message.video_note:
                    return "vdn"

            # Voice
            if is_in_config(gid, "voi"):
                if message.voice:
                    return "voi"

            # Basic types messages

            # Bot command
            if is_in_config(gid, "bmd"):
                if is_bmd(message):
                    return "bmd"

            # Service
            if is_in_config(gid, "ser"):
                if message.service:
                    return "ser"

            if not is_class_c(None, message):
                # Animated Sticker
                if is_in_config(gid, "ast"):
                    if message.sticker and message.sticker.is_animated:
                        return "ast"

                # Audio
                if is_in_config(gid, "aud"):
                    if message.audio:
                        return "aud"

                # Document
                if is_in_config(gid, "doc"):
                    if message.document:
                        return "doc"

                # Game
                if is_in_config(gid, "gam"):
                    if message.game:
                        return "gam"

                # GIF
                if is_in_config(gid, "gif"):
                    if (message.animation
                            or (message.document
                                and message.document.mime_type
                                and "gif" in message.document.mime_type)):
                        return "gif"

                # Via Bot
                if is_in_config(gid, "via"):
                    if message.via_bot:
                        return "via"

                # Video
                if is_in_config(gid, "vid"):
                    if message.video:
                        return "vid"

                # Sticker
                if is_in_config(gid, "sti") and message.sticker:
                    return "sti"

                # Dice
                if is_in_config(gid, "dic") and (message.dice or (message.from_user
                                                                  and not message.forward_from_chat
                                                                  and not message.service
                                                                  and not message.media
                                                                  and not message.edit_date
                                                                  and not message.media_group_id
                                                                  and not message.text
                                                                  and not message.entities
                                                                  and not message_text
                                                                  and not message.caption
                                                                  and not message.contact
                                                                  and not message.location
                                                                  and not message.venue
                                                                  and not message.poll
                                                                  and not message.via_bot)):
                    return "dic"

            # Spam messages

            if not (is_class_c(None, message) or is_class_e(None, message)):
                message_text = get_text(message, True)

                # AFF link
                if is_in_config(gid, "aff"):
                    if is_regex_text("adi", message_text):
                        return "aff"

                # Emoji
                if is_in_config(gid, "emo"):
                    if is_emoji("many", message_text, message):
                        return "emo"

                # Executive file
                if is_in_config(gid, "exe"):
                    if is_exe(message):
                        return "exe"

                # Instant messenger link
                if is_in_config(gid, "iml"):
                    if is_regex_text("iml", message_text):
                        return "iml"

                # Phone Number
                if is_in_config(gid, "pho"):
                    if is_regex_text("pho", message_text):
                        return "pho"

                # Short link
                if is_in_config(gid, "sho"):
                    if is_regex_text("sho", message_text):
                        return "sho"

                # Telegram link
                if is_in_config(gid, "tgl"):
                    if is_tgl(client, message):
                        return "tgl"

                # Telegram proxy
                if is_in_config(gid, "tgp"):
                    if is_regex_text("tgp", message_text):
                        return "tgp"

                # QR code
                if is_in_config(gid, "qrc"):
                    # Get the image
                    file_id, file_ref, big = get_file_id(message)
                    image_path = big and get_downloaded_path(client, file_id, file_ref)
                    image_path and need_delete.append(image_path)

                    # Check hash
                    image_hash = image_path and get_md5sum("file", image_path)

                    if image_path and image_hash and image_hash not in glovar.except_ids["temp"]:
                        # Check declare status
                        if is_declared_message(None, message):
                            return ""

                        # Get QR code
                        qrcode = get_qrcode(image_path)

                        if qrcode and not (glovar.nospam_id in glovar.admin_ids[gid] and is_ban_text(qrcode, False)):
                            return "qrc"

            # Schedule to delete stickers and animations
            if (message.sticker
                    or message.animation
                    or (message.document
                        and message.document.mime_type
                        and "gif" in message.document.mime_type)
                    or message.dice):
                mid = message.message_id
                glovar.message_ids[gid]["stickers"][mid] = now
                save("message_ids")
                return ""

        # Preview message
        else:
            if text:
                # AFF link
                if is_in_config(gid, "aff"):
                    if is_regex_text("adi", text):
                        return "aff"

                # Instant messenger link
                if is_in_config(gid, "iml"):
                    if is_regex_text("iml", text):
                        return "iml"

                if is_regex_text("tgl", text):
                    # Telegram link
                    if is_in_config(gid, "tgl"):
                        # Ignore message's text and preview's display_url if possible
                        message_text = text.split("\n\n")[0]
                        url = text.split("\n\n")[1]
                        tgl_text = text.replace(message_text, "")

                        if get_stripped_link(url) in message_text:
                            tgl_text = tgl_text.replace(url, "")

                        if is_regex_text("tgl", tgl_text):
                            return "tgl"

                    # Short Link
                    if is_in_config(gid, "sho"):
                        if is_regex_text("sho", text):
                            return "sho"

                # Telegram proxy
                if is_in_config(gid, "tgp"):
                    if is_regex_text("tgp", text):
                        return "tgp"

            # QR code
            if image_path:
                qrcode = get_qrcode(image_path)

                if qrcode and not (glovar.nospam_id in glovar.admin_ids[gid] and is_ban_text(qrcode, False)):
                    return "qrc"
    except Exception as e:
        logger.warning(f"Is not allowed error: {e}", exc_info=True)
    finally:
        for file in need_delete:
            thread(delete_file, (file,))

    return ""


def is_regex_text(word_type: str, text: str, ocr: bool = False, again: bool = False) -> Optional[Match]:
    # Check if the text hit the regex rules
    result = None
    try:
        if text:
            if not again:
                text = re.sub(r"\s{2,}", " ", text)
            elif " " in text:
                text = re.sub(r"\s", "", text)
            else:
                return None
        else:
            return None

        with glovar.locks["regex"]:
            words = list(eval(f"glovar.{word_type}_words"))

        for word in words:
            if ocr and "(?# nocr)" in word:
                continue

            result = re.search(word, text, re.I | re.S | re.M)

            # Count and return
            if result:
                count = eval(f"glovar.{word_type}_words").get(word, 0)
                count += 1
                eval(f"glovar.{word_type}_words")[word] = count
                save(f"{word_type}_words")
                return result

        # Try again
        return is_regex_text(word_type, text, ocr, True)
    except Exception as e:
        logger.warning(f"Is regex text error: {e}", exc_info=True)

    return result


def is_tgl(client: Client, message: Message, friend: bool = False) -> bool:
    # Check if the message includes the Telegram link
    try:
        # Bypass prepare
        gid = message.chat.id
        description = get_description(client, gid).lower()
        pinned_message = get_pinned(client, gid)
        pinned_text = get_text(pinned_message).lower()

        # Check links
        bypass = get_stripped_link(get_channel_link(message))
        links = get_links(message)
        tg_links = [lk.lower() for lk in links if is_regex_text("tgl", lk)]

        # Define a bypass link filter function
        def is_bypass_link(link: str) -> bool:
            try:
                link_username = re.match(r"t\.me/([a-z][0-9a-z_]{4,31})/", f"{link}/")

                if link_username:
                    link_username = link_username.group(1).lower()

                    if link_username in glovar.invalid:
                        return True

                    if link_username == "joinchat":
                        link_username = ""
                    else:
                        if is_friend_username(client, gid, link_username, friend):
                            return True

                if (f"{bypass}/" in f"{link}/"
                        or link in description
                        or (link_username and link_username in description)
                        or link in pinned_text
                        or (link_username and link_username in pinned_text)):
                    return True
            except Exception as ee:
                logger.warning(f"Is bypass link error: {ee}", exc_info=True)

            return False

        bypass_list = [link for link in tg_links if is_bypass_link(link)]

        if len(bypass_list) != len(tg_links):
            return True

        # Check text
        message_text = get_text(message, True, True).lower()

        for bypass in bypass_list:
            message_text = message_text.replace(bypass, "")

        if is_regex_text("tgl", message_text):
            return True

        # Check mentions
        entities = message.entities or message.caption_entities

        if not entities:
            return False

        for en in entities:
            if en.type == "mention":
                username = get_entity_text(message, en)[1:].lower()

                if username in glovar.invalid:
                    continue

                if message.chat.username and username == message.chat.username.lower():
                    continue

                if username in description:
                    continue

                if username in pinned_text:
                    continue

                if not is_friend_username(client, gid, username, friend):
                    return True

            if en.type == "user":
                uid = en.user.id
                member = get_member(client, gid, uid)

                if member is False:
                    return True

                if member and member.status not in {"creator", "administrator", "member"}:
                    return True
    except Exception as e:
        logger.warning(f"Is tgl error: {e}", exc_info=True)

    return False


def is_watch_user(user: User, the_type: str, now: int) -> bool:
    # Check if the message is sent by a watch user
    try:
        if is_class_e_user(user):
            return False

        uid = user.id
        until = glovar.watch_ids[the_type].get(uid, 0)

        if now < until:
            return True
    except Exception as e:
        logger.warning(f"Is watch user error: {e}", exc_info=True)

    return False


def is_wb_text(text: str, ocr: bool) -> bool:
    # Check if the text is wb text
    try:
        if (is_regex_text("wb", text, ocr)
                or is_regex_text("ad", text, ocr)
                or is_regex_text("iml", text, ocr)
                or is_regex_text("pho", text, ocr)
                or is_regex_text("sho", text, ocr)
                or is_regex_text("spc", text, ocr)):
            return True

        for c in ascii_lowercase:
            if c not in {"i"} and is_regex_text(f"ad{c}", text, ocr):
                return True
    except Exception as e:
        logger.warning(f"Is wb text error: {e}", exc_info=True)

    return False
