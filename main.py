#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to handle '(my_)chat_member' updates.
Greets new users & keeps track of which chats the bot is in.

Usage:
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging
from typing import Optional, Tuple

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
# Telegram Imports
from telegram import (
    Chat,
    ChatMember,
    ChatMemberUpdated,
    Update,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    JobQueue
)
from telegram.constants import ParseMode
from indexed_bzip2 import IndexedBzip2File
from Block_Classes import Tick, BTCBlock, BTCPrice

# Other Imports
import json, asyncio, pickle

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


# Grab External settings
with open("config.toml", mode="rb") as fp:
    config = tomllib.load(fp)

# Enable logging

logging.basicConfig(
    format="%(asctime)s - %(filename)s : %(lineno)d - %(levelname)s - %(message)s", level=logging.DEBUG
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.getLogger("asyncssh").setLevel(logging.WARNING)
logging.getLogger("_client.py").setLevel(logging.WARNING)
#logging.disable(logging.INFO)

Bitcoin_blockprice = {}

# =============== STARTUP FUNCTIONS
async def post_init(application: Application) -> None:
    # Currently don't need any post_init
    global Bitcoin_blockprice
    Bitcoin_blockprice = await _load_blockprices()
    # Rebuild Hamburger Menu
    await application.bot.setMyCommands(command_list())
    return None


def command_list():
    # Returns a list of BotCommand objects to insert into the bot.
    logger.debug(f"Generate Bot Command Menu.")
    command_set = config['bot_commands']
    commands = []
    for cmd in command_set.keys():
        commands.append(BotCommand(cmd, command_set[cmd]["desc"]))
    return commands


# =============== BASIC BOT FUNCTIONS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.name.lstrip("@")
    response = (f'Welcome to the Bitcoin Blockprice Bot {user_name}!\n'
                f'Use /help to see what I can do for you.')
    # context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    # response = pretty(config) + f"\n\n{message}\n"
    await update.message.reply_text(response)


async def blockprice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return the blockprice details for a specific block."""
    try:
        # args[0] should contain the time for the timer in seconds
        block = context.args[0]
        logger.debug(f"Get blockprice for block {block}.")
        response = _get_blockprice(int(block))
        logger.debug(f"Blockprice for block {block} is {response}.")
        await update.effective_message.reply_text(f"{response}", parse_mode="Markdown")

    except (IndexError, ValueError, KeyError) as e:
        # await update.effective_message.reply_text("Usage: /ip2mac <Full IP Address>")
        logger.debug(f"ERROR: {e}")
        context.user_data["last_command"] = _get_blockprice
        await update.effective_message.reply_text("Usage: /block <Block #>")


async def satsusd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return the blockprice details for a specific block."""
    try:
        # args[0] should contain the time for the timer in seconds
        block = context.args[0]
        logger.debug(f"Get Sats/$ for block {block}.")
        response = _get_satsusd(int(block))
        logger.debug(f"Sats/$ for block {block} is {response}.")
        if response == float('inf'):
            await update.effective_message.reply_text(f"Infinite! 丰/$ (before ₿itcoin pricing data).\n")
        elif response == float('nan'):
            await update.effective_message.reply_text(_check_end(int(block))[1])
        else:
            await update.effective_message.reply_text(f"{response:,.0f} 丰/$\n")

    except (IndexError, ValueError, KeyError) as e:
        # await update.effective_message.reply_text("Usage: /ip2mac <Full IP Address>")
        logger.debug(f"ERROR: {e}")
        context.user_data["last_command"] = _get_satsusd
        await update.effective_message.reply_text("Usage: /sats <Block #>")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    commands = config['bot_commands']
    try:
        cmd = str(context.args[0]).strip(". ")
        help_response = f"Details for /{cmd}: \n{commands[cmd]['detail']}"

    except (IndexError, ValueError):
        help_response = "Using the Blockprice Bot:\n"
        for cmd in commands.keys():
            help_response = help_response + f"/{cmd} {commands[cmd]['desc']}\n"
    except (KeyError):
        help_response = "Invalid command: " + cmd
    await update.message.reply_text(help_response)


async def usdatblock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return the blockprice details for a specific block."""
    try:
        # args[0] should contain the time for the timer in seconds
        block = int(context.args[0])
        usd = float(context.args[1])
        logger.debug(f"Get BTC for {usd} block {block}.")
        response = _get_usdatblock(int(block), float(usd))
        logger.debug(f"BTC for ${usd} at block {block} is {response}.")
        if response == "inf":
            await update.effective_message.reply_text(f"Infinite! (before ₿itcoin pricing data).\n")
        elif response == "nan":
            await update.effective_message.reply_text(_check_end(int(block))[1])
        else:
            await update.effective_message.reply_text(f"${usd:,.2} at {block} was {response}.\n")

    except (IndexError, ValueError, KeyError) as e:
        # await update.effective_message.reply_text("Usage: /ip2mac <Full IP Address>")
        logger.debug(f"ERROR: {e}")
        context.user_data["last_command"] = _get_satsusd
        await update.effective_message.reply_text("Usage: /usd_block <Block #> <usd>")


async def btcatblock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return the blockprice details for a specific block."""
    try:
        # args[0] should contain the time for the timer in seconds
        block = int(context.args[0])
        btc = float(context.args[1])
        logger.debug(f"Get USD for {btc} at block {block}.")
        response = _get_btcatblock(int(block), float(btc))

        logger.debug(f"USD for {btc} btc at block {block} is {response}.")
        if response == float('inf'):
            await update.effective_message.reply_text(f"Infinite! 丰/$ (before ₿itcoin pricing data).\n")
        elif response == float('nan'):
            await update.effective_message.reply_text(_check_end(int(block))[1])
        else:
            await update.effective_message.reply_text(f"{btc:,.2} at {block} was {response}.\n")

    except (IndexError, ValueError, KeyError) as e:
        # await update.effective_message.reply_text("Usage: /ip2mac <Full IP Address>")
        logger.debug(f"ERROR: {e}")
        context.user_data["last_command"] = _get_satsusd
        await update.effective_message.reply_text("Usage: /sats <Block #>")


async def txprice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return the blockprice details for a specific block."""
    try:
        # args[0] should contain the time for the timer in seconds
        block = context.args[0]
        logger.debug(f"Get Sats/$ for block {block}.")
        response = _get_satsusd(int(block))
        logger.debug(f"Sats/$ for block {block} is {response}.")
        if response == float('inf'):
            await update.effective_message.reply_text(f"Infinite! 丰/$ (before ₿itcoin pricing data).\n")
        elif response == float('nan'):
            await update.effective_message.reply_text(_check_end(int(block))[1])
        else:
            await update.effective_message.reply_text(f"{response:,.0f} 丰/$\n")

    except (IndexError, ValueError, KeyError) as e:
        # await update.effective_message.reply_text("Usage: /ip2mac <Full IP Address>")
        logger.debug(f"ERROR: {e}")
        context.user_data["last_command"] = _get_satsusd
        await update.effective_message.reply_text("Usage: /sats <Block #>")


# =============== ADVANCED BOT FUNCTIONS
async def continue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # If the last command was entered without a parameter, allow the next message to
    # state the missing parameter
    last_command = context.user_data["last_command"]
    if last_command:
        logger.debug(f"Follow-on command for {last_command}.")
        # process the last command, but also strip trailing things that are often inserted by accident
        response, secondary = last_command(update.message.text.strip(". "))
        await update.message.reply_text(response)
        context.user_data["last_command"] = None


async def _load_blockprices() -> dict:
    temp_btc_blockprice = pickle.load(IndexedBzip2File("btc_blockprice.pkl.bz2", parallelization=0))
    #with IndexedBzip2File("bp.bz2", parallelization=0) as f:
    #    json_bytes = f.read()
    #json_str = json_bytes.decode('utf-8')
    #temp_btc_blockprice = json.loads(json_str)
    btc_blockprice = {}
    for block, price in temp_btc_blockprice.items():
        btc_blockprice[int(block)] = BTCPrice.from_dict(price)
    return btc_blockprice


def _check_end(block: int = 751157) -> (bool, str):
    # Check if the block is the last block
    global Bitcoin_blockprice
    last_block = max(Bitcoin_blockprice.keys())
    if block > last_block:
        return (False, f"Block {block} is too high. The current last block we have data for is {str(last_block)}.")
    else:
        return (True, "")


def _get_blockprice(block: int = 751157) -> str:
    logger.debug("Entering _get_blockprice")
    global Bitcoin_blockprice
    if not _check_end(block)[0]:
        return _check_end(block)[1]
    logger.debug(f"Blockprice for block {block} is {Bitcoin_blockprice[int(block)]}")
    return f"```\n{Bitcoin_blockprice[int(block)].as_str}\n```"


def _get_satsusd(block: int = 751157) -> float:
    logger.debug("Entering _get_satsusd")
    global Bitcoin_blockprice
    if Bitcoin_blockprice[int(block)].close == 0:
        return float('inf')
    elif not _check_end(block)[0]:
        return float('nan')
    moscowtime = (100000000.0/(Bitcoin_blockprice[int(block)].close))
    logger.debug(f"Sats/USD for block {block} is {moscowtime:,.0f}")
    return moscowtime


def _get_usdatblock(block: int = 751157, usd: float = 20.00) -> str:
    logger.debug("Entering _get_usdatblock")
    global Bitcoin_blockprice
    if Bitcoin_blockprice[int(block)].close == 0:
        return "inf"
    elif not _check_end(block)[0]:
        return "nan"
    sats = int((100000000.0 / (Bitcoin_blockprice[int(block)].close)) * usd)
    btc = sats / 100000000.0
    if btc > 1.0:
        return f"{btc:,.8f} ₿"
    else:
        return f"{sats:,} 丰"


def _get_btcatblock(block: int = 751157, btc: float = 20.00) -> str:
    logger.debug("Entering _get_btcatblock")
    global Bitcoin_blockprice
    if Bitcoin_blockprice[int(block)].close == 0:
        return "inf"
    elif not _check_end(block)[0]:
        return "nan"
    sats = int((100000000.0 / (Bitcoin_blockprice[int(block)].close)) * usd)
    btc = sats / 100000000.0
    if btc > 1.0:
        return f"{btc:,.8f} ₿"
    else:
        return f"{sats:,} 丰"



# =============== IDEAS TO ADD:
'''
/txprice <txid> Get a TXID, and convert all inputs/outputs to USD for the block the TXID is in
/usd@block <block> <btc-amt> Get the USD value of a BTC amount at a specific block
/btc@block <block> <usd-amt> Get the BTC value of a USD amount at a specific block
'''

# =============== MAIN LOOP
def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = (Application.builder()
                   .token(config['general']['tg_api_key'])
                   .post_init(post_init)
                   .build()
                   )

    # Other Commands
    application.add_handler(CommandHandler("block", blockprice))
    application.add_handler(CommandHandler("sats", satsusd))
    application.add_handler(CommandHandler("txprice", txprice))
    application.add_handler(CommandHandler("usd_block", usdatblock))
    application.add_handler(CommandHandler("btc_block", btcatblock))
    #application.add_handler(CommandHandler("update", update))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", start))

    # Inside a DM, collect non command i.e message - address commands which didn't have a proper input
    #application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, continue_command))

    # Run the bot until the user presses Ctrl-C
    # We pass 'allowed_updates' handle *all* updates including `chat_member` updates
    # To reset this, simply pass `allowed_updates=[]`
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
