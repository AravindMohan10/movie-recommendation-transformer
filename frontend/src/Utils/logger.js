/**
 * Dev-only logger for production cleanliness.
 * - log/warn: only in development (Vite import.meta.env.DEV)
 * - error: always logged so production errors are visible in browser console
 */
const isDev = import.meta.env.DEV;

export const devLog = isDev ? (...args) => console.log(...args) : () => {};
export const devWarn = isDev ? (...args) => console.warn(...args) : () => {};
export const devError = (...args) => console.error(...args);
