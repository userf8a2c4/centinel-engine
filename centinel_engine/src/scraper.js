/**
 * Scraper defensivo con rotación de agentes y control de errores.
 *
 * Defensive scraper with user-agent rotation and error control.
 */

import axios from "axios";
import crypto from "crypto";
import config from "./config.js";
import logger from "./logger.js";

const robotsChecked = new Set();

/**
 * Suspende la ejecución durante un intervalo.
 *
 * Pause execution for a time interval.
 */
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Devuelve una copia del arreglo en orden aleatorio.
 *
 * Return a shuffled copy of the array.
 */
const shuffleArray = (array) => {
  const copy = [...array];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
};

/**
 * Selecciona un User-Agent aleatorio de configuración.
 *
 * Select a random User-Agent from configuration.
 */
const getRandomUserAgent = () => {
  const index = Math.floor(Math.random() * config.userAgents.length);
  return config.userAgents[index];
};

/**
 * Calcula un delay con jitter.
 *
 * Calculate a delay with jitter.
 */
const getDelayMs = () => {
  const jitter = (Math.random() * 2 - 1) * config.jitterMs;
  return Math.max(0, config.baseDelayMs + jitter);
};

/**
 * Indica si un status HTTP amerita reintento.
 *
 * Indicate whether an HTTP status should be retried.
 */
const shouldRetry = (status) => status === 429 || (status >= 500 && status <= 599);

/**
 * Revisa robots.txt una sola vez por dominio.
 *
 * Check robots.txt once per domain.
 */
const checkRobotsOnce = async (url) => {
  try {
    const parsed = new URL(url);
    const domain = parsed.origin;
    if (robotsChecked.has(domain)) {
      return;
    }
    robotsChecked.add(domain);
    const robotsUrl = `${domain}/robots.txt`;
    await axios.get(robotsUrl, { timeout: config.requestTimeoutMs });
    logger.info({ msg: "Robots.txt checked", domain, robotsUrl });
  } catch (error) {
    logger.warn({ msg: "Robots.txt check failed", error: error.message });
  }
};

/**
 * Descarga con reintentos controlados.
 *
 * Fetch with controlled retries.
 */
const fetchWithRetry = async (url) => {
  const headers = {
    "User-Agent": getRandomUserAgent(),
    Accept: "application/json,text/plain,*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    Connection: "keep-alive"
  };

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await axios.get(url, {
        timeout: config.requestTimeoutMs,
        maxRedirects: 5,
        headers,
        validateStatus: () => true
      });

      if (response.status >= 200 && response.status < 400) {
        return response;
      }

      if (attempt === 0 && shouldRetry(response.status)) {
        const backoff = 1000 * 2 ** attempt;
        logger.warn({ msg: "Retrying after status", url, status: response.status, backoff });
        await sleep(backoff);
        continue;
      }

      return response;
    } catch (error) {
      if (attempt === 0) {
        const backoff = 1000 * 2 ** attempt;
        logger.warn({ msg: "Retrying after error", url, error: error.message, backoff });
        await sleep(backoff);
        continue;
      }
      throw error;
    }
  }

  throw new Error("Unexpected retry flow");
};

/**
 * Ejecuta un ciclo completo de scraping y hashing.
 *
 * Run a full scraping and hashing cycle.
 */
export const scrapeCycle = async () => {
  const shuffled = shuffleArray(config.urls);
  let consecutiveErrors = 0;
  const results = [];

  for (const url of shuffled) {
    await checkRobotsOnce(url);

    try {
      const response = await fetchWithRetry(url);
      if (response.status >= 400) {
        consecutiveErrors += 1;
        results.push({
          hash: "0x",
          url,
          timestampISO: new Date().toISOString(),
          status: response.status
        });
      } else {
        let payload;
        try {
          payload = typeof response.data === "string" ? response.data : JSON.stringify(response.data);
        } catch (serializeError) {
          logger.error({ msg: "JSON serialize failed", url, error: serializeError.message });
          consecutiveErrors += 1;
          results.push({
            hash: "0x",
            url,
            timestampISO: new Date().toISOString(),
            status: "SERIALIZE_ERROR"
          });
          continue;
        }
        const hash = crypto.createHash("sha256").update(payload).digest("hex");
        results.push({
          hash: `0x${hash}`,
          url,
          timestampISO: new Date().toISOString(),
          status: response.status
        });
        consecutiveErrors = 0;
      }
    } catch (error) {
      consecutiveErrors += 1;
      results.push({
        hash: "0x",
        url,
        timestampISO: new Date().toISOString(),
        status: "ERROR"
      });
      logger.error({ msg: "Scrape failed", url, error: error.message });
    }

    await sleep(getDelayMs());
  }

  return { results, consecutiveErrors };
};
