"""
ব্রো (Bro) — Nova Telegram Bot
টেলিগ্রাম বটের মাধ্যমে রিমোট কমান্ড গ্রহণ ও কার্যকর।
"""

import asyncio
import os
from typing import Any, Callable, Dict, List, Optional

from utils.logger import get_logger

log = get_logger("nova_telegram")

try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        ContextTypes,
        filters,
    )

    _HAS_TELEGRAM = True
except ImportError:
    _HAS_TELEGRAM = False
    log.warning("python-telegram-bot ইনস্টল নেই")


class NovaTelegramBot:
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = config or {}
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", cfg.get("token", ""))
        self._app: Optional[Any] = None
        self._command_handler: Optional[Callable] = None
        self._authorized_users: List[int] = cfg.get("authorized_users", [])
        self._running = False

    async def plan(self, command: str, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return [{"description": command, "action": "telegram_command", "risky": True}]

    async def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"status": "ready", "telegram": _HAS_TELEGRAM, "token_set": bool(self.token)}

    async def execute_step(self, step: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return await self.execute(step.get("description", ""), context)

    def set_command_handler(self, handler: Callable) -> None:
        self._command_handler = handler

    async def start(self) -> bool:
        if not _HAS_TELEGRAM:
            log.error("python-telegram-bot ইনস্টল প্রয়োজন")
            return False

        if not self.token or self.token == "your_telegram_bot_token":
            log.warning("টেলিগ্রাম বট টোকেন কনফিগার করা হয়নি")
            return False

        try:
            self._app = Application.builder().token(self.token).build()

            self._app.add_handler(CommandHandler("start", self._cmd_start))
            self._app.add_handler(CommandHandler("status", self._cmd_status))
            self._app.add_handler(CommandHandler("help", self._cmd_help))
            self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

            await self._app.initialize()
            await self._app.start()
            if self._app.updater:
                await self._app.updater.start_polling()
            self._running = True
            log.info("টেলিগ্রাম বট চালু")
            return True
        except Exception as exc:
            log.error("টেলিগ্রাম বট শুরু ব্যর্থ: %s", exc)
            return False

    async def stop(self) -> None:
        if self._app:
            if self._app.updater:
                await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        self._running = False
        log.info("টেলিগ্রাম বট বন্ধ")

    def _is_authorized(self, user_id: int) -> bool:
        if not self._authorized_users:
            return True
        return user_id in self._authorized_users

    async def _cmd_start(self, update: Any, context: Any) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "হাই! আমি ব্রো টেলিগ্রাম বট। 🤖\n"
                "আমাকে কমান্ড পাঠাও, আমি তোমার পিসিতে কাজ করব।\n\n"
                "/status — বর্তমান অবস্থা\n"
                "/help — সাহায্য"
            )

    async def _cmd_status(self, update: Any, context: Any) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "✅ ব্রো সক্রিয়\n"
                f"📡 সংযোগ: স্থিতিশীল"
            )

    async def _cmd_help(self, update: Any, context: Any) -> None:
        if update.effective_message:
            await update.effective_message.reply_text(
                "ব্রো কমান্ড:\n"
                "• যেকোনো টেক্সট পাঠাও — ব্রো সেটা কার্যকর করবে\n"
                "• /status — সিস্টেমের অবস্থা\n"
                "• /help — এই সাহায্য বার্তা"
            )

    async def _handle_message(self, update: Any, context: Any) -> None:
        if not update.effective_message or not update.effective_user:
            return

        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await update.effective_message.reply_text("⛔ অনুমোদিত নয়")
            return

        text = update.effective_message.text or ""
        log.info("টেলিগ্রাম কমান্ড [%d]: %s", user_id, text[:100])

        if self._command_handler:
            try:
                if asyncio.iscoroutinefunction(self._command_handler):
                    result = await self._command_handler(text, {"source": "telegram", "user_id": user_id})
                else:
                    result = self._command_handler(text, {"source": "telegram", "user_id": user_id})

                response = result if isinstance(result, str) else str(result)
                await update.effective_message.reply_text(response[:4096])
            except Exception as exc:
                await update.effective_message.reply_text(f"❌ ত্রুটি: {exc}")
        else:
            await update.effective_message.reply_text(f"📩 কমান্ড গৃহীত: {text}")

    async def send_message(self, chat_id: int, text: str) -> bool:
        if self._app and self._app.bot:
            try:
                await self._app.bot.send_message(chat_id=chat_id, text=text[:4096])
                return True
            except Exception as exc:
                log.error("টেলিগ্রাম মেসেজ পাঠানো ব্যর্থ: %s", exc)
        return False

    async def fallback(self, step: Dict[str, Any], error: Exception, context: Optional[Dict[str, Any]]) -> Any:
        return None
