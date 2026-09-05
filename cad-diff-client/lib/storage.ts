import { createClient } from "@supabase/supabase-js";

// Service role key bypasses RLS — only ever use this on the server (API routes),
// never in client-side code.
export const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

const BUCKET = "cad-revisions";

export async function uploadFile(key: string, body: Buffer, contentType: string) {
  const { error } = await supabaseAdmin.storage
    .from(BUCKET)
    .upload(key, body, { contentType, upsert: true });

  if (error) throw error;
  return key;
}

export async function getFileUrl(key: string, expiresInSeconds = 3600) {
  const { data, error } = await supabaseAdmin.storage
    .from(BUCKET)
    .createSignedUrl(key, expiresInSeconds);

  if (error) throw error;
  return data.signedUrl;
}