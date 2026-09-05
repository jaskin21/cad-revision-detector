import { Queue } from "bullmq";
import IORedis from "ioredis";

const connection = new IORedis(process.env.UPSTASH_REDIS_URL!, {
  maxRetriesPerRequest: null,
});

export const diffQueue = new Queue("diff-jobs", { connection });