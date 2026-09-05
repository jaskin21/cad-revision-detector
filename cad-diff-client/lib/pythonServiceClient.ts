export async function callDiffService(fileA: Buffer, fileNameA: string, fileB: Buffer, fileNameB: string) {
  const formData = new FormData();
  formData.append("revision_a", new Blob([new Uint8Array(fileA)]), fileNameA);
  formData.append("revision_b", new Blob([new Uint8Array(fileB)]), fileNameB);

  const response = await fetch(`${process.env.PYTHON_SERVICE_URL}/diff`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Diff service failed: ${response.status} ${await response.text()}`);
  }

  return response.json();
}