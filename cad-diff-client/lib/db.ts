import { supabaseAdmin } from "@/lib/storage"; // reuse the same client

export async function createRevisionRecord(id: string, projectId: string, keyA: string, keyB: string) {
  const { error } = await supabaseAdmin
    .from("revisions")
    .insert({ id, project_id: projectId, key_a: keyA, key_b: keyB, status: "queued" });
  if (error) throw error;
}

export async function updateRevisionStatus(id: string, status: string) {
  const { error } = await supabaseAdmin.from("revisions").update({ status }).eq("id", id);
  if (error) throw error;
}

export async function saveRevisionResult(id: string, confidence: string, changes: unknown) {
  const { error } = await supabaseAdmin
    .from("revisions")
    .update({ status: "completed", confidence, changes, completed_at: new Date().toISOString() })
    .eq("id", id);
  if (error) throw error;
}

export async function markRevisionFailed(id: string, errorMessage: string) {
  const { error } = await supabaseAdmin
    .from("revisions")
    .update({ status: "failed", error: errorMessage })
    .eq("id", id);
  if (error) throw error;
}