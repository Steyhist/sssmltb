from asyncio import Queue, create_subprocess_exec
from signal import signal, SIGINT
from aiofiles import open as aiopen
from time import time
from bot import (
    LOGGER,
    PARALLEL_TASKS,
    Interval,
    QbInterval,
    bot,
    botloop,
    m_queue,
    scheduler,
)
from os import path as ospath, remove as osremove, execl as osexecl
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from sys import executable
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.mirror_leech_utils.download_utils.aria2_download import (
    start_aria2_listener,
)
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.ext_utils.bot_utils import cmd_exec, new_task, run_sync_to_async
from json import loads
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.message_utils import editMessage, sendMarkup, sendMessage
from .helper.ext_utils.misc_utils import clean_all, exit_clean_up, start_cleanup
from .modules import (
    batch,
    cancel,
    botfiles,
    copy,
    leech,
    mirror_leech,
    mirror_select,
    myfilesset,
    owner_settings,
    rcfm,
    stats,
    status,
    clone,
    storage,
    cleanup,
    torr_search,
    torr_select,
    user_settings,
    ytdlp,
    shell,
    exec,
    rss,
    serve,
    sync,
    gd_count,
    tmdb,
)


async def start(client, message):
    buttons = ButtonMaker()
    buttons.url_buildbutton("Owner", "https://Steyhist.t.me")
    buttons.url_buildbutton("Info", "https://t.me/steyhiststuff")
    reply_markup = buttons.build_menu(2)
    if CustomFilters.user_filter or CustomFilters.chat_filter:
        msg = """
**Halo, ¡Selamat datang di Histeria-MLTB!\n
Saya dapat membantu Anda menyalin file dari satu cloud ke cloud lainnya.
Saya juga dapat melakukan mirror-leech file dan tautan ke Telegram atau cloud**\n\n
        """
        await sendMarkup(msg, message, reply_markup)
    else:
        await sendMarkup(
            "Bukan pengguna yang sah, hubungi owner untuk meminta akses!", message, reply_markup
        )


async def restart(client, message):
    restart_msg = await sendMessage("Memulai ulang...", message)
    if scheduler.running:
        scheduler.shutdown(wait=False)
    if Interval:
        for intvl in list(Interval.values()):
            intvl.cancel()
    if QbInterval:
        QbInterval[0].cancel()
    await clean_all()
    await (
        await create_subprocess_exec(
            "pkill", "-9", "-f", "gunicorn|aria2c|rclone|qbittorrent-nox|ffmpeg"
        )
    ).wait()
    await (await create_subprocess_exec("python3", "update.py")).wait()
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_msg.chat.id}\n{restart_msg.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(client, message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage("Starting Ping", message)
    end_time = int(round(time() * 1000))
    await editMessage(f"{end_time - start_time} ms", reply)


async def get_ip(client, message):
    stdout, stderr, rc = await cmd_exec("curl https://ifconfig.me/all.json", shell=True)
    if rc == 0:
        res = loads(stdout)
        await message.reply_text(f"Your IP is {res['ip_addr']}")
    else:
        LOGGER.info(f"Error: {stderr}")


async def get_log(client, message):
    await client.send_document(chat_id=message.chat.id, document="botlog.txt")


@new_task
async def mirror_worker(queue: Queue):
    while True:
        tg_down = await queue.get()
        await tg_down.download()


async def main():
    await start_cleanup()
    await torr_search.initiate_search_tools()
    await run_sync_to_async(start_aria2_listener, wait=False)

    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        try:
            await bot.edit_message_text(chat_id, msg_id, "Restarted successfully!")
        except:
            pass
        osremove(".restartmsg")

    if PARALLEL_TASKS:
        for _ in range(PARALLEL_TASKS):
            mirror_worker(m_queue)

    bot.add_handler(MessageHandler(start, filters=command(BotCommands.StartCommand)))
    bot.add_handler(
        MessageHandler(
            restart,
            filters=command(BotCommands.RestartCommand)
            & (CustomFilters.owner_filter | CustomFilters.sudo_filter),
        )
    )
    bot.add_handler(
        MessageHandler(
            get_log,
            filters=command(BotCommands.LogsCommand)
            & (CustomFilters.owner_filter | CustomFilters.sudo_filter),
        )
    )
    bot.add_handler(
        MessageHandler(
            ping,
            filters=command(BotCommands.PingCommand)
            & (CustomFilters.user_filter | CustomFilters.chat_filter),
        )
    )
    bot.add_handler(MessageHandler(get_ip, filters=command(BotCommands.IpCommand)))
    LOGGER.info("Bot Dimulai!")
    signal(SIGINT, exit_clean_up)


botloop.run_until_complete(main())
botloop.run_forever()
