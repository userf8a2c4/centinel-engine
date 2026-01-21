import config from "./config.js";
import logger from "./logger.js";
import { scrapeCycle } from "./scraper.js";
import batcher from "./batcher.js";

const randomBetween = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;

class Scheduler {
  constructor() {
    this.failedCycles = 0;
    this.isRunning = false;
  }

  async runCycle() {
    this.isRunning = true;
    logger.info({ msg: "Scrape cycle started" });

    const { results, consecutiveErrors } = await scrapeCycle();
    batcher.addEntries(results);

    if (results.every((entry) => entry.status === "ERROR" || entry.status >= 400)) {
      this.failedCycles += 1;
    } else {
      this.failedCycles = 0;
    }

    if (this.failedCycles > config.maxFailedCyclesBeforeWarn) {
      logger.warn({ msg: "Multiple failed cycles detected", failedCycles: this.failedCycles });
    }

    let nextInterval = config.cycleIntervalMs;
    if (consecutiveErrors > config.maxErrorsBeforeDegrade) {
      nextInterval = randomBetween(...config.degradedIntervalRangeMs);
      logger.warn({
        msg: "Degraded interval activated",
        consecutiveErrors,
        nextInterval
      });
    }

    logger.info({ msg: "Scrape cycle completed", nextInterval });
    setTimeout(() => {
      this.runCycle().catch((error) => {
        logger.error({ msg: "Cycle failed", error: error.message });
      });
    }, nextInterval);
  }

  start() {
    if (this.isRunning) {
      return;
    }

    batcher.start();
    this.runCycle().catch((error) => {
      logger.error({ msg: "Scheduler failed", error: error.message });
    });
  }
}

export default new Scheduler();
