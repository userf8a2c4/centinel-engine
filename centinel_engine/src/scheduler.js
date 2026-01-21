/**
 * Scheduler de ciclos de scraping y degradación controlada.
 *
 * Scheduler for scraping cycles and controlled degradation.
 */

import config from "./config.js";
import logger from "./logger.js";
import { scrapeCycle } from "./scraper.js";
import batcher from "./batcher.js";

/**
 * Genera un número entero aleatorio entre min y max.
 *
 * Generate a random integer between min and max.
 */
const randomBetween = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;

/**
 * Orquesta ciclos de scraping y envío de batches.
 *
 * Orchestrate scraping cycles and batch sending.
 */
class Scheduler {
  constructor() {
    this.failedCycles = 0;
    this.isRunning = false;
  }

  /**
   * Ejecuta un ciclo completo y programa el siguiente.
   *
   * Run a full cycle and schedule the next one.
   */
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

  /**
   * Inicia el scheduler si no está en ejecución.
   *
   * Start the scheduler if it is not already running.
   */
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
