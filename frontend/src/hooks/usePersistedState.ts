import { useState, useEffect, useCallback } from 'react';

const STORAGE_PREFIX = 'evolution-suite-';

/**
 * Check if localStorage is available
 */
function isLocalStorageAvailable(): boolean {
  try {
    const testKey = '__test__';
    window.localStorage.setItem(testKey, testKey);
    window.localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

/**
 * Get a value from localStorage with the evolution-suite prefix
 */
export function getPersistedValue<T>(key: string, defaultValue: T): T {
  if (!isLocalStorageAvailable()) {
    return defaultValue;
  }

  try {
    const stored = localStorage.getItem(STORAGE_PREFIX + key);
    if (stored === null) {
      return defaultValue;
    }
    return JSON.parse(stored) as T;
  } catch {
    return defaultValue;
  }
}

/**
 * Set a value in localStorage with the evolution-suite prefix
 */
export function setPersistedValue<T>(key: string, value: T): void {
  if (!isLocalStorageAvailable()) {
    return;
  }

  try {
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value));
  } catch {
    // Silently fail if storage is full or unavailable
    console.warn(`Failed to persist value for key: ${key}`);
  }
}

/**
 * Remove a value from localStorage with the evolution-suite prefix
 */
export function removePersistedValue(key: string): void {
  if (!isLocalStorageAvailable()) {
    return;
  }

  try {
    localStorage.removeItem(STORAGE_PREFIX + key);
  } catch {
    // Silently fail
  }
}

/**
 * A hook that persists state to localStorage
 * @param key - The key to use in localStorage (will be prefixed with 'evolution-suite-')
 * @param defaultValue - The default value if nothing is stored
 * @returns A tuple of [value, setValue] similar to useState
 */
export function usePersistedState<T>(
  key: string,
  defaultValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  // Initialize state from localStorage or use default
  const [state, setState] = useState<T>(() => {
    return getPersistedValue(key, defaultValue);
  });

  // Persist to localStorage whenever state changes
  useEffect(() => {
    setPersistedValue(key, state);
  }, [key, state]);

  // Wrapper to support both direct values and updater functions
  const setPersistedState = useCallback(
    (value: T | ((prev: T) => T)) => {
      setState((prev) => {
        const newValue = typeof value === 'function' ? (value as (prev: T) => T)(prev) : value;
        return newValue;
      });
    },
    []
  );

  return [state, setPersistedState];
}
