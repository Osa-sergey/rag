"""Voice Expense Bot — entry point.

Usage:
    python -m voice_expense_bot
    python -m voice_expense_bot telegram.bot_token=YOUR_TOKEN
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf

from voice_expense_bot.schemas import VoiceExpenseConfig


logger = logging.getLogger(__name__)

# Hydra config path relative to this file
CONFIG_PATH = "conf"
CONFIG_NAME = "config"


async def _run_bot(cfg: VoiceExpenseConfig) -> None:
    """Initialize all components and start the bot."""
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode

    from voice_expense_bot.bot import router
    from voice_expense_bot.containers import VoiceExpenseContainer

    # Build DI container
    container = VoiceExpenseContainer(config=cfg)

    # Initialize components
    logger.info("Initializing components...")
    transcriber = container.transcriber()
    intent_classifier = container.intent_classifier()
    category_classifier = container.category_classifier()
    extractor = container.extractor()
    storage = container.storage()

    # Connect to database
    await storage.connect()

    # Create bot and dispatcher
    bot = Bot(
        token=cfg.telegram.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Inject dependencies into handler context
    dp["transcriber"] = transcriber
    dp["intent_classifier"] = intent_classifier
    dp["category_classifier"] = category_classifier
    dp["extractor"] = extractor
    dp["storage"] = storage

    logger.info("Bot is starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await storage.close()
        await bot.session.close()


@hydra.main(config_path=CONFIG_PATH, config_name=CONFIG_NAME, version_base=None)
def main(raw_cfg: DictConfig) -> None:
    """Entry point: Hydra config → Pydantic validation → run bot."""
    # Convert OmegaConf → dict → Pydantic
    cfg_dict = OmegaConf.to_container(raw_cfg, resolve=True)
    cfg = VoiceExpenseConfig(**cfg_dict)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, cfg.log_level, logging.INFO),
        format="%(asctime)s [%(name)-30s] %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("Voice Expense Bot starting with config:")
    logger.info("  GigaAM model: %s", cfg.transcriber.model_name)
    logger.info("  LLM: %s @ %s", cfg.llm.model_name, cfg.llm.base_url)
    logger.info("  Embeddings: %s", cfg.embeddings.model_name)
    logger.info("  Database: %s:%d/%s (schema=%s)",
                cfg.database.host, cfg.database.port,
                cfg.database.database, cfg.database.schema_name)

    if not cfg.telegram.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set!")
        logger.error("Set it via: telegram.bot_token=YOUR_TOKEN or TELEGRAM_BOT_TOKEN env var")
        sys.exit(1)

    asyncio.run(_run_bot(cfg))


if __name__ == "__main__":
    main()
