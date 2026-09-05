import dotenv from "dotenv";
dotenv.config({ path: ".env.local" });

import { Worker } from "bullmq";
import IORedis from "ioredis";
import { supabaseAdmin } from "@/lib/storage";
import { callDiffService } from "@/lib/pythonServiceClient";
import { updateRevisionStatus, saveRevisionResult, markRevisionFailed } from "@/lib/db";

const connection = new IORedis(process.env.UPSTASH_REDIS_URL!, {
  maxRetriesPerRequest: null,
});

const BUCKET = "cad-revisions";

async function downloadFile(key: string): Promise<Buffer> {
  const { data, error } = await supabaseAdmin.storage.from(BUCKET).download(key);
  if (error) throw error;
  return Buffer.from(await data.arrayBuffer());
}

const worker = new Worker(
  "diff-jobs",
  async (job) => {
    const { revisionId, keyA, keyB } = job.data;

    await updateRevisionStatus(revisionId, "processing");

    try {
      const fileA = await downloadFile(keyA);
      const fileB = await downloadFile(keyB);

      const result = await callDiffService(fileA, keyA, fileB, keyB);

      await saveRevisionResult(revisionId, result.confidence, result.changes);
    } catch (err) {
      await markRevisionFailed(revisionId, err instanceof Error ? err.message : "Unknown error");
      throw err; // let BullMQ mark the job failed too
    }
  },
  { connection }
);

worker.on("completed", (job) => console.log(`Job ${job.id} completed`));
worker.on("failed", (job, err) => console.error(`Job ${job?.id} failed:`, err));

console.log("Worker started, listening for diff jobs...");