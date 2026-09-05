import { NextRequest, NextResponse } from "next/server";
import { uploadFile } from "@/lib/storage";
import { diffQueue } from "@/lib/queue";
import { createRevisionRecord } from "@/lib/db";
import { randomUUID } from "crypto";

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const fileA = formData.get("fileA") as File;
  const fileB = formData.get("fileB") as File;
  const projectId = formData.get("projectId") as string;

  if (!fileA || !fileB) {
    return NextResponse.json({ error: "Both revisions required" }, { status: 400 });
  }

  const revisionId = randomUUID();
  const keyA = `${projectId}/${revisionId}/rev-a-${fileA.name}`;
  const keyB = `${projectId}/${revisionId}/rev-b-${fileB.name}`;

  await uploadFile(keyA, Buffer.from(await fileA.arrayBuffer()), fileA.type);
  await uploadFile(keyB, Buffer.from(await fileB.arrayBuffer()), fileB.type);

  await createRevisionRecord(revisionId, projectId, keyA, keyB);
  await diffQueue.add("diff-job", { revisionId, projectId, keyA, keyB });

  return NextResponse.json({ revisionId, status: "queued" });
}