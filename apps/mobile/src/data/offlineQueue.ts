import AsyncStorage from "@react-native-async-storage/async-storage";
import { MutationKey, onlineManager } from "@tanstack/react-query";

const STORAGE_KEY = "ai-health/mobile/offline-queue";

type QueueItem = {
  id: string;
  key: string;
  variables: unknown;
  createdAt: number;
};

type Handler = (variables: unknown) => Promise<void>;

const handlers = new Map<string, Handler>();

const serializeKey = (key: MutationKey): string => {
  if (Array.isArray(key)) {
    return JSON.stringify(key);
  }
  return typeof key === "string" ? key : JSON.stringify(key);
};

const readQueue = async (): Promise<QueueItem[]> => {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as QueueItem[];
  } catch (error) {
    console.warn("Failed to read offline queue", error);
    return [];
  }
};

const writeQueue = async (items: QueueItem[]) => {
  try {
    if (items.length === 0) {
      await AsyncStorage.removeItem(STORAGE_KEY);
      return;
    }
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch (error) {
    console.warn("Failed to write offline queue", error);
  }
};

export const queueMutation = async <TVariables>(mutationKey: MutationKey, variables: TVariables) => {
  const key = serializeKey(mutationKey);
  const items = await readQueue();
  items.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    key,
    variables,
    createdAt: Date.now()
  });
  await writeQueue(items);
};

export const registerQueueHandler = (mutationKey: MutationKey, handler: Handler) => {
  const key = serializeKey(mutationKey);
  handlers.set(key, handler);
  return () => {
    handlers.delete(key);
  };
};

export const flushQueue = async () => {
  const items = await readQueue();
  if (!onlineManager.isOnline() || items.length === 0) {
    return;
  }

  const remaining: QueueItem[] = [];

  for (const item of items) {
    const handler = handlers.get(item.key);
    if (!handler) {
      remaining.push(item);
      continue;
    }
    try {
      await handler(item.variables);
    } catch (error) {
      console.warn("Failed to flush queue item", error);
      remaining.push(item);
    }
  }

  await writeQueue(remaining);
};
