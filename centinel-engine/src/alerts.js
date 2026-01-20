import TelegramBot from "node-telegram-bot-api";
import config from "./config.js";
import logger from "./logger.js";

let bot = null;

if (config.telegramToken && config.telegramChatId) {
  bot = new TelegramBot(config.telegramToken, { polling: false });
  logger.info({ msg: "Telegram alerts enabled." });
}

export const sendAlert = async (message) => {
  if (!bot) {
    logger.warn({ msg: "Telegram alert skipped - missing credentials", message });
    return;
  }

  try {
    await bot.sendMessage(config.telegramChatId, message);
  } catch (error) {
    logger.error({ msg: "Failed to send Telegram alert", error: error.message });
  }
};
