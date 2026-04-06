"""Voice Bot — entry point.

Usage:
    python -m voice_bot
    python -m voice_bot telegram.bot_token=YOUR_TOKEN
"""
from __future__ import annotations

import asyncio
import logging
import sys

import hydra
from omegaconf import DictConfig, OmegaConf

from voice_bot.schemas import VoiceBotConfig
from cli_base.logging import setup_logging

logger = logging.getLogger(__name__)

CONFIG_PATH = "conf"
CONFIG_NAME = "config"


async def _run_bot(cfg: VoiceBotConfig) -> None:
    """Initialize all components and start the bot."""
    from aiogram import Bot, Dispatcher
    from aiogram.client.default import DefaultBotProperties
    from aiogram.enums import ParseMode
    from aiogram.fsm.storage.memory import MemoryStorage

    from voice_bot.bot import router
    from voice_bot.containers import VoiceBotContainer
    from voice_bot.integrations.obsidian_tasks.handlers import task_router

    # DI container
    container = VoiceBotContainer(config=cfg)

    # Initialize all components
    logger.info("Initializing components...")
    transcriber = container.transcriber()
    intent_classifier = container.intent_classifier()
    account_resolver = container.account_resolver()
    firefly_client = container.firefly_client()
    firefly_extractor = container.firefly_extractor()
    date_parser = container.date_parser()
    obsidian_vault = container.obsidian_vault()
    task_extractor = container.task_extractor()

    # Load Firefly accounts for account resolver (for embeddings + index)
    try:
        await account_resolver.load_accounts(firefly_client)
        logger.info(
            "Loaded %d accounts from Firefly III (embeddings: %s)",
            len(account_resolver.account_names),
            account_resolver.has_embeddings,
        )
    except Exception as e:
        logger.warning("Could not load Firefly III accounts: %s", e)

    # Load Obsidian People registry (for person name resolution in tasks)
    try:
        obsidian_vault.load_people_registry()
        people_count = len(obsidian_vault.all_people_names())
        logger.info("Loaded %d people from Obsidian vault", people_count)
    except Exception as e:
        logger.warning("Could not load Obsidian people registry: %s", e)

    # Bot + dispatcher with MemoryStorage for FSM
    bot = Bot(
        token=cfg.telegram.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    dp.include_router(task_router)  # Obsidian task FSM callbacks

    # Inject all dependencies into handler context
    dp["transcriber"] = transcriber
    dp["intent_classifier"] = intent_classifier
    dp["account_resolver"] = account_resolver
    dp["firefly_client"] = firefly_client
    dp["firefly_extractor"] = firefly_extractor
    dp["date_parser"] = date_parser
    dp["vault"] = obsidian_vault
    dp["task_extractor"] = task_extractor
    dp["intents_cfg"] = cfg.intents  # intent → integration mapping

    logger.info("Bot is starting (polling)...")
    try:
        await dp.start_polling(bot)
    finally:
        await firefly_client.close()
        await bot.session.close()


@hydra.main(config_path=CONFIG_PATH, config_name=CONFIG_NAME, version_base=None)
def main(raw_cfg: DictConfig) -> None:
    """Entry point: Hydra config → Pydantic validation → run bot."""
    cfg_dict = OmegaConf.to_container(raw_cfg, resolve=True)
    cfg = VoiceBotConfig(**cfg_dict)

    setup_logging(level=cfg.log_level, log_file=cfg.log_file)

    logger.info("Voice Bot starting:")
    logger.info("  GigaAM model: %s", cfg.transcriber.model_name)
    logger.info("  LLM: %s @ %s", cfg.llm.model_name, cfg.llm.base_url)
    logger.info("  Embeddings: %s", cfg.embeddings.model_name)
    logger.info("  Firefly III: %s", cfg.firefly.get("base_url", "not configured"))

    if not cfg.telegram.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set!")
        sys.exit(1)

    asyncio.run(_run_bot(cfg))


if __name__ == "__main__":
    main()
